# Cold Wallet Bot

Tracks daily balances for a set of cold wallet addresses across multiple chains,
posts a report to Slack with day-over-day changes, and keeps a running history.

## What it does

Every day at 10am SGT (triggered externally via cron-job.org):

1. Reads the address list from `addresses.csv`
2. Validates each address's format for its chain
3. Fetches the live on-chain balance for each address
4. Compares against the previous day's snapshot (`balance_history.json`)
5. Posts a report to Slack showing current balance, absolute change, and % change
6. Saves today's balances as the new snapshot for tomorrow's comparison

## Currently tracked

| Symbol | Chain |
|--------|-------|
| APT | Aptos |
| AR | Arweave |
| ICP | Internet Computer |
| VET | VeChain |
| ZIL | Zilliqa |

## Files

- **`addresses.csv`** — the address list (symbol, name, network_id, address)
- **`address_validators.py`** — per-chain address format validation
- **`balance_fetchers.py`** — per-chain live balance fetching (RPC/REST calls)
- **`cold_wallet_report.py`** — main script: validates, fetches, diffs, posts to Slack, saves snapshot
- **`balance_history.json`** — daily snapshot log (auto-updated by every run)
- **`.github/workflows/validate.yml`** — GitHub Actions workflow that runs the report
- **`requirements.txt`** — Python dependencies

## Running manually

```bash
python cold_wallet_report.py addresses.csv
```

Requires a `SLACK_WEBHOOK_URL` (and optionally `SLACK_WEBHOOK_URL_2` for a second
channel) environment variable set, or it'll just skip the Slack post and print
to console instead.

## Scheduling

This repo doesn't use GitHub's native cron — the workflow only listens for
`workflow_dispatch`. Scheduling is handled externally by **cron-job.org**,
which sends a POST request to GitHub's API once daily at 10am SGT to trigger
the workflow. This is intentional — GitHub's native cron can be delayed or
skipped on low-activity repos, so an external trigger is more reliable.

## Notes

- Balances with no reliable keyless data source (previously SC, ORDI) are
  excluded rather than shown as errors.
- If a live fetch fails for a chain, it currently defaults to `0.0000` rather
  than showing an error, to keep the Slack report clean. This means a genuine
  API outage could look identical to a real zero balance — worth being aware
  of if a number looks unexpectedly low.
- Address format validation happens before every balance fetch, so a
  malformed address in `addresses.csv` will show as `0.0000` rather than
  attempting a fetch against a bad address.
