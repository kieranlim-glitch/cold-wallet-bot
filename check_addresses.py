"""
Reads addresses.csv and validates each address against its network's
expected format using address_validators.py. Also flags any address
string that appears under more than one network_id, and posts a
summary to Slack.
"""

import csv
import os
import sys
from collections import defaultdict
import requests
from address_validators import validate_address

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")


def post_to_slack(text: str):
    if not SLACK_WEBHOOK_URL:
        print("No SLACK_WEBHOOK_URL set, skipping Slack post.")
        return
    r = requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=20)
    r.raise_for_status()


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "addresses.csv"

    results = []
    address_to_networks = defaultdict(list)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row["symbol"]
            network_id = row["network_id"]
            address = row["address"]
            try:
                ok = validate_address(network_id, address)
            except ValueError as e:
                ok = None
                print(f"WARNING: {e}")
            results.append((symbol, network_id, address, ok))
            address_to_networks[address].append((symbol, network_id))

    lines = [f"{'Symbol':<8}{'Network':<14}{'Status':<10}"]
    invalid_count = 0
    for symbol, network_id, address, ok in results:
        if ok is None:
            status = "NO VALIDATOR"
        elif ok:
            status = "VALID"
        else:
            status = "INVALID"
            invalid_count += 1
        lines.append(f"{symbol:<8}{network_id:<14}{status:<10}")

    print("\n".join(lines))
    print(f"\n{invalid_count} invalid address(es) out of {len(results)} total.")

    duplicate_lines = []
    for address, entries in address_to_networks.items():
        distinct_networks = {net for _, net in entries}
        if len(distinct_networks) > 1:
            names = ", ".join(f"{sym} ({net})" for sym, net in entries)
            duplicate_lines.append(f"• {address}: {names}")

    slack_msg = "*Address Validation Report*\n```" + "\n".join(lines) + "```"
    slack_msg += f"\n{invalid_count} invalid, {len(duplicate_lines)} duplicate(s)."
    if duplicate_lines:
        slack_msg += "\n\n:warning: *Duplicate addresses across chains:*\n" + "\n".join(duplicate_lines)

    post_to_slack(slack_msg)

    if invalid_count > 0 or duplicate_lines:
        sys.exit(1)


if __name__ == "__main__":
    main()
