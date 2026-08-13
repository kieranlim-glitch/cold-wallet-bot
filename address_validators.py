"""
Address format validators for supported networks.
Each function returns True/False based on structural validation
(length, prefix, character set where applicable).
This does NOT verify the address is funded or "real" on-chain —
only that the format is structurally valid for that network.
"""

import re


HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
BASE58_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]+$")
BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _is_hex(s: str, expected_len: int = None) -> bool:
    if not HEX_RE.match(s):
        return False
    if expected_len is not None and len(s) != expected_len:
        return False
    return True


def _evm_style_valid(addr: str) -> bool:
    """0x + 40 hex chars. Format-only check (no EIP-55 checksum)."""
    if not addr.startswith("0x"):
        return False
    return _is_hex(addr[2:], expected_len=40)


def _bech32_polymod(values):
    GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ v
        for i in range(5):
            chk ^= GEN[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp):
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _bech32_verify_checksum(hrp, data, const=1):
    return _bech32_polymod(_bech32_hrp_expand(hrp) + data) == const


def _bech32_decode(addr: str, expected_hrp: str, allow_bech32m: bool = False):
    if addr != addr.lower() and addr != addr.upper():
        return False
    addr = addr.lower()
    if "1" not in addr:
        return False
    pos = addr.rfind("1")
    hrp, data_part = addr[:pos], addr[pos + 1:]
    if hrp != expected_hrp:
        return False
    if len(data_part) < 6:
        return False
    try:
        data = [BECH32_CHARSET.index(c) for c in data_part]
    except ValueError:
        return False
    if _bech32_verify_checksum(hrp, data, const=1):
        return True
    if allow_bech32m and _bech32_verify_checksum(hrp, data, const=0x2bc830a3):
        return True
    return False


def is_valid_aptos(addr: str) -> bool:
    if not addr.startswith("0x"):
        return False
    return _is_hex(addr[2:], expected_len=64)


def is_valid_arweave(addr: str) -> bool:
    if len(addr) != 43:
        return False
    return re.match(r"^[A-Za-z0-9_-]+$", addr) is not None


def is_valid_icp(addr: str) -> bool:
    if _is_hex(addr, expected_len=64):
        return True
    principal_re = re.compile(r"^[a-z0-9]{5}(-[a-z0-9]{5}){9,}(-[a-z0-9]{1,5})?$")
    return bool(principal_re.match(addr))


def is_valid_sui(addr: str) -> bool:
    if not addr.startswith("0x"):
        return False
    return _is_hex(addr[2:], expected_len=64)


def is_valid_vechain(addr: str) -> bool:
    return _evm_style_valid(addr)


def is_valid_zilliqa(addr: str) -> bool:
    """Zilliqa: bech32, prefix 'zil1', standard bech32 (not bech32m)."""
    return _bech32_decode(addr, expected_hrp="zil")


VALIDATORS = {
    "aptos":   is_valid_aptos,
    "arweave": is_valid_arweave,
    "icp":     is_valid_icp,
    "sui":     is_valid_sui,
    "vechain": is_valid_vechain,
    "zilliqa": is_valid_zilliqa,
}


def validate_address(network_id: str, address: str) -> bool:
    validator = VALIDATORS.get(network_id)
    if validator is None:
        raise ValueError(f"No validator registered for network_id={network_id!r}")
    return validator(address)
