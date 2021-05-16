import cProfile
import re

try:
    cProfile.run("import main", "profiler_data")
except KeyboardInterrupt:
    pass
finally:
    import pstats
    from pstats import SortKey
    p = pstats.Stats("profiler_data")
    p.strip_dirs().sort_stats(SortKey.CUMULATIVE).print_stats(100)
