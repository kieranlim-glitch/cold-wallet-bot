"""
Fetches live balances, compares against the most recent prior snapshot
saved in balance_history.json, and posts a report (with day-over-day
absolute and percentage diffs, labeled with the SGT capture time) to
Slack. Saves today's snapshot for tomorrow's comparison.
"""
import csv
import json
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import requests
from address_validators import validate_address
from balance_fetchers import BALANCE_FETCHERS

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
SLACK_WEBHOOK_URL_2 = os.environ.get("SLACK_WEBHOOK_URL_2", "")
HISTORY_FILE = "balance_history.json"
SGT = ZoneInfo("Asia/Singapore")


def post_to_slack(text: str):
    for url in [SLACK_WEBHOOK_URL, SLACK_WEBHOOK_URL_2]:
        if not url:
            continue
        try:
            r = requests.post(url, json={"text": text}, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"Failed to post to Slack webhook: {e}")


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, sort_keys=True)


def most_recent_prior_date(history, today_str):
    past_dates = [d for d in history.keys() if d < today_str]
    if not past_dates:
        return None
    return max(past_dates)


def format_sgt(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str).astimezone(SGT)
    return dt.strftime("%Y-%m-%d %I:%M %p SGT")


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

    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")

    history = load_history()
    prior_date = most_recent_prior_date(history, today_str)
    prior_entry = history.get(prior_date, {}) if prior_date else {}
    prior_balances = prior_entry.get("balances", {})
    prior_captured_at = prior_entry.get("captured_at")

    order = [row["symbol"] for row in rows]
    lines = []
    for sym in order:
        current = results[sym]
        line = f"{sym:<8} {current:>15,.4f}"
        if prior_date and sym in prior_balances:
            prior = prior_balances[sym]
            diff = current - prior
            sign = "+" if diff >= 0 else ""
            if prior != 0:
                pct = (diff / prior) * 100
                pct_str = f"{sign}{pct:,.2f}%"
            else:
                pct_str = "N/A"
            line += f"  ({sign}{diff:,.4f}, {pct_str})"
        lines.append(line)

    if prior_date and prior_captured_at:
        header = f"*Cold wallet balances* (vs {format_sgt(prior_captured_at)})"
    else:
        header = "*Cold wallet balances* (no prior snapshot yet)"

    msg = f"{header}\n```" + "\n".join(lines) + "```"
    print("\n".join(lines))

    post_to_slack(msg)

    history[today_str] = {
        "captured_at": now_utc.isoformat(),
        "balances": results,
    }
    save_history(history)


if __name__ == "__main__":
    main()
