"""Frame parser/encoder for E Smart / SmartLive UDP frames.

This module is pure offline byte handling — it never opens a socket.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

AES_KEY_DEFAULT = b"1234567890ABCDEF"
MAGIC = b"\x1a\x3b\x5d\x7c"

STREAM_TABLE = bytes.fromhex(
    "7c9ce84a13dedcb22f2123e4307b3d8c12b319ad748a2940f52dbea559e0f479"
    "d24bce89c6912ba282488425fb8fe9a6781a6f706ba4bda9815351869785efc1"
    "1fc4dba1c2ebd901ac0f952c5ced39b737d8e1020aae5f1cc573094e6924906d"
    "88ab43c00db545384f502266207f075b14981d9ba72ab9a85dd5f8e58d9f77ff"
    "6a80dfe2bf10d775645776f355cdd0c8b09e3f65f603312ecbf1fc4947063eb1"
    "945eee54110e043a34dd4df9ecc7c9e3336c567eb4a0fd7afaba3b05b8158783"
    "bc0b270c3cf79ae708719600bb26af422872d18b5ad6da9358feaacc6e1bf0a3"
    "18e6364162cf99f2324c67606192cad3ea637d16b68ed46835c3529d46441e17"
)


def _aes_ecb_block(block: bytes, key: bytes, decrypt: bool = False) -> bytes:
    if len(block) != 16 or len(key) != 16:
        raise ValueError("AES block/key must be 16 bytes")
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    op = cipher.decryptor() if decrypt else cipher.encryptor()
    return op.update(block) + op.finalize()


def checksum4(buf: bytes) -> bytes:
    """Direct-AP checksum variant for SMART_d139 frames."""
    out = [0x43, 0x53, 0x32, 0x4E]
    if not buf:
        return bytes(out)
    last = len(buf) - 1
    for i, b in enumerate(buf):
        out[0] = ((0x4E ^ b) ^ out[0]) & 0xFF
        if i % 2 == 0:
            out[1] = ((buf[last - i] ^ out[0]) ^ out[1]) & 0xFF
        if i % 3 >= 2:
            out[2] = ((b ^ out[1]) ^ out[2]) & 0xFF
        if i % 5 >= 3:
            out[3] = ((buf[last - i] ^ out[2]) ^ out[3]) & 0xFF
    return bytes(out)


def checksum4_cs2n(buf: bytes) -> bytes:
    """LAN CS2N checksum variant used by IOT/XWPSS frames."""
    out = [0x43, 0x53, 0x32, 0x4E]
    if not buf:
        return bytes(out)
    last = len(buf) - 1
    for i, b in enumerate(buf):
        out[0] = ((out[3] ^ b) ^ out[0]) & 0xFF
        if i % 2 == 0:
            out[1] = ((buf[last - i] ^ out[0]) ^ out[1]) & 0xFF
        if i % 3 >= 2:
            out[2] = ((b ^ out[1]) ^ out[2]) & 0xFF
        if i % 5 >= 3:
            out[3] = ((buf[last - i] ^ out[2]) ^ out[3]) & 0xFF
    return bytes(out)


def stream_encrypt(plain: bytes, ctx4: bytes, table: bytes = STREAM_TABLE) -> bytes:
    if len(ctx4) != 4:
        raise ValueError("ctx4 must be 4 bytes")
    if not plain:
        return b""
    out = bytearray(len(plain))
    prev = table[ctx4[0]] ^ plain[0]
    out[0] = prev
    for i in range(1, len(plain)):
        prev = table[(ctx4[prev & 3] + prev) & 0xFF] ^ plain[i]
        out[i] = prev
    return bytes(out)


def stream_decrypt(cipher: bytes, ctx4: bytes, table: bytes = STREAM_TABLE) -> bytes:
    if len(ctx4) != 4:
        raise ValueError("ctx4 must be 4 bytes")
    if not cipher:
        return b""
    out = bytearray(len(cipher))
    out[0] = table[ctx4[0]] ^ cipher[0]
    for i in range(1, len(cipher)):
        prev_cipher = cipher[i - 1]
        out[i] = table[(ctx4[prev_cipher & 3] + prev_cipher) & 0xFF] ^ cipher[i]
    return bytes(out)


@dataclass
class Frame:
    checksum: bytes
    nonce: bytes
    length: int
    version: int
    state: int
    payload: bytes
    checksum_ok: bool
    checksum_ok_cs2n: bool = False


def parse_frame(packet: bytes, key: bytes = AES_KEY_DEFAULT) -> Frame:
    if len(packet) < 16:
        raise ValueError("packet too short")
    hdr = _aes_ecb_block(packet[:16], key, decrypt=True)
    csum = hdr[:4]
    nonce = hdr[4:8]
    magic = hdr[8:12]
    ln = int.from_bytes(hdr[12:14], "big")
    ver = hdr[14]
    state = hdr[15]
    if magic != MAGIC:
        raise ValueError(f"bad magic after AES decrypt: {magic.hex()}")
    payload_cipher = packet[16:ln]
    payload = stream_decrypt(payload_cipher, nonce, STREAM_TABLE)
    chk_input = hdr[4:16] + payload
    calc = checksum4(chk_input)
    calc_cs2n = checksum4_cs2n(chk_input)
    return Frame(csum, nonce, ln, ver, state, payload, csum == calc, csum == calc_cs2n)


def encode_frame(
    payload: bytes,
    state: int = 0x40,
    key: bytes = AES_KEY_DEFAULT,
    nonce: bytes | None = None,
    checksum_algo: str = "direct",
) -> bytes:
    if len(payload) > 0xFFFF - 16:
        raise ValueError("payload too long")
    nonce = nonce or os.urandom(4)
    hdr_tail = nonce + MAGIC + (len(payload) + 16).to_bytes(2, "big") + bytes([1, state & 0xFF])
    if checksum_algo == "direct":
        csum = checksum4(hdr_tail + payload)
    elif checksum_algo in ("cs2n", "lan"):
        csum = checksum4_cs2n(hdr_tail + payload)
    else:
        raise ValueError(f"unknown checksum_algo {checksum_algo!r}")
    hdr = csum + hdr_tail
    return _aes_ecb_block(hdr, key, decrypt=False) + stream_encrypt(payload, nonce, STREAM_TABLE)
