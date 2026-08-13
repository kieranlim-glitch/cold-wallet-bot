"""
Fetches live balances for all addresses in addresses.csv and posts
a clean balance report to Slack, in the same style as wallet_report.py.
SC and ORDI show ERROR — no reliable keyless balance source found for them.
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
    errors = {}

    for row in rows:
        symbol = row["symbol"]
        network_id = row["network_id"]
        address = row["address"]

        try:
            valid = validate_address(network_id, address)
        except ValueError:
            valid = None

        if valid is False:
            results[symbol] = None
            errors[symbol] = "Invalid address format"
            continue

        fetcher = BALANCE_FETCHERS.get(network_id)
        if fetcher is None:
            results[symbol] = None
            errors[symbol] = "No balance source available"
            continue

        try:
            results[symbol] = fetcher(address)
        except Exception as e:
            results[symbol] = None
            errors[symbol] = str(e)

    order = [row["symbol"] for row in rows]
    lines = [
        f"{sym:<12} {'ERROR':>15}" if results[sym] is None else
        f"{sym:<12} {results[sym]:>15,.4f}"
        for sym in order
    ]
    msg = "*Cold wallet balances*\n```" + "\n".join(lines) + "```"

    if errors:
        err_lines = "\n".join(f"• {sym}: {err}" for sym, err in errors.items())
        msg += f"\n\n:warning: *Fetch errors:*\n{err_lines}"

    print("\n".join(lines))
    if errors:
        print("\nErrors:")
        for sym, err in errors.items():
            print(f"  {sym}: {err}")

    post_to_slack(msg)


if __name__ == "__main__":
    main()
