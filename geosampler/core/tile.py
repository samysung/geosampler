from typing import List, Optional, Any
from geosampler import gpd, np
from geosampler.core.shape import create_box_from_bounds, box


def tile(bounds: List, crs: Any, tile_size: Optional[int, List] = 256, overlap: Optional[int, List] = 0,
         strict_inclusion: bool = True) -> gpd.GeoDataFrame:
    """
    Simple function to tile with a regular step in X-axis and Y-axis
    Parameters
    ----------
    bounds : list
        bounds of extent to tile
    crs : crs of extent to tile in any Proj compatible format
    tile_size :
    overlap
    strict_inclusion

    Returns
    -------

    """
    gdf: gpd.GeoDataFrame
    min_x, min_y = bounds[0], bounds[1]
    max_x, max_y = bounds[2], bounds[3]
    tile_size = tile_size if isinstance(tile_size, List) else [tile_size, tile_size]
    overlap = overlap if isinstance(overlap, List) else [overlap, overlap]
    step = [
        tile_size[0] - (2 * overlap[0]),
        tile_size[1] - (2 * overlap[1])
    ]
    tmp_list = []
    for i in np.arange(min_x - overlap[0], max_x + overlap[0], step[0]):

        for j in np.arange(min_y - overlap[1], max_y + overlap[1], step[1]):

            "handling case where the extent is not a multiple of step"
            if i + tile_size[0] > max_x + overlap[0] and strict_inclusion:
                i = max_x + overlap[0] - tile_size[0]

            if j + tile_size[1] > max_y + overlap[1] and strict_inclusion:
                j = max_y + tile_size[1] - tile_size[1]

            left = i
            right = i + tile_size
            bottom = j
            top = j + tile_size
            bbox: box = _create_box_from_bounds(left, bottom, right, top)

            row_d = {
                "id": f"{left}-{bottom}-{right}-{top}",
                "geometry": bbox
            }
            tmp_list.append(row_d)

    gdf = gpd.GeoDataFrame(tmp_list, crs=crs, geometry="geometry")
    return gdf
