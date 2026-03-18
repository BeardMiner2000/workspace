from datetime import datetime, timezone
import os
import time


def main() -> None:
    source = os.getenv('MARKET_DATA_SOURCE', 'stub')
    print(f'[data_ingest] starting placeholder service (source={source})')
    print('[data_ingest] current role: keep the Docker stack alive and reserve the process boundary for future feed adapters')
    while True:
        print(f"[data_ingest] heartbeat {datetime.now(timezone.utc).isoformat()}")
        time.sleep(30)


if __name__ == '__main__':
    main()
