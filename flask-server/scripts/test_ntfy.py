from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from website.notifications import _build_auth_header


def main() -> int:
    load_dotenv(PROJECT_DIR / ".env", override=False)

    parser = argparse.ArgumentParser(description="Send test message to ntfy.")
    parser.add_argument(
        "--message",
        default="Test ntfy da sito-filippo",
        help="Message body to publish.",
    )
    parser.add_argument(
        "--title",
        default="Test notifica",
        help="Value for ntfy Title header.",
    )
    parser.add_argument(
        "--priority",
        default="3",
        help="Value for ntfy Priority header.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Override request timeout in seconds.",
    )
    args = parser.parse_args()

    import os

    ntfy_url = os.getenv("NTFY_URL", "https://ntfy.filipporadiceosteopata.com/Appuntamenti").strip()
    ntfy_token = os.getenv("NTFY_TOKEN", "").strip()
    ntfy_timeout = args.timeout if args.timeout is not None else float(os.getenv("NTFY_TIMEOUT", "5"))

    if not ntfy_url:
        print("ERR: NTFY_URL missing")
        return 2

    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Title": args.title,
        "Priority": args.priority,
    }
    if ntfy_token:
        headers["Authorization"] = _build_auth_header(ntfy_token)

    payload = args.message.encode("utf-8")
    req = request.Request(ntfy_url, data=payload, headers=headers, method="POST")

    print(f"POST {ntfy_url}")
    print(f"Auth header: {'present' if 'Authorization' in headers else 'missing'}")
    print(f"Timeout: {ntfy_timeout}s")

    try:
        with request.urlopen(req, timeout=ntfy_timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(f"Status: {response.status}")
            if body:
                print("Response body:")
                print(body)
            return 0
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP error: {exc.code}")
        if body:
            print("Response body:")
            print(body)
        return 1
    except URLError as exc:
        print(f"Connection error: {exc.reason}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
