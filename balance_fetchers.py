"""
Balance fetcher for cold-wallet-bot addresses.
Covers: APT, AR, ICP, SUI, VET
"""

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (ColdWalletBot/1.0)"}


def safe_get_json(url, timeout=25, headers=None):
    r = requests.get(url, headers=headers or HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


def safe_post_json(url, payload, timeout=25, headers=None):
    r = requests.post(url, json=payload, headers=headers or HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


# ── APT (Aptos) ──────────────────────────────────────────────────────────────

def get_apt_balance(address: str) -> float:
    url = "https://fullnode.mainnet.aptoslabs.com/v1/view"
    payload = {
        "function": "0x1::coin::balance",
        "type_arguments": ["0x1::aptos_coin::AptosCoin"],
        "arguments": [address],
    }
    out = safe_post_json(url, payload)
    octas = int(out[0])
    return octas / 1e8


# ── AR (Arweave) ─────────────────────────────────────────────────────────────

def get_ar_balance(address: str) -> float:
    url = f"https://arweave.net/wallet/{address}/balance"
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    winston = int(r.text.strip())
    return winston / 1e12


# ── ICP (Internet Computer) ──────────────────────────────────────────────────

def get_icp_balance(account_id: str) -> float:
    url = f"https://ledger-api.internetcomputer.org/accounts/{account_id}"
    data = safe_get_json(url)
    e8s = int(data["balance"])
    return e8s / 1e8


# ── SUI ──────────────────────────────────────────────────────────────────────

def get_sui_balance(address: str) -> float:
    url = "https://fullnode.mainnet.sui.io:443"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "suix_getBalance",
        "params": [address],  # add a 2nd param (coin type) here if you need a non-SUI coin
    }
    out = safe_post_json(url, payload)
    result = out.get("result", {})
    if "error" in out:
        raise RuntimeError(f"SUI RPC error: {out['error']}")
    total_balance = int(result["totalBalance"])
    return total_balance / 1e9  # SUI uses 9 decimals


# ── VET (VeChain) ────────────────────────────────────────────────────────────

def get_vet_balance(address: str) -> float:
    url = f"https://mainnet.veblocks.net/accounts/{address}"
    data = safe_get_json(url)
    # VeChain node API returns balance as a hex string in wei (18 decimals)
    balance_wei = int(data["balance"], 16)
    return balance_wei / 1e18


# ── Registry used by cold_wallet_report.py ───────────────────────────────────

BALANCE_FETCHERS = {
    "APT": get_apt_balance,
    "AR": get_ar_balance,
    "ICP": get_icp_balance,
    "SUI": get_sui_balance,
    "VET": get_vet_balance,
}
