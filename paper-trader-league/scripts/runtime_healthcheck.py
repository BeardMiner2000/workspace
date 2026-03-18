#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


DEFAULT_CONTAINERS = [
    "ptl-timescaledb",
    "ptl-trade-engine",
    "ptl-scoring-api",
    "ptl-data-ingest",
    "ptl-grafana",
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str


def run_command(command: list[str]) -> str:
    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        stdout = proc.stdout.strip()
        msg = stderr or stdout or f"command failed with exit code {proc.returncode}"
        raise RuntimeError(msg)
    return proc.stdout.strip()


def fetch_json(url: str, timeout: float = 5.0) -> Any:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc)) from exc


def container_status(container: str) -> tuple[str, str]:
    output = run_command(
        [
            "docker",
            "inspect",
            "-f",
            "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
            container,
        ]
    )
    status, health = output.split("|", 1)
    return status, health


def psql_query(container: str, user: str, database: str, sql: str) -> str:
    return run_command(["docker", "exec", container, "psql", "-U", user, "-d", database, "-At", "-c", sql])


def parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def age_seconds(ts: datetime | None) -> float | None:
    if ts is None:
        return None
    now = datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (now - ts.astimezone(timezone.utc)).total_seconds()


def check_containers(containers: list[str]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for container in containers:
        try:
            status, health = container_status(container)
            ok = status == "running" and health in {"healthy", "none", "starting"}
            results.append(CheckResult(f"container:{container}", ok, f"status={status}, health={health}"))
        except Exception as exc:
            results.append(CheckResult(f"container:{container}", False, str(exc)))
    return results


def check_http(url: str, expected_service: str | None = None, predicate: Any | None = None) -> CheckResult:
    try:
        payload = fetch_json(url)
        if predicate is not None:
            ok = bool(predicate(payload))
        else:
            ok = payload.get("ok") is True
        if expected_service is not None:
            ok = ok and payload.get("service") == expected_service
        return CheckResult(f"http:{url}", ok, json.dumps(payload, sort_keys=True))
    except Exception as exc:
        return CheckResult(f"http:{url}", False, str(exc))


def check_db_state(container: str, user: str, database: str, season_id: str, stale_after: int) -> list[CheckResult]:
    results: list[CheckResult] = []

    try:
        season_count = int(psql_query(container, user, database, f"SELECT COUNT(*) FROM seasons WHERE season_id = '{season_id}';"))
        bot_count = int(psql_query(container, user, database, f"SELECT COUNT(*) FROM season_bots WHERE season_id = '{season_id}';"))
        counts_raw = psql_query(
            container,
            user,
            database,
            "SELECT json_build_object(" \
            "'market_marks', (SELECT COUNT(*) FROM market_marks WHERE season_id = '" + season_id + "')," \
            "'bot_orders', (SELECT COUNT(*) FROM bot_orders WHERE season_id = '" + season_id + "')," \
            "'bot_fills', (SELECT COUNT(*) FROM bot_fills WHERE season_id = '" + season_id + "')," \
            "'bot_metrics', (SELECT COUNT(*) FROM bot_metrics WHERE season_id = '" + season_id + "')" \
            ");",
        )
        latest_raw = psql_query(
            container,
            user,
            database,
            "SELECT json_build_object(" \
            "'market_marks', COALESCE((SELECT to_char(MAX(ts) AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.MSOF') FROM market_marks WHERE season_id = '" + season_id + "'), '')," \
            "'bot_orders', COALESCE((SELECT to_char(MAX(ts) AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.MSOF') FROM bot_orders WHERE season_id = '" + season_id + "'), '')," \
            "'bot_metrics', COALESCE((SELECT to_char(MAX(ts) AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.MSOF') FROM bot_metrics WHERE season_id = '" + season_id + "'), '')" \
            ");",
        )
    except Exception as exc:
        return [CheckResult("db:query", False, str(exc))]

    counts = json.loads(counts_raw)
    latest = json.loads(latest_raw)

    results.append(CheckResult("db:season_exists", season_count == 1, f"season_id={season_id}, count={season_count}"))
    results.append(CheckResult("db:season_bots", bot_count >= 1, f"season_id={season_id}, count={bot_count}"))

    nonzero = all(int(counts[key]) > 0 for key in ("market_marks", "bot_orders", "bot_fills", "bot_metrics"))
    results.append(CheckResult("db:row_counts", nonzero, json.dumps(counts, sort_keys=True)))

    for key, label in (("market_marks", "progress:market_marks"), ("bot_orders", "progress:bot_orders"), ("bot_metrics", "progress:bot_metrics")):
        ts = parse_iso8601(latest.get(key))
        age = age_seconds(ts)
        ok = age is not None and age <= stale_after
        age_text = "missing" if age is None else f"age_seconds={age:.1f}, latest_ts={latest.get(key)}"
        results.append(CheckResult(label, ok, age_text))

    return results


def check_leaderboard(url: str, season_id: str, min_bots: int = 1) -> CheckResult:
    try:
        payload = fetch_json(f"{url}?season_id={season_id}")
        bots = payload.get("bots", [])
        ok = payload.get("season_id") == season_id and len(bots) >= min_bots
        return CheckResult("api:leaderboard", ok, f"bot_count={len(bots)}")
    except Exception as exc:
        return CheckResult("api:leaderboard", False, str(exc))


def print_results(results: list[CheckResult]) -> int:
    failed = [r for r in results if not r.ok]
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {result.details}")
    print()
    if failed:
        print(f"SUMMARY: FAIL ({len(failed)} check(s) failed)")
        return 1
    print(f"SUMMARY: OK ({len(results)} checks)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Paper Trader League runtime continuity checker")
    parser.add_argument("--season-id", default="season-001")
    parser.add_argument("--stale-after-seconds", type=int, default=180)
    parser.add_argument("--postgres-container", default="ptl-timescaledb")
    parser.add_argument("--postgres-user", default="paperbot")
    parser.add_argument("--postgres-db", default="paperbot")
    parser.add_argument("--trade-engine-health", default="http://localhost:8088/health")
    parser.add_argument("--scoring-api-health", default="http://localhost:8090/health")
    parser.add_argument("--leaderboard-url", default="http://localhost:8090/leaderboard")
    parser.add_argument("--grafana-health", default="http://localhost:3000/api/health")
    args = parser.parse_args()

    results: list[CheckResult] = []
    results.extend(check_containers(DEFAULT_CONTAINERS))
    results.append(check_http(args.trade_engine_health, expected_service="trade_engine"))
    results.append(check_http(args.scoring_api_health, expected_service="scoring_api"))
    results.append(check_http(args.grafana_health, predicate=lambda payload: payload.get("database") == "ok"))
    results.append(check_leaderboard(args.leaderboard_url, args.season_id, min_bots=3))
    results.extend(
        check_db_state(
            args.postgres_container,
            args.postgres_user,
            args.postgres_db,
            args.season_id,
            args.stale_after_seconds,
        )
    )
    return print_results(results)


if __name__ == "__main__":
    sys.exit(main())
