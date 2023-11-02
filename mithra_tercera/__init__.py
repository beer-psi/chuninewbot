import logging
from typing import NamedTuple, Literal


class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: Literal["alpha", "beta", "candidate", "final"]
    serial: int


__title__ = "mithratercera"
__author__ = "beerpsi"
__license__ = "0BSD"
__copyright__ = "Copyright 2023-present beerpsi"
__version__ = "0.3.0a"

version_info: VersionInfo = VersionInfo(
    major=0,
    minor=3,
    micro=0,
    releaselevel="alpha",
    serial=0,
)

logging.getLogger(__name__).addHandler(logging.NullHandler())

del logging, NamedTuple, Literal, VersionInfo
