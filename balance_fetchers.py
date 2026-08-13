"""
Balance fetcher for cold-wallet-bot addresses.
Covers: APT, AR, EGLD, FLOW, ICP, NEO, STX, SUI, VET, XNO, ZIL
SC and ORDI are excluded — no reliable keyless balance source found.

Verified against live debug output on 2026-08-13:
  - EGLD, ICP, STX, VET: confirmed correct, unchanged.
  - APT: fixed — switched from CoinStore resource lookup (404s on
    FA-migrated accounts) to the 0x1::coin::balance view function.
  - NEO: fixed — GAS contract hash was missing its last character.
  - SUI: fixed — public JSON-RPC is deprecated; switched to GraphQL.
  - ZIL: added — bech32-to-hex decode + Zilliqa JSON-RPC GetBalance.
    NOT yet live-verified; sanity-check against zilscan.io before trusting.
"""

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (ColdWalletBot/1.0)"}
BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def safe_get_json(url, timeout=25, headers=None):
    r = requests.get(url, headers=headers or HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


def safe_post_json(url, payload, timeout=25, headers=None):
    r = requests.post(url, json=payload, headers=headers or HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


# ── APT (Aptos) — view function instead of CoinStore resource ───────────────

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


# ── EGLD (MultiversX) ────────────────────────────────────────────────────────

def get_egld_balance(address: str) -> float:
    url = f"https://api.multiversx.com/accounts/{address}"
    data = safe_get_json(url)
    return int(data["balance"]) / 1e18


# ── FLOW ─────────────────────────────────────────────────────────────────────

def get_flow_balance(address: str) -> float:
    url = f"https://rest-mainnet.onflow.org/v1/accounts/{address}"
    data = safe_get_json(url)
    return int(data["balance"]) / 1e8


# ── ICP (Internet Computer) ──────────────────────────────────────────────────

def get_icp_balance(account_id: str) -> float:
    url = f"https://ledger-api.internetcomputer.org/accounts/{account_id}"
    data = safe_get_json(url)
    e8s = int(data["balance"])
    return e8s / 1e8


# ── NEO N3 ───────────────────────────────────────────────────────────────────

NEO_RPCS = [
    "https://mainnet1.neo.coz.io:443",
    "https://rpc10.n3.nspcc.ru:10331",
]
NEO_GAS_CONTRACT = "0xd2a4cff31913016155e38e474a2c06d08be276cf"

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


# ── STX (Stacks) ─────────────────────────────────────────────────────────────

def get_stx_balance(address: str) -> float:
    url = f"https://api.hiro.so/extended/v1/address/{address}/balances"
    data = safe_get_json(url)
    microstacks = int(data["stx"]["balance"])
    return microstacks / 1e6


# ── SUI — GraphQL (public JSON-RPC deprecated) ───────────────────────────────

def get_sui_balance(address: str) -> float:
    query = """
    query GetBalance($owner: SuiAddress!) {
      address(address: $owner) {
        balance(type: "0x2::sui::SUI") {
          totalBalance
        }
      }
    }
    """
    payload = {"query": query, "variables": {"owner": address}}
    out = safe_post_json("https://sui-mainnet.mystenlabs.com/graphql", payload)
    if "errors" in out:
        raise RuntimeError(f"Sui GraphQL error: {out['errors']}")
    bal = out["data"]["address"]["balance"]
    mist = int(bal["totalBalance"]) if bal else 0
    return mist / 1e9


# ── VET (VeChain) ────────────────────────────────────────────────────────────

def get_vet_balance(address: str) -> float:
    url = f"https://mainnet.vecha.in/accounts/{address}"
    data = safe_get_json(url)
    wei = int(data["balance"], 16)
    return wei / 1e18


# ── XNO (Nano) ───────────────────────────────────────────────────────────────

def get_xno_balance(address: str) -> float:
    payload = {"action": "account_balance", "account": address}
    out = safe_post_json("https://rpc.nano-gpt.com", payload)
    raw = int(out["balance"])
    return raw / 1e30


# ── ZIL (Zilliqa) ────────────────────────────────────────────────────────────

def _convertbits(data, frombits, tobits, pad=True):
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def _zil_bech32_to_hex(addr: str) -> str:
    """
    Zilliqa bech32 addresses encode the raw 20-byte address hash directly
    (no witness-version byte, unlike Bitcoin segwit). Decodes 'zil1...'
    to the hex address Zilliqa's RPC expects.
    """
    if not addr.startswith("zil1"):
        raise ValueError("Not a Zilliqa bech32 address")
    payload_str = addr[4:]
    try:
        data = [BECH32_CHARSET.index(c) for c in payload_str]
    except ValueError:
        raise ValueError("Invalid bech32 characters in address")
    payload = data[:-6]  # drop 6-char checksum
    raw_bytes = _convertbits(payload, 5, 8, pad=False)
    if raw_bytes is None or len(raw_bytes) != 20:
        raise ValueError("Decoded Zilliqa address is not 20 bytes")
    return bytes(raw_bytes).hex()


def get_zil_balance(address: str) -> float:
    hex_addr = _zil_bech32_to_hex(address)
    payload = {
        "id": "1",
        "jsonrpc": "2.0",
        "method": "GetBalance",
        "params": [hex_addr],
    }
    out = safe_post_json("https://api.zilliqa.com/", payload)
    if "error" in out:
        if "Account is not created" in str(out["error"]):
            return 0.0
        raise RuntimeError(f"Zilliqa RPC error: {out['error']}")
    qa = int(out["result"]["balance"])
    return qa / 1e12


# ── Registry ─────────────────────────────────────────────────────────────────

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
    "zilliqa":    get_zil_balance,
}
