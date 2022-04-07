from typing import Protocol, List
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from geosampler import gpd


class Tiler(Protocol):
    pass


@dataclass
class Tile(ABC):

    extent_file: str
    debug: bool = False
    bounds: list = field(default=None)
    step: int = 50
    tile_size: int = 256
    ops: str = "intersects"
    strict_inclusion: bool = True

    @abstractmethod
    def tiling(self):
        pass

