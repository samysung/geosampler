import random
import logging
from dataclasses import dataclass, field
from typing import Union, Tuple, Protocol, runtime_checkable
from typing import Callable, List, Optional, Dict, Generator, Any, Sequence

import pandas as pd
import geopandas as gpd

from .tile import SimpleTiler, QuadTreeTiler
from ..core.sample import _weighted_cyclic_iterator
from ..core.types import URI
from ..core.shape import pick_one, intersection_reach_surface_criteria

logger = logging.getLogger(__name__)


@runtime_checkable
class SamplingInterface(Protocol):

    def sample(self) -> Union[gpd.GeoDataFrame, Sequence[gpd.GeoDataFrame], Dict[str, gpd.GeoDataFrame]]: ...


@dataclass
class SimpleTiledSamplingInterface:

    tiler: Union[URI, SimpleTiler]

    def get_tiled_gdf(self) -> gpd.GeoDataFrame:
        if isinstance(self.tiler, URI):
            return gpd.read_file(self.tiler)
        elif isinstance(self.tiler.tiled_gdf, gpd.GeoDataFrame):
            return self.tiler.tiled_gdf
        else:
            return self.tiler.tile()

    @staticmethod
    def get_output(gdf) -> Union[gpd.GeoDataFrame, Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]]:
        assert isinstance(gdf, gpd.GeoDataFrame)
        point_gdf = gdf.apply(lambda x: x.geometry.centroid, axis=1)
        point_gdf = gpd.GeoDataFrame(gdf, crs=gdf.crs, geometry="geometry")
        output = (gdf, point_gdf)
        return output


@dataclass
class QuadTreeSamplingInterface:

    tiler: QuadTreeTiler


@dataclass
class GridSampling(SamplingInterface, SimpleTiledSamplingInterface, Callable):

    def sample(self) -> Union[gpd.GeoDataFrame, Sequence[gpd.GeoDataFrame], Dict[str, gpd.GeoDataFrame]]:
        return GridSampling.get_output(gdf=self.get_tiled_gdf())

    def __call__(self) -> Union[gpd.GeoDataFrame, Sequence[gpd.GeoDataFrame], Dict[str, gpd.GeoDataFrame]]:
        return self.sample()


@dataclass
class PickableSamplingInterface:

    n_sample: int = 50


@dataclass
class RandomSampling(PickableSamplingInterface, GridSampling):

    def sample(self) -> Union[gpd.GeoDataFrame, Sequence[gpd.GeoDataFrame], Dict[str, gpd.GeoDataFrame]]:

        gdf = self.get_tiled_gdf()
        if self.n_sample > len(gdf):

            logger.warning(f"""
            you have requested a number of sample
            superior to the number of unit of your tiled extent:
            number of sample requested {self.n_sample}, number of tile possible: {len(gdf)}
            We have returned the number of possible tile
            """)

            return GridSampling.get_output(gdf=gdf)
        gdf = gdf.sample(n=self.n_sample)
        return GridSampling.get_output(gdf=gdf)


@dataclass
class MaskedSamplingInterface:

    n_sample: Union[Dict, int] = 50
    mask: Optional[URI] = None
    field_name: Optional[str] = None
    min_percentage: Optional[float] = None
    max_percentage: Optional[float] = None
    lazy_loading: bool = False
    _has_mask: bool = field(init=False, default=False)
    _mask: Union[URI, gpd.GeoDataFrame, None] = field(init=False, default=None)
    _n_sample: Union[Dict, int] = field(init=False)
    _sample_polygon: bool = field(init=False, default=False)
    _output_list: List = field(init=False, default_factory=lambda x: list())
    _output_polygon_list: List = field(init=False, default_factory=lambda x: list())
    _crs: Any = field(init=False, default=None)

    def init_mask_sampling_interface(self, tiled_gdf: gpd.GeoDataFrame):
        self._has_mask = self.mask is not None
        if self._has_mask:
            self._mask = gpd.read_file(self.mask) if self.lazy_loading is False else self.mask
        _n_sample_is_dict: bool = isinstance(self.n_sample, Dict)
        self._sample_polygon = _n_sample_is_dict
        self._n_sample = {key: 0 if _n_sample_is_dict else self.n_sample for key in self.n_sample.keys()}
        self._crs = tiled_gdf.crs

    def target_criteria(self) -> bool:
        match self.n_sample:
            case int():
                if self._n_sample >= self.n_sample:
                    return True
                else:
                    return False
            case dict():
                s = sum([1 if (self._n_sample[k] >= v) else 0 for k, v in self.n_sample.items()])
                return s >= len(self.n_sample.keys())

    def pick_one_polygon(self, row: pd.Series) -> Optional[gpd.GeoSeries]:

        if isinstance(self._mask, URI):
            gdf = gpd.read_file(self._mask, mask=row.geometry)
            return pick_one(gdf)

        else:
            bounds = row.geometry.bounds
            xmin, ymin, xmax, ymax = bounds[0], bounds[1], bounds[2], bounds[3]
            gdf = self._mask.cx[xmin: xmax, ymin:ymax]
            return pick_one(gdf)

    def box_reach_criteria(self, row: pd.Series) -> bool:
        row_gdf = gpd.GeoDataFrame([row.to_dict()])
        match [self.min_percentage is None, self.max_percentage is None]:
            case [True, True]:
                return True
            case [True, False]:
                return intersection_reach_surface_criteria(row_gdf,
                                                           self._mask,
                                                           criterion=self.max_percentage,
                                                           how='inferior')
            case [False, True]:
                return intersection_reach_surface_criteria(row_gdf,
                                                           self._mask,
                                                           criterion=self.min_percentage,
                                                           how='superior')
            case [False, False]:
                return bool(sum([intersection_reach_surface_criteria(row_gdf,
                                                                     self._mask,
                                                                     criterion=self.max_percentage,
                                                                     how='inferior'),
                                 intersection_reach_surface_criteria(row_gdf,
                                                                     self._mask,
                                                                     criterion=self.min_percentage,
                                                                     how='superior')
                                 ]
                                )
                            )

    def update_sampling_account(self, row: pd.Series, polygon_row: Optional[pd.Series] = None) -> None:
        if isinstance(self.n_sample, dict):
            self._n_sample[row[self.field_name]] += 1
        else:
            self._n_sample += 1
        self._output_list.append(row.to_dict())
        if self._sample_polygon:
            assert polygon_row is not None
            self._output_polygon_list.append(polygon_row)

    @property
    def crs(self):
        return self._crs

    @crs.setter
    def crs(self, crs):
        self._crs = crs

    @property
    def output_list(self):
        return self._output_list

    @property
    def output_polygon_list(self):
        return self._output_polygon_list

    @property
    def sample_polygon(self):
        return self._sample_polygon


