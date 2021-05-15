import pstats
from pstats import SortKey
p = pstats.Stats("profiler_data")
p.strip_dirs().sort_stats(SortKey.CUMULATIVE).print_stats(100)
