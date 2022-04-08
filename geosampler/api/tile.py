from typing import List, Optional, Any, Union, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from geosampler import gpd
from geosampler.core.tile import tile
from geosampler.core.shape import load_polygon_from_wkt


@dataclass
class ABCTiler(ABC):
    bounds: Optional[str, List]
    debug: bool

    @abstractmethod
    def tile(self) -> gpd.GeoDataFrame:
        pass


@dataclass
class SimpleTiler(ABCTiler):
    """
    """

    tile_size: Union[int, float, List[float, float], Tuple[float, float]]
    extent: Optional[str, gpd.GeoDataFrame] = field(default=None)
    bounds: Optional[str, List] = field(default=None)
    crs: Optional[Any] = field(default=None)
    debug: bool = False
    overlap: Optional[int, float, List[float, float], Tuple[float, float]] = 0
    has_extent: bool = field(init=False)
    tiled_gdf: gpd.GeoDataFrame = field(init=False)
    ops = "intersects"
    strict_inclusion: bool = True

    def __post_init__(self):

        self.tile_size = SimpleTiler.init_type(self.tile_size)
        if self.extent is not None:

            self.extent: gpd.GeoDataFrame = self.extent if isinstance(self.extent,
                                                                      gpd.GeoDataFrame) else gpd.read_file(self.extent)
            self.has_extent = True
            self.bounds = self.extent.bounds if self.bounds is None else self.bounds
            self.crs = self.extent.crs

        self.bounds = load_polygon_from_wkt(self.bounds).bounds if isinstance(self.bounds, str) else self.bounds
        if self.crs is None:
            raise AttributeError("crs variable has not been initialized, you can do it"
                                 "by initializing crs or by initializing the extent attribute")
        self.overlap = [0.0, 0.0] if self.overlap is None else SimpleTiler.init_type(self.overlap)

    def tile(self) -> gpd.GeoDataFrame:
        """

        Returns
        -------
        gpd.GeoDataFrame

        """
        self.tiled_gdf = tile(bounds=self.bounds, crs=self.crs, tile_size=self.tile_size, overlap=self.overlap,
                              strict_inclusion=self.strict_inclusion)
        return self.tiled_gdf

    @staticmethod
    def init_type(attr: Union[int, float, List[float, float], Tuple[float, float]]) -> List[float, float]:

        if isinstance(attr, int):
            return [float(attr), float(attr)]
        elif isinstance(attr, float):
            return [float(attr), float(attr)]
        else:
            return list(attr)
