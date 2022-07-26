import random
import logging
from dataclasses import dataclass, field
from typing import Union, Tuple, Protocol, runtime_checkable, Callable, List, Optional, Dict

import geopandas as gpd

from .tile import SimpleTiler, QuadTreeTiler
from ..core.types import URI


logger = logging.getLogger(__name__)


@runtime_checkable
class SamplingInterface(Protocol):

    def sample(self) -> Union[gpd.GeoDataFrame, Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]]: ...


@dataclass
class SimpleTiledSamplingInterface:

    tiler: SimpleTiler

    def _get_tiled_gdf(self) -> gpd.GeoDataFrame:
        if isinstance(self.tiler.tiled_gdf, gpd.GeoDataFrame):
            return self.tiler.tiled_gdf
        else:
            return self.tiler.tile()

    @staticmethod
    def _get_output(gdf) -> Union[gpd.GeoDataFrame, Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]]:
        point_gdf = gdf.apply(lambda x: x.geometry.centroid, axis=1)
        point_gdf = gpd.GeoDataFrame(point_gdf, crs=gdf.crs)
        output = (gdf, point_gdf)
        return output


@dataclass
class QuadTreeSamplingInterface:

    tiler: QuadTreeTiler


@dataclass
class GridSampling(SamplingInterface, SimpleTiledSamplingInterface, Callable):

    def sample(self) -> Union[gpd.GeoDataFrame, Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]]:

        return GridSampling._get_output(gdf=self._get_tiled_gdf())

    def __call__(self) -> Union[gpd.GeoDataFrame, Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]]:
        return self.sample()


@runtime_checkable
class PickableSamplingInterface(Protocol):

    n_sample: int = 50


@dataclass
class RandomSampling(SamplingInterface, SimpleTiledSamplingInterface, PickableSamplingInterface):
    n_sample: int = 50

    def sample(self) -> Union[gpd.GeoDataFrame, Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]]:

        gdf = self._get_tiled_gdf()
        if self.n_sample > len(gdf):
            logger.warning(f"""
            you have requested a number of sample
            superior to the number of unit of your tiled extent:
            number of sample requested {self.n_sample}, number of tile possible: {len(gdf)}
            We have returned the number of possible tile
            """)
            return self._get_output(gdf=gdf)

        gdf = gdf.sample(n=self.n_sample)
        return GridSampling._get_output(gdf=gdf)


@dataclass
class MaskedSamplingInterface:

    n_sample: Union[Dict, int] = 50
    mask: Optional[URI] = None
    field_name: Optional[str] = None
    min_percentage_of_intersection: Optional[float] = None
    max_percentage_of_intersection: Optional[float] = None
    _n_sample: Union[Dict, int] = field(init=False)


@dataclass
class WeightedCyclicIteratorInterface:
    weights: Union[str, List, None] = field(default=None)
    interval: int = 1
    random_starting_point: bool = True
    max_cycle_number: int = 1


@dataclass
class SystematicSampling(SamplingInterface, WeightedCyclicIteratorInterface, SimpleTiledSamplingInterface):
    """
    from wikipedia:
    systematic sampling is a statistical method
    involving the selection of elements
    from an ordered sampling frame. The most common form
    of systematic sampling is an equiprobability method.
    In this approach, progression through the list is treated circularly,
    with a return to the top once the end of the list is passed.
    The sampling starts by selecting an element from the list at
    random and then every kth element in the frame is selected, where k,
    is the sampling interval (sometimes known as the skip): this is calculated as:[1]
    k = N / n

    Parameters
    ----------


    References
    ----------
    Wikipedia article on systematic sampling
    .. _web_link: https://en.wikipedia.org/wiki/Systematic_sampling

    """

    oversampling: bool = False
    _starting_point: int = field(init=False)
    _picked: List = field(init=False, default_factory=lambda: list())
    _sample_polygon : bool = field(init=False, default=False)

    def __post_init__(self):
        self._get_tiled_gdf()
        self._starting_point = random.randint(0, len(self.tiler.tiled_gdf) - 1) \
            if self.random_starting_point is True else 0
        match self.weights:
            case None:
                self.weights = [1 for i in range(len(self.tiler.tiled_gdf))]
            case str():
                self.weights = self.tiler.tiled_gdf[self.weights]
            case list():
                assert len(self.weights) == len(self.tiler.tiled_gdf)

    def sample(self) -> Union[gpd.GeoDataFrame, Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]]:
        ...
