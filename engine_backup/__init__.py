# Copyright (c) OpenMMLab. All rights reserved.
from .config import Config, DictAction
from .registry import Registry
from .fileio import dump, load
from .utils import *

__all__ = [
    'Config', 'DictAction', 'Registry', 'dump', 'load'
]