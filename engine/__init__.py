"""
簡化版 Engine 模組
提供配置管理和註冊系統
"""
from .config import Config, ConfigDict, DictAction
from .registry import (
    Registry, 
    BACKENDS, BENCHMARKS, EVALUATORS, MODELS, DATASETS,
    register_backend, register_benchmark, register_evaluator, 
    register_model, register_dataset,
    build_from_cfg
)

__all__ = [
    # Config
    'Config', 'ConfigDict', 'DictAction',
    
    # Registry
    'Registry', 'build_from_cfg',
    'BACKENDS', 'BENCHMARKS', 'EVALUATORS', 'MODELS', 'DATASETS',
    'register_backend', 'register_benchmark', 'register_evaluator',
    'register_model', 'register_dataset'
]