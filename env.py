import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BENCHMARK_FOLDER = os.path.join(ROOT, "benchmark")
DATASET_CACHE_FOLDER = os.path.join(ROOT, 'cache')

del os, sys