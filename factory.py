import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([os.path.dirname(ROOT), os.path.dirname(os.path.dirname(ROOT))])

from benchmark.MBPP.MBPP import MBPP

class BenchmarkFactory:
    @staticmethod
    def get_task(args):
        if args.task == "MBPP":
            return MBPP(name = args.task,
                        prompt_type = args.prompt_type)
        else:   
            raise ValueError("Unknown Task type")