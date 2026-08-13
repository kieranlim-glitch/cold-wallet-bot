"""
Address format validators for supported networks.
Each function returns True/False based on structural validation
(length, prefix, character set, checksum where applicable).
This does NOT verify the address is funded or "real" on-chain —
only that the format is structurally valid for that network.
"""

import re


# ── Helpers ──────────────────────────────────────────────────────────────────

HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
BASE58_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]+$")

BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _is_hex(s: str, expected_len: int = None) -> bool:
    if not HEX_RE.match(s):
        return False
    if expected_len is not None and len(s) != expected_len:
        return False
    return True


def _keccak256(data: bytes) -> bytes:
    """
    Minimal Keccak-256 (not SHA3-256 — different padding).
    Needed for EIP-55 checksum validation on EVM-style addresses.
    """
    RC = [
        0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
        0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
        0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
        0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
        0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
        0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
    ]
    offsets = [
        [0, 1, 62, 28, 27], [36, 44, 6, 55, 20], [3, 10, 43, 25, 39],
        [41, 45, 15, 21, 8], [18, 2, 61, 56, 14],
    ]

    def rol(x, s):
        return ((x << s) | (x >> (64 - s))) & 0xFFFFFFFFFFFFFFFF

    rate = 136  # 1088 bits for Keccak-256
    padded = bytearray(data)
    padded.append(0x01)
    while len(padded) % rate != 0:
        padded.append(0x00)
    padded[-1] ^= 0x80

    state = [[0] * 5 for _ in range(5)]

    for block_start in range(0, len(padded), rate):
        block = padded[block_start:block_start + rate]
        for i in range(rate // 8):
            x, y = (i // 5) % 5, i % 5
            lane = int.from_bytes(block[i * 8:i * 8 + 8], "little")
            state[x][y] ^= lane

        for rnd in range(24):
            C = [state[x][0] ^ state[x][1] ^ state[x][2] ^ state[x][3] ^ state[x][4] for x in range(5)]
            D = [C[(x - 1) % 5] ^ rol(C[(x + 1) % 5], 1) for x in range(5)]
            for x in range(5):
                for y in range(5):
                    state[x][y] ^= D[x]

            B = [[0] * 5 for _ in range(5)]
            for x in range(5):
                for y in range(5):
                    B[y][(2 * x + 3 * y) % 5] = rol(state[x][y], offsets[x][y])
            state = B

            T = [[0] * 5 for _ in range(5)]
            for x in range(5):
                for y in range(5):
                    T[x][y] = state[x][y] ^ ((~state[(x + 1) % 5][y]) & state[(x + 2) % 5][y])
            state = T

            state[0][0] ^= RC[rnd]

    out = bytearray()
    for i in range(4):
        x, y = (i // 5) % 5, i % 5
        out += state[x][y].to_bytes(8, "little")
    return bytes(out[:32])


def _eip55_checksum_valid(addr_hex_no_0x: str) -> bool:
    """EIP-55 mixed-case checksum for 40-hex-char EVM addresses."""
    addr_lower = addr_hex_no_0x.lower()
    hashed = _keccak256(addr_lower.encode("ascii"))
    hash_hex = hashed.hex()
    for i, c in enumerate(addr_hex_no_0x):
        if c.isalpha():
            bit = int(hash_hex[i], 16) >= 8
            if bit and c.islower():
                return False
            if not bit and c.isupper():
                return False
    return True


def _evm_style_valid(addr: str) -> bool:
    """
    0x + 40 hex chars. If the address is mixed-case, verify EIP-55
    checksum. All-lowercase or all-uppercase addresses skip checksum
    (that's the EIP-55 convention — checksum only applies to mixed case).
    """
    if not addr.startswith("0x"):
        return False
    body = addr[2:]
    if not _is_hex(body, expected_len=40):
        return False
    if body == body.lower() or body == body.upper():
        return True
    return _eip55_checksum_valid(body)


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
    """Generic bech32 / bech32m structural + checksum validator."""
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


# ── Per-chain validators ───────────────────────────────────────────────────

def is_valid_aptos(addr: str) -> bool:
    """Aptos: 0x + 64 hex chars (32-byte address, may be zero-padded)."""
    if not addr.startswith("0x"):
        return False
    return _is_hex(addr[2:], expected_len=64)


def is_valid_arweave(addr: str) -> bool:
    """Arweave: 43-char base64url string (256-bit hash)."""
    if len(addr) != 43:
        return False
    return re.match(r"^[A-Za-z0-9_-]+$", addr) is not None


def is_valid_dymension(addr: str) -> bool:
    """Dymension: Cosmos SDK bech32, prefix 'dym1'."""
    return _bech32_decode(addr, expected_hrp="dym")


def is_valid_multiversx(addr: str) -> bool:
    """MultiversX (EGLD): bech32, prefix 'erd1', 62 chars total."""
    if len(addr) != 62:
        return False
    return _bech32_decode(addr, expected_hrp="erd")


def is_valid_flow(addr: str) -> bool:
    """Flow: 0x + 16 hex chars (8-byte address)."""
    if not addr.startswith("0x"):
        return False
    return _is_hex(addr[2:], expected_len=16)


def is_valid_icp(addr: str) -> bool:
    """
    Internet Computer: supports two formats.
      - Account Identifier: 64 hex chars
      - Principal ID: base32-ish, dash-separated groups of 5, CRC32 suffix
    """
    if _is_hex(addr, expected_len=64):
        return True
    principal_re = re.compile(r"^[a-z0-9]{5}(-[a-z0-9]{5}){9,}(-[a-z0-9]{1,5})?$")
    return bool(principal_re.match(addr))


def is_valid_manta(addr: str) -> bool:
    """Manta Network: EVM-style, 0x + 40 hex chars, EIP-55 checksum if mixed case."""
    return _evm_style_valid(addr)


def is_valid_neo(addr: str) -> bool:
    """Neo N3: base58, 34 chars, starts with 'N'."""
    if len(addr) != 34 or not addr.startswith("N"):
        return False
    return bool(BASE58_RE.match(addr))


def is_valid_ordi_brc20(addr: str) -> bool:
    """
    Ordinals/BRC-20: Bitcoin address. Accepts Taproot (bc1p...) primarily,
    since that's the standard for inscriptions, but also allows legacy/
    segwit formats since BRC-20 wallets sometimes use those too.
    """
    if addr.startswith("bc1p"):
        return len(addr) == 62 and _bech32_decode(addr, expected_hrp="bc", allow_bech32m=True)
    if addr.startswith("bc1q"):
        return _bech32_decode(addr, expected_hrp="bc", allow_bech32m=False)
    if addr.startswith(("1", "3")):
        return 25 <= len(addr) <= 34 and bool(BASE58_RE.match(addr))
    return False


def is_valid_siacoin(addr: str) -> bool:
    """Siacoin: 76 hex chars (32-byte unlock hash + 8-char checksum)."""
    return _is_hex(addr, expected_len=76)


def is_valid_stacks(addr: str) -> bool:
    """Stacks: starts with 'SP' (mainnet) or 'SM' (mainnet multisig), ~38-41 chars."""
    if not addr.startswith(("SP", "SM")):
        return False
    return 38 <= len(addr) <= 41 and bool(re.match(r"^[A-Z0-9]+$", addr))


def is_valid_sui(addr: str) -> bool:
    """Sui: 0x + 64 hex chars (32-byte address)."""
    if not addr.startswith("0x"):
        return False
    return _is_hex(addr[2:], expected_len=64)


def is_valid_theta(addr: str) -> bool:
    """Theta: EVM-style, 0x + 40 hex chars, EIP-55 checksum if mixed case."""
    return _evm_style_valid(addr)


def is_valid_vechain(addr: str) -> bool:
    """VeChain: EVM-style, 0x + 40 hex chars, EIP-55 checksum if mixed case."""
    return _evm_style_valid(addr)


def is_valid_nano(addr: str) -> bool:
    """Nano: 'nano_' + 60 chars (52-char base32 payload + 8-char checksum)."""
    if not addr.startswith("nano_"):
        return False
    return len(addr) == 65


# ── Registry: network_id -> validator ───────────────────────────────────────

VALIDATORS = {
    "aptos":       is_valid_aptos,
    "arweave":     is_valid_arweave,
    "dymension":   is_valid_dymension,
    "multiversx":  is_valid_multiversx,
    "flow":        is_valid_flow,
    "icp":         is_valid_icp,
    "manta":       is_valid_manta,
    "neo":         is_valid_neo,
    "brc20":       is_valid_ordi_brc20,
    "siacoin":     is_valid_siacoin,
    "stacks":      is_valid_stacks,
    "sui":         is_valid_sui,
    "theta":       is_valid_theta,
    "vechain":     is_valid_vechain,
    "nano":        is_valid_nano,
}


def validate_address(network_id: str, address: str) -> bool:
    validator = VALIDATORS.get(network_id)
    if validator is None:
        raise ValueError(f"No validator registered for network_id={network_id!r}")
    return validator(address)
