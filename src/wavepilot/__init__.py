"""WavePilot adaptive OFDM modem."""

from .adaptation import LinkAdapter
from .channel import ChannelConfig, apply_channel
from .config import OFDMConfig
from .phy import DecodeError, OFDMModem, RxResult

__all__ = [
    "ChannelConfig",
    "DecodeError",
    "LinkAdapter",
    "OFDMConfig",
    "OFDMModem",
    "RxResult",
    "apply_channel",
]

__version__ = "0.1.0"

