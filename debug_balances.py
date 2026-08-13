"""
Debug script — prints raw API responses for chains with suspicious
or errored output, so we can fix based on real data instead of guesses.
"""

import json
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (ColdWalletBot/1.0)"}

ADDR = {
    "EGLD": "erd10u3n46rkewzp9nqfnsx7vruz68vnvcfdwlsq38gysrf55z3ef7as54860a",
    "ICP":  "fe3e9427110f728a864c0cfa091126fa42897bc55fe4b8aca7df8fe21b040555",
    "NEO":  "Ncby6iv4U7F3pu8ErzBzfbGXmsPeq2XF6s",
    "STX":  "SP2RJJJYGANXRWZ9REH87E6MFXJQSV81JJHX34KD3",
    "SUI":  "0x8df8a81cf24f66f1ff2b22b5f091ccad944cc3499823b7b5d44e2b718b00de58",
    "VET":  "0x52e81a1f8c917987c28da71B4c84eb51cc3Cd3a9",
    "XNO":  "nano_1c8j1h5ujzgefuezziffeksy39xrcj84d4neo6eyhx1ze858ogikgmxhmeyq",
}


def show(label, resp):
    print(f"\n===== {label} =====")
    print(json.dumps(resp, indent=2)[:1500])


def main():
    # EGLD
    try:
        r = requests.get(f"https://api.multiversx.com/accounts/{ADDR['EGLD']}", headers=HEADERS, timeout=25)
        show("EGLD", r.json())
    except Exception as e:
        print(f"\n===== EGLD ERROR =====\n{e}")

    # ICP
    try:
        r = requests.get(f"https://ledger-api.internetcomputer.org/accounts/{ADDR['ICP']}", headers=HEADERS, timeout=25)
        show("ICP", r.json())
    except Exception as e:
        print(f"\n===== ICP ERROR =====\n{e}")

    # NEO
    try:
        payload = {"jsonrpc": "2.0", "method": "getnep17balances", "params": [ADDR["NEO"]], "id": 1}
        r = requests.post("https://mainnet1.neo.coz.io:443", json=payload, headers=HEADERS, timeout=25)
        show("NEO", r.json())
    except Exception as e:
        print(f"\n===== NEO ERROR =====\n{e}")

    # STX
    try:
        r = requests.get(f"https://api.hiro.so/extended/v1/address/{ADDR['STX']}/balances", headers=HEADERS, timeout=25)
        show("STX", r.json())
    except Exception as e:
        print(f"\n===== STX ERROR =====\n{e}")

    # SUI
    try:
        payload = {"jsonrpc": "2.0", "id": 1, "method": "suix_getBalance", "params": [ADDR["SUI"]]}
        r = requests.post("https://fullnode.mainnet.sui.io:443", json=payload, headers=HEADERS, timeout=25)
        show("SUI", r.json())
    except Exception as e:
        print(f"\n===== SUI ERROR =====\n{e}")

    # VET
    try:
        r = requests.get(f"https://mainnet.vecha.in/accounts/{ADDR['VET']}", headers=HEADERS, timeout=25)
        show("VET", r.json())
    except Exception as e:
        print(f"\n===== VET ERROR =====\n{e}")

    # XNO
    try:
        payload = {"action": "account_balance", "account": ADDR["XNO"]}
        r = requests.post("https://rpc.nano-gpt.com", json=payload, headers=HEADERS, timeout=25)
        show("XNO", r.json())
    except Exception as e:
        print(f"\n===== XNO ERROR =====\n{e}")


if __name__ == "__main__":
    main()
