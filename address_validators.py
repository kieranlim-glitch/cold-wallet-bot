"""
Address format validators for supported networks.
Each function returns True/False based on structural validation
(length, prefix, character set where applicable).
This does NOT verify the address is funded or "real" on-chain —
only that the format is structurally valid for that network.
"""
import re

HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


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


def is_valid_vechain(addr: str) -> bool:
    return _evm_style_valid(addr)


VALIDATORS = {
    "aptos":   is_valid_aptos,
    "arweave": is_valid_arweave,
    "icp":     is_valid_icp,
    "vechain": is_valid_vechain,
}


def validate_address(network_id: str, address: str) -> bool:
    validator = VALIDATORS.get(network_id)
    if validator is None:
        raise ValueError(f"No validator registered for network_id={network_id!r}")
    return validator(address)
