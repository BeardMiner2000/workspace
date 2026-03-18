from datetime import datetime
import time


def main() -> None:
    print("[data_ingest] starting stub service")
    print("[data_ingest] TODO: connect CCXT/news/sentiment feeds and persist normalized market events")
    while True:
        print(f"[data_ingest] heartbeat {datetime.utcnow().isoformat()}Z")
        time.sleep(30)


if __name__ == "__main__":
    main()
