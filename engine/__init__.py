# Engine: Standalone ConfigDict Implementation
# Extracted from MMEngine for independent use

from engine.config_dict import ConfigDict
from engine.lazy import LazyObject, LazyAttr
from .config import Config

__version__ = "1.0.0"
__all__ = ["ConfigDict", "LazyObject", "LazyAttr", "Config"]