@dataclass
class WeightedCyclicSamplingInterface(SamplingInterface):
    weights: Union[str, List, None] = field(default=None)
    interval: int = 1
    random_starting_point: bool = True
    max_cycle_number: int = 1
    oversampling: bool = False
    _weights: List = field(init=False)
    _starting_point: int = field(init=False)
    _picked: List = field(init=False, default_factory=lambda: list())
    _sample_generator: Generator[int, None, None] = field(init=False)

    def init_weighted_cyclic_interface(self, tiled_gdf: gpd.GeoDataFrame):

        self._starting_point = random.randint(0, len(tiled_gdf) - 1) \
            if self.random_starting_point is True else 0
        match self.weights:
            case None:
                self._weights = [1 for i in range(len(tiled_gdf))]
            case str():
                self._weights = tiled_gdf[self.weights]
            case list():
                assert len(self._weights) == len(tiled_gdf)
                self._weights = self.weights
        self._sample_generator = _weighted_cyclic_iterator(weights=self._weights,
                                                           interval=self.interval,
                                                           started_point=self._starting_point,
                                                           max_cycle=self.max_cycle_number)

    def get_next_index(self) -> Optional[int]:
        try:
            index = next(self._sample_generator)
            if index in self._picked and self.oversampling is False:
                return None
            else:
                self._picked.append(index)
                return index
        except StopIteration as si:
            raise si

    @property
    def sample_generator(self):
        return self._sample_generator


@dataclass
class SystematicSampling(WeightedCyclicSamplingInterface,
                         MaskedSamplingInterface,
                         SimpleTiledSamplingInterface):
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
    _tiled_gdf: gpd.GeoDataFrame = field(init=False)

    def __post_init__(self):

        self._tiled_gdf = self.get_tiled_gdf()
        self.init_mask_sampling_interface(self._tiled_gdf)
        self.init_weighted_cyclic_interface(self._tiled_gdf)

    def sample(self) -> Union[None, gpd.GeoDataFrame, Sequence[gpd.GeoDataFrame], Dict[str, gpd.GeoDataFrame]]:

        while self.target_criteria() is False:

            try:
                index = self.get_next_index()
                row = self._tiled_gdf[index]
                if self.sample_polygon:
                    polygon_row = self.pick_one_polygon(row)
                    if polygon_row is not None:
                        self.update_sampling_account(row, polygon_row)
                else:
                    if self.box_reach_criteria(row):
                        self.update_sampling_account(row)
            except StopIteration:
                logger.info(f'''you've reached the last iteration without reaching your criteria 
                your target criteria: {str(self.n_sample)}
                your number of sample reached: {str(self._n_sample)}''')

        return self.get_result()

    def get_result(self) -> Dict[str, gpd.GeoDataFrame]:

        box_gdf = gpd.GeoDataFrame(self.output_list, crs=self._tiled_gdf.crs, geometry="geometry")
        output_box = SimpleTiledSamplingInterface.get_output(box_gdf)
        if self.sample_polygon:
            polygon_gdf = gpd.GeoDataFrame(self.output_polygon_list, crs=self._tiled_gdf.crs, geometry="geometry")
            output_polygon = SimpleTiledSamplingInterface.get_output(polygon_gdf)
            return {'box': output_box[0],
                    'box_centroid': output_box[1],
                    'polygon': output_polygon[0],
                    'polygon_centroid': output_polygon[1]}
        else:
            return {'box': output_box[0],
                    'box_centroid': output_box[1]}
