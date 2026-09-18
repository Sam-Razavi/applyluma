#!/usr/bin/env python3
"""Send a fake inbound email to the webhook, to test ingestion end to end.

Exists so the pipeline can be exercised before any DNS or mail vendor is set
up. Standard library only, so it runs on Windows, macOS and Linux with no
virtualenv and nothing to install.

Requires the server to be running the ``generic`` vendor
(``INBOUND_EMAIL_VENDOR=generic``), since it signs the body the way that
adapter expects.

    python backend/scripts/send_test_inbound_email.py \
        --address u-YOURTOKEN@in.applyluma.com \
        --secret  YOUR_INBOUND_EMAIL_WEBHOOK_SECRET

Then open /admin/inbound-mail to see what arrived and what it matched.

Add --dry-run to print the request without sending it.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime

DEFAULT_URL = "https://applyluma-production.up.railway.app/api/v1/inbound/email"
SIGNATURE_HEADER = "X-ApplyLuma-Signature"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a signed test message to the inbound email webhook.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--address",
        required=True,
        help="Your inbound address, from /admin/users -> your user -> Inbound mail address.",
    )
    parser.add_argument(
        "--secret",
        required=True,
        help="The INBOUND_EMAIL_WEBHOOK_SECRET set on the server.",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Webhook URL (default: {DEFAULT_URL})")
    parser.add_argument(
        "--from",
        dest="from_address",
        default="Spotify Careers <careers@spotify.com>",
        help="Sender to simulate. Use a company you actually have an application for "
        "to see a match.",
    )
    parser.add_argument("--subject", default="Your application to Spotify")
    parser.add_argument("--text", default="Thank you for applying. We will be in touch.")
    parser.add_argument(
        "--message-id",
        default=None,
        help="Defaults to a unique id per run. Reuse one to test that duplicates are dropped.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the request instead of sending it."
    )
    return parser


def build_payload(args: argparse.Namespace) -> dict[str, str]:
    now = datetime.now(UTC)
    # Unique by default so repeated runs each create a row; pass --message-id
    # explicitly to exercise the dedupe path instead.
    message_id = args.message_id or f"<test-{now.strftime('%Y%m%d%H%M%S%f')}@applyluma.test>"
    return {
        "to": args.address,
        "from": args.from_address,
        "subject": args.subject,
        "text": args.text,
        "message_id": message_id,
        "date": now.strftime("%a, %d %b %Y %H:%M:%S +0000"),
    }


def sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def explain(status: int, body: str) -> str:
    """Translate the webhook's deliberately-terse replies into next steps."""
    if status == 202:
        return "Accepted. Open /admin/inbound-mail — the message should be listed."
    if status == 200:
        return (
            "Ignored. The address did not resolve to a user. Check that --address "
            "matches the one shown in the admin drawer, and that INBOUND_EMAIL_DOMAIN "
            "on the server matches its domain part."
        )
    if status == 400:
        return (
            "Invalid signature. --secret does not match INBOUND_EMAIL_WEBHOOK_SECRET "
            "on the server."
        )
    if status == 503:
        return (
            "Not configured. Set INBOUND_EMAIL_WEBHOOK_SECRET and INBOUND_EMAIL_DOMAIN "
            "on the server, and make sure INBOUND_EMAIL_VENDOR=generic for this script."
        )
    if status == 413:
        return "Payload too large."
    return f"Unexpected response: {body}"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if "@" not in args.address:
        print(f"error: --address does not look like an email address: {args.address}")
        return 2

    body = json.dumps(build_payload(args)).encode("utf-8")
    signature = sign(body, args.secret)

    if args.dry_run:
        print(f"POST {args.url}")
        print(f"{SIGNATURE_HEADER}: {signature}")
        print(body.decode())
        return 0

    request = urllib.request.Request(
        args.url,
        data=body,
        headers={"Content-Type": "application/json", SIGNATURE_HEADER: signature},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status, text = response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        # The webhook answers 4xx/5xx with a JSON body worth showing.
        status, text = exc.code, exc.read().decode()
    except urllib.error.URLError as exc:
        print(f"Could not reach {args.url}: {exc.reason}")
        return 1

    print(f"HTTP {status}  {text}")
    print(explain(status, text))
    return 0 if status in (200, 202) else 1


if __name__ == "__main__":
    sys.exit(main())
