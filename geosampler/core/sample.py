from typing import List
import logging
import numpy as np

logger = logging.getLogger(__name__)


def _increment_pointer(pointer, interval, max_pointer_value, actual_index):
    if pointer + interval >= max_pointer_value:
        pointer = (pointer + interval) % max_pointer_value
        actual_index = 0
        return pointer, actual_index
    else:
        return pointer + interval, actual_index


def _update_index(cumsum_weights: List,
                  actual_weight: int,
                  actual_index: int,
                  max_index: int) -> int:
    while True:
        if actual_index > max_index:
            actual_index = 0
        if actual_weight >= cumsum_weights[actual_index]:
            actual_index += 1
        else:
            return actual_index


def _weighted_cyclic_iterator(weights: List,
                              interval: int = 1,
                              started_point: int = 0,
                              max_cycle: int = 1):
    """

    Parameters
    ----------
    weights
    interval
    started_point
    max_cycle

    Returns
    -------

    """
    assert started_point < len(weights)
    cumsum_weights = list(np.cumsum(weights))
    # lookup_table = {cumsum_weights[i]: i for i in range(len(weights))}
    # print(f'lookup table: {lookup_table}')
    logger.debug(f"cumsum weights: {cumsum_weights}")
    """
    pointer = started_point
    logger.debug(f"pointer at start: {pointer}")
    max_val_pointer = len(weights) - 1
    logger.debug(f"max value of pointer: {max_val_pointer}")
    """
    index = started_point
    max_index = len(weights) - 1
    logger.debug(f'max index: {max_index}')
    pointer = cumsum_weights[started_point] - weights[started_point]
    logger.debug(f"weighted_pointer at start: {pointer}")
    start_pointer = pointer
    last_pointer = pointer
    max_pointer_value = cumsum_weights[len(weights) - 1]
    logger.debug(f"max value of weighted_pointer: {max_pointer_value}")
    n_cycle_completed = 0
    # picked_sample = list()  # list of pointed value already picked
    while True:

        if (last_pointer < start_pointer) and (pointer >= start_pointer):
            n_cycle_completed += 1
            logger.debug(f'number of cycle finished: {n_cycle_completed}')
            if n_cycle_completed >= max_cycle:
                logger.debug("end of routine, because max cycle has been reached")
                break  # max cycle iteration completed
        yield index
        logger.debug(f'index yielded {index}, pointer {pointer}, last pointer{last_pointer}')
        last_pointer = pointer
        pointer, index = _increment_pointer(pointer, interval, max_pointer_value, index)
        index = _update_index(cumsum_weights, pointer, index, max_index)
