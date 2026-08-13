"""
Fetches live balances for all addresses in addresses.csv and posts
a clean balance report to Slack, in the same style as wallet_report.py.
Any chain without a working balance source (or a failed fetch) shows 0.0000
instead of an error — SC and ORDI always show 0 since no keyless source
exists for them; other chains show 0 if the live fetch fails.
"""

import csv
import os
import sys
import requests
from address_validators import validate_address
from balance_fetchers import BALANCE_FETCHERS

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")


def post_to_slack(text: str):
    if not SLACK_WEBHOOK_URL:
        print("No SLACK_WEBHOOK_URL set, skipping Slack post.")
        return
    r = requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=20)
    r.raise_for_status()


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "addresses.csv"

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    results = {}

    for row in rows:
        symbol = row["symbol"]
        network_id = row["network_id"]
        address = row["address"]

        try:
            valid = validate_address(network_id, address)
        except ValueError:
            valid = None

        if valid is False:
            results[symbol] = 0.0
            continue

        fetcher = BALANCE_FETCHERS.get(network_id)
        if fetcher is None:
            results[symbol] = 0.0
            continue

        try:
            results[symbol] = fetcher(address)
        except Exception:
            results[symbol] = 0.0

    order = [row["symbol"] for row in rows]
    lines = [f"{sym:<12} {results[sym]:>15,.4f}" for sym in order]
    msg = "*Cold wallet balances*\n```" + "\n".join(lines) + "```"

    print("\n".join(lines))

    post_to_slack(msg)


if __name__ == "__main__":
    main()
