"""Synchronous SmartLive LAN client for the TODO/T-AF05W air fryer.

Provides login, status read, and control (temp/time/fan/start/stop). The client
is synchronous; Home Assistant integrations wrap calls in an executor.
"""
from __future__ import annotations

import select
import socket
import time
from dataclasses import dataclass, field
from typing import Iterable

from .composer import inner_01_login, inner_06, inner_0d, rec
from .protocol import encode_frame, parse_frame
from .session import (
    DEFAULT_ARCH_IDENTITY,
    SmartLiveLanIdentity,
    build_iot_xwpss_prefix,
    build_session_probe_packet,
    lan_payload,
    parse_session_beacon,
)

DEFAULT_FRYER_PORT = 7066
DEFAULT_OPEN_PROBE_PORTS = (32708, 23982, 23976, 7066)
TEMP_MIN_C = 30
TEMP_MAX_C = 250
TIME_MIN_MIN = 1
TIME_MAX_MIN = 60
FAN_CHOICES = (1, 2, 3)


def discover_local_ip(fryer_ip: str) -> str:
    """Return the local IP the OS would use to reach ``fryer_ip``.

    Uses the UDP-connect-without-send idiom — no packet leaves the host.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect((fryer_ip, 1))
        return probe.getsockname()[0]


@dataclass
class StatusRecord:
    offset: int
    code: int
    value: int
    aux: list[int]
    raw: str


@dataclass
class AirFryerStatus:
    online: bool
    phase: str
    status_text: str
    status_code: int | None = None
    status_value: int | None = None
    remaining_min_bucket: int | None = None
    done_flag: bool | None = None
    seq: int | None = None
    records: list[StatusRecord] = field(default_factory=list)


def _inner_payload(packet: bytes) -> bytes:
    frame = parse_frame(packet)
    return frame.payload[64:] if len(frame.payload) >= 64 else b""


def _is_state_result(packet: bytes, magic_prefix: bytes) -> bool:
    try:
        return parse_frame(packet).state == 0x48 and _inner_payload(packet).startswith(magic_prefix)
    except Exception:
        return False


def decode_status_inner(inner: bytes) -> AirFryerStatus:
    if not inner.startswith(bytes.fromhex("5a4108")):
        raise ValueError(f"not a 5a4108 status response: {inner[:8].hex()}")
    seq = inner[-2] if len(inner) >= 2 else None
    records: list[StatusRecord] = []
    for off in range(8, max(8, len(inner) - 7)):
        chunk = inner[off : off + 8]
        if len(chunk) == 8 and chunk[0] == 0x71 and chunk[7] == 0x5A:
            records.append(
                StatusRecord(
                    offset=off,
                    code=chunk[1],
                    value=chunk[2],
                    aux=list(chunk[3:7]),
                    raw=chunk.hex(),
                )
            )
    phase = "unknown"
    status_text = "Status received"
    remaining_min_bucket: int | None = None
    status_code: int | None = None
    status_value: int | None = None
    done_flag: bool | None = None
    if records:
        first = records[0]
        status_code = first.code
        status_value = first.value
        if first.code == 0x03:
            phase = "cooking"
            status_text = "Cooking"
            remaining_min_bucket = first.value
            done_flag = False
        elif first.code == 0x00:
            remaining_min_bucket = 0
            done_flag = bool(len(first.aux) >= 3 and first.aux[2] == 0x40)
            phase = "done" if done_flag else "standby"
            status_text = "Done" if done_flag else "Standby"
    return AirFryerStatus(
        online=True,
        phase=phase,
        status_text=status_text,
        status_code=status_code,
        status_value=status_value,
        remaining_min_bucket=remaining_min_bucket,
        done_flag=done_flag,
        seq=seq,
        records=records,
    )


class AirFryerClient:
    """Synchronous LAN client. One instance = one query/control session."""

    def __init__(
        self,
        fryer_ip: str,
        client_ip: str | None = None,
        client_port: int = 0,
        password: bytes = b"fryme",
        arch_identity: str = DEFAULT_ARCH_IDENTITY,
        open_probe_ports: Iterable[int] = DEFAULT_OPEN_PROBE_PORTS,
    ) -> None:
        self.fryer_ip = fryer_ip
        self.client_ip = client_ip or discover_local_ip(fryer_ip)
        self.client_port = client_port
        self.password = password
        self.arch_identity = arch_identity
        self.open_probe_ports = tuple(open_probe_ports)
        self.sock: socket.socket | None = None
        self.session_port: int | None = None

    def __enter__(self) -> "AirFryerClient":
        self.open_socket()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def open_socket(self) -> None:
        if self.sock is not None:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.client_ip, self.client_port))
        # Pick up the OS-assigned port if we bound to 0 — it gets embedded in the LAN payload.
        self.client_port = sock.getsockname()[1]
        sock.setblocking(False)
        self.sock = sock

    def close(self) -> None:
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def _drain(self, seconds: float) -> list[tuple[tuple[str, int], bytes]]:
        if self.sock is None:
            raise RuntimeError("socket not open")
        end = time.time() + seconds
        out: list[tuple[tuple[str, int], bytes]] = []
        while time.time() < end:
            timeout = max(0.03, min(0.3, end - time.time()))
            r, _, _ = select.select([self.sock], [], [], timeout)
            if not r:
                continue
            try:
                data, addr = self.sock.recvfrom(4096)
            except BlockingIOError:
                continue
            out.append((addr, data))
        return out

    def _app_packet(self, inner: bytes, lower_counter: int, nonce: bytes) -> bytes:
        ident = SmartLiveLanIdentity(self.client_ip, self.client_port, lower_counter)
        return encode_frame(lan_payload(inner, ident), state=0x40, nonce=nonce, checksum_algo="lan")

    def _empty_poll(self, lower_counter: int, nonce: bytes) -> bytes:
        ident = SmartLiveLanIdentity(self.client_ip, self.client_port, lower_counter)
        return encode_frame(build_iot_xwpss_prefix(ident, inner_len=0), state=0x40, nonce=nonce, checksum_algo="lan")

    def _send(self, packet: bytes, port: int) -> None:
        if self.sock is None:
            raise RuntimeError("socket not open")
        self.sock.sendto(packet, (self.fryer_ip, port))

    def open_lower_session(self) -> int:
        if self.sock is None:
            self.open_socket()
        probe = build_session_probe_packet(self.arch_identity, nonce=b"\x05\x06\x07\x08")
        for port in self.open_probe_ports:
            self._send(probe, port)
            for addr, data in self._drain(1.5):
                try:
                    f = parse_frame(data)
                    if f.state == 0x71 and f.checksum_ok_cs2n and len(f.payload) == 32:
                        parse_session_beacon(f.payload)
                        self.session_port = addr[1]
                        return addr[1]
                except Exception:
                    continue
        raise TimeoutError("no state=0x71 lower-session ACK")

    def login(self, max_attempts: int = 20) -> int:
        port = self.session_port or self.open_lower_session()
        for attempt in range(1, max_attempts + 1):
            counter = 0x4A + attempt
            login_pkt = self._app_packet(
                inner_01_login(seq=attempt, password=self.password),
                counter,
                bytes([0x09, 0x0A, 0x0B, (0x0B + attempt) & 0xFF]),
            )
            self._send(login_pkt, port)
            replies = self._drain(0.25)
            for empty_idx in range(2):
                poll = self._empty_poll(counter, bytes([0xB0, 0xB1, attempt & 0xFF, empty_idx]))
                self._send(poll, port)
                replies.extend(self._drain(0.6))
            if any(_is_state_result(d, bytes.fromhex("5a410101")) for _, d in replies):
                for ack_round in range(1, 4):
                    self._send(self._empty_poll(counter, bytes([0xA1, 0xA2, 0xA3, ack_round])), port)
                    self._drain(0.35)
                return counter + 1
        raise TimeoutError("login state=0x48 result not observed")

    def get_status(self) -> AirFryerStatus:
        next_counter = self.login()
        port = self.session_port
        if port is None:
            raise RuntimeError("session port missing after login")
        base_seq = 0x13
        for batch in range(6):
            counter = next_counter + batch
            seq = base_seq + batch
            for repeat in range(5):
                pkt = self._app_packet(
                    inner_0d(seq=seq, password=self.password),
                    counter,
                    bytes([0x0D, 0x0E, batch & 0xFF, repeat & 0xFF]),
                )
                self._send(pkt, port)
                replies = self._drain(0.35)
                for empty_idx in range(2):
                    self._send(
                        self._empty_poll(counter, bytes([0xC0, batch & 0xFF, repeat & 0xFF, empty_idx])),
                        port,
                    )
                    replies.extend(self._drain(0.45))
                for _, data in replies:
                    if _is_state_result(data, bytes.fromhex("5a4108")):
                        return decode_status_inner(_inner_payload(data))
        raise TimeoutError("status state=0x48 / inner 5a4108 not observed")

    def _send_control(self, records: list[bytes], gap_s: float = 1.0) -> None:
        next_counter = self.login()
        port = self.session_port
        if port is None:
            raise RuntimeError("session port missing after login")
        if not records:
            return
        for idx, rec_group in enumerate(records):
            inner = inner_06([rec_group] if isinstance(rec_group, bytes) else rec_group,
                             seq=0x70 + idx, password=self.password)
            pkt = self._app_packet(
                inner,
                next_counter + idx,
                bytes([0x70 + idx * 2, 0x71 + idx * 2, idx & 0xFF, 0x00]),
            )
            self._send(pkt, port)
            self._drain(0.8 if idx < len(records) - 1 else 2.0)
            if idx < len(records) - 1:
                time.sleep(gap_s)

    def set_temperature(self, celsius: int) -> None:
        if not TEMP_MIN_C <= celsius <= TEMP_MAX_C:
            raise ValueError(f"temperature must be {TEMP_MIN_C}..{TEMP_MAX_C}C")
        self._send_control([[rec(0x03, celsius)]])

    def set_time(self, minutes: int) -> None:
        if not TIME_MIN_MIN <= minutes <= TIME_MAX_MIN:
            raise ValueError(f"minutes must be {TIME_MIN_MIN}..{TIME_MAX_MIN}")
        self._send_control([[rec(0x05, minutes)]])

    def set_fan(self, fan: int) -> None:
        if fan not in FAN_CHOICES:
            raise ValueError(f"fan must be one of {FAN_CHOICES}")
        self._send_control([[rec(0x09, fan)]])

    def power_on(self) -> None:
        self._send_control([[rec(0x01), rec(0x06), rec(0x06), rec(0x09, 1), rec(0x09, 2), rec(0x09, 3)]])

    def start(self) -> None:
        """Issue the cook-start sequence. Caller is responsible for safety gating."""
        self._send_control([[rec(0x0A), rec(0x02), rec(0x01), rec(0x06), rec(0x06),
                             rec(0x09, 1), rec(0x09, 2), rec(0x09, 3)]])

    def stop(self) -> None:
        self._send_control([[rec(0x0A), rec(0x0A), rec(0x02), rec(0x01), rec(0x06),
                             rec(0x06), rec(0x09, 1), rec(0x09, 2)]])
