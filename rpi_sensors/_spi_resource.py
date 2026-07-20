"""Reference-counted SPI leases shared by every MCP3208 sensor class."""

from dataclasses import dataclass
from threading import RLock
from typing import Iterable, List, Protocol, Tuple

from . import _pi4gpio_backend
from ._validation import require_non_negative_int

SpiKey = Tuple[str, int, int]


class SpiLike(Protocol):
    def xfer2(self, data: Iterable[int]) -> Iterable[int]: ...

    def close(self) -> None: ...


@dataclass
class _Entry:
    spi: SpiLike
    users: int = 0


_entries: dict[SpiKey, _Entry] = {}
_entries_lock = RLock()


def _open_spi(backend: str, bus: int, device: int) -> SpiLike:
    if backend == "pi4gpio":
        client = _pi4gpio_backend.get_pi4gpio_client()
        return _pi4gpio_backend.Pi4gpioSpiTransferShim(client, bus, device)

    import spidev

    spi = spidev.SpiDev()
    spi.open(bus, device)
    spi.max_speed_hz = 1_000_000
    return spi


class SpiLease:
    """An idempotently closable reference to one shared SPI connection."""

    def __init__(self, key: SpiKey, spi: SpiLike):
        self._key = key
        self._spi = spi
        self._closed = False

    def xfer2(self, data: Iterable[int]) -> List[int]:
        if self._closed:
            raise RuntimeError("SPI connection is closed")
        return list(self._spi.xfer2(list(data)))

    def close(self) -> None:
        if self._closed:
            return
        with _entries_lock:
            if self._closed:
                return
            self._closed = True
            entry = _entries.get(self._key)
            if entry is None:
                return
            entry.users -= 1
            if entry.users == 0:
                entry.spi.close()
                del _entries[self._key]


def acquire_spi(bus: int = 0, device: int = 0) -> SpiLease:
    bus = require_non_negative_int("spi_bus", bus)
    device = require_non_negative_int("spi_device", device)
    backend = _pi4gpio_backend.get_backend()
    key = (backend, bus, device)

    with _entries_lock:
        entry = _entries.get(key)
        if entry is None:
            entry = _Entry(_open_spi(backend, bus, device))
            _entries[key] = entry
        entry.users += 1
        return SpiLease(key, entry.spi)


def _reset_for_tests() -> None:
    """Close and clear all resources; intended for isolated tests only."""
    with _entries_lock:
        for entry in _entries.values():
            entry.spi.close()
        _entries.clear()
