from typing import List, Optional, Any, Union, Tuple, Protocol, Dict, runtime_checkable
from dataclasses import dataclass, field
from geosampler import gpd
from geosampler.core.tile import tile, Overlap, TileSize
from geosampler.core.shape import load_polygon_from_wkt, print_gdf


@runtime_checkable
class TilerInterface(Protocol):

    def tile(self, options: Optional[Dict[Any, Any]]) -> gpd.GeoDataFrame:
        ...

    def print(self, filename: str, driver: Optional[str]):
        ...


@dataclass
class SimpleTiler:
    """"A dataclass.

    Parameters
    ----------
    x
        The first parameter.

    Attributes
    ----------
    x
        The first attribute.
    y
        The second attribute.
    """

    tile_size: Union[int, float, List[float], Tuple[float, float]]
    extent: Union[Optional[str], gpd.GeoDataFrame] = field(default=None)
    bounds: Union[Optional[str], List] = field(default=None)
    crs: Optional[Any] = field(default=None)
    debug: bool = False
    overlap: Union[Optional[int], float, List[float], Tuple[float, float]] = 0
    has_extent: bool = field(init=False)
    tiled_gdf: gpd.GeoDataFrame = field(init=False)
    ops: str = "intersects"
    strict_inclusion: bool = True

    def __post_init__(self):
        """"A dataclass.

        Parameters
        ----------
        x
            The first parameter.

        Attributes
        ----------
        x
            The first attribute.
        y
            The second attribute.
        """

        self._tile_size: TileSize = SimpleTiler.init_type(self.tile_size)
        if self.extent is not None:
            self.extent: gpd.GeoDataFrame = self.extent if isinstance(self.extent,
                                                                      gpd.GeoDataFrame) else gpd.read_file(self.extent)
            self.has_extent = True
            self.bounds = self.extent.bounds if self.bounds is None else self.bounds
            self.crs = self.extent.crs
        self._bounds: List = load_polygon_from_wkt(self.bounds).bounds if isinstance(self.bounds, str) else self.bounds

        if self.crs is None:
            raise AttributeError("crs variable has not been initialized, you can do it"
                                 "by initializing crs or by initializing the extent attribute")
        self._overlap: Overlap = [0.0, 0.0] if self.overlap is None else SimpleTiler.init_type(self.overlap)

    def tile(self, options: Optional[Dict[Any, Any]]) -> gpd.GeoDataFrame:
        """

        Returns
        -------
        gpd.GeoDataFrame

        """

        tile_generator = tile(bounds=self._bounds, tile_size=self._tile_size, overlap=self._overlap,
                              strict_inclusion=self.strict_inclusion)
        tmp_list: List[Dict] = [i for i in tile_generator]
        self.tiled_gdf = gpd.GeoDataFrame(tmp_list, crs=self.crs, geometry="geometry")
        return self.tiled_gdf

    def print(self, filename: str, driver: Optional[str] = None):
        print_gdf(self.tiled_gdf, filename, driver)

    @staticmethod
    def init_type(attr: Union[int, float, List[float], Tuple[float, float]]) -> List[float]:

        if isinstance(attr, int):
            return [float(attr), float(attr)]
        elif isinstance(attr, float):
            return [float(attr), float(attr)]
        else:
            return list(attr)
