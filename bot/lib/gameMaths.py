from ..cfg import cfg
import math


def truncItemSpawnResolution(num : float) -> float:
    """Truncate the passed float to itemSpawnRateResDP decimal places.

    :param float num: Float number to truncate
    :return: num, truncated to itemSpawnRateResDP decimal places
    :rtype: float
    """
    return math.trunc(num * math.pow(10, cfg.itemSpawnRateResDP)) / math.pow(10, cfg.itemSpawnRateResDP)
