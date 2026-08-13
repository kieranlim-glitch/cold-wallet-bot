"""
Balance fetcher for cold-wallet-bot addresses.
Covers: APT, AR, EGLD, FLOW, ICP, NEO, STX, SUI, VET, XNO
SC and ORDI are excluded — no reliable keyless balance source found.
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


def get_apt_balance(address: str) -> float:
    resource = "0x1::coin::CoinStore%3C0x1::aptos_coin::AptosCoin%3E"
    url = f"https://fullnode.mainnet.aptoslabs.com/v1/accounts/{address}/resource/{resource}"
    data = safe_get_json(url)
    octas = int(data["data"]["coin"]["value"])
    return octas / 1e8


def get_ar_balance(address: str) -> float:
    url = f"https://arweave.net/wallet/{address}/balance"
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    winston = int(r.text.strip())
    return winston / 1e12


def get_egld_balance(address: str) -> float:
    url = f"https://api.multiversx.com/accounts/{address}"
    data = safe_get_json(url)
    return int(data["balance"]) / 1e18


def get_flow_balance(address: str) -> float:
    url = f"https://rest-mainnet.onflow.org/v1/accounts/{address}"
    data = safe_get_json(url)
    return int(data["balance"]) / 1e8


def get_icp_balance(account_id: str) -> float:
    url = f"https://ledger-api.internetcomputer.org/accounts/{account_id}"
    data = safe_get_json(url)
    e8s = int(data.get("balance") or data.get("icp_balance") or 0)
    return e8s / 1e8


NEO_RPCS = [
    "https://mainnet1.neo.coz.io:443",
    "https://rpc10.n3.nspcc.ru:10331",
]
NEO_GAS_CONTRACT = "0xd2a4cff31913016155e38e474a2c06d08be276c"

def get_neo_gas_balance(address: str) -> float:
    payload = {"jsonrpc": "2.0", "method": "getnep17balances", "params": [address], "id": 1}
    last_err = None
    for rpc in NEO_RPCS:
        try:
            out = safe_post_json(rpc, payload)
            for bal in out["result"]["balance"]:
                if bal["assethash"].lower() == NEO_GAS_CONTRACT.lower():
                    return int(bal["amount"]) / 1e8
            return 0.0
        except Exception as e:
            last_err = str(e)
    raise RuntimeError(f"All NEO RPCs failed. Last error: {last_err}")


def get_stx_balance(address: str) -> float:
    url = f"https://api.hiro.so/extended/v1/address/{address}/balances"
    data = safe_get_json(url)
    microstacks = int(data["stx"]["balance"])
    return microstacks / 1e6


def get_sui_balance(address: str) -> float:
    payload = {"jsonrpc": "2.0", "id": 1, "method": "suix_getBalance", "params": [address]}
    out = safe_post_json("https://fullnode.mainnet.sui.io:443", payload)
    mist = int(out["result"]["totalBalance"])
    return mist / 1e9


def get_vet_balance(address: str) -> float:
    url = f"https://mainnet.vecha.in/accounts/{address}"
    data = safe_get_json(url)
    wei = int(data["balance"], 16)
    return wei / 1e18


def get_xno_balance(address: str) -> float:
    payload = {"action": "account_balance", "account": address}
    out = safe_post_json("https://rpc.nano-gpt.com", payload)
    raw = int(out["balance"])
    return raw / 1e30


BALANCE_FETCHERS = {
    "aptos":      get_apt_balance,
    "arweave":    get_ar_balance,
    "multiversx": get_egld_balance,
    "flow":       get_flow_balance,
    "icp":        get_icp_balance,
    "neo":        get_neo_gas_balance,
    "stacks":     get_stx_balance,
    "sui":        get_sui_balance,
    "vechain":    get_vet_balance,
    "nano":       get_xno_balance,
}
