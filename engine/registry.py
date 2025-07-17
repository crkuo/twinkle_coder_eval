"""
增強版註冊系統
基於 mmengine 設計，加入動態載入和 default_args 支援
"""
import inspect
import importlib
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union


class Registry:
    """
    增強版註冊表
    支援動態模組載入和 default_args
    """
    
    def __init__(self, name: str, build_func: Optional[Callable] = None, locations: List[str] = None):
        self._name = name
        self._module_dict: Dict[str, Type] = {}
        self._locations = locations or []
        self._imported = False
        self._build_func = build_func or self._default_build_func
        self.logger = logging.getLogger(__name__)
    
    def register_module(self, name: Optional[str] = None, force: bool = False):
        """
        註冊模組裝飾器
        
        Args:
            name: 註冊名稱，預設使用類名
            force: 是否強制覆蓋已存在的註冊
        """
        def _register(cls):
            module_name = name or cls.__name__
            
            if module_name in self._module_dict and not force:
                raise KeyError(f"'{module_name}' is already registered in {self._name}")
            
            self._module_dict[module_name] = cls
            return cls
        
        return _register
    
    def get(self, name: str) -> Optional[Type]:
        """
        獲取註冊的模組，支援動態載入
        
        Args:
            name: 模組名稱
            
        Returns:
            註冊的類或 None
        """
        # 首先嘗試從已註冊的模組獲取
        if name in self._module_dict:
            return self._module_dict[name]
        
        # 如果沒有找到，嘗試動態載入
        if not self._imported and self._locations:
            self._import_modules()
            if name in self._module_dict:
                return self._module_dict[name]
        
        return None
    
    def _import_modules(self):
        """
        動態載入指定位置的模組
        """
        if self._imported:
            return
        
        for location in self._locations:
            try:
                importlib.import_module(location)
                self.logger.debug(f"Successfully imported {location}")
            except ImportError as e:
                self.logger.warning(f"Failed to import {location}: {e}")
        
        self._imported = True
    
    def build(self, cfg: Dict[str, Any]) -> Any:
        """
        構建物件
        
        Args:
            cfg: 包含 'type' 欄位的配置字典
            
        Returns:
            構建的物件實例
        """
        return self._build_func(cfg, self)
    
    def _default_build_func(self, cfg: Dict[str, Any], registry: 'Registry') -> Any:
        """
        預設構建函數
        """
        cfg = cfg.copy()
        
        if 'type' not in cfg:
            raise KeyError("Config must contain 'type' field")
        
        obj_type = cfg.pop('type')
        obj_cls = registry.get(obj_type)
        
        # 根據類的 __init__ 方法簽名過濾參數
        init_signature = inspect.signature(obj_cls.__init__)
        valid_params = {}
        
        for param_name, param in init_signature.parameters.items():
            if param_name == 'self':
                continue
            
            if param_name in cfg:
                valid_params[param_name] = cfg[param_name]
            elif param.default is not inspect.Parameter.empty:
                # 使用預設值
                pass
            else:
                # 必要參數但未提供
                raise ValueError(f"Required parameter '{param_name}' not provided for {obj_cls.__name__}")
        
        return obj_cls(**valid_params)
    
    def list_modules(self) -> List[str]:
        """
        列出所有註冊的模組名稱
        """
        return list(self._module_dict.keys())
    
    def __contains__(self, name: str) -> bool:
        """
        檢查模組是否已註冊
        """
        return name in self._module_dict
    
    def __len__(self) -> int:
        """
        返回註冊模組數量
        """
        return len(self._module_dict)
    
    def __repr__(self) -> str:
        return f"Registry(name={self._name}, modules={len(self._module_dict)})"


# 便利函數
def build_from_cfg(cfg: Dict[str, Any], registry: Registry) -> Any:
    """
    從配置構建物件
    
    Args:
        cfg: 配置字典
        registry: 註冊表
        
    Returns:
        構建的物件
    """
    return registry.build(cfg)


# 全域註冊表
BACKENDS = Registry('backends')
BENCHMARKS = Registry('benchmarks')
EVALUATORS = Registry('evaluators')
MODELS = Registry('models')
DATASETS = Registry('datasets')


# 裝飾器別名
def register_backend(name: Optional[str] = None, force: bool = False):
    """註冊後端"""
    return BACKENDS.register_module(name, force)


def register_benchmark(name: Optional[str] = None, force: bool = False):
    """註冊基準測試"""
    return BENCHMARKS.register_module(name, force)


def register_evaluator(name: Optional[str] = None, force: bool = False):
    """註冊評估器"""
    return EVALUATORS.register_module(name, force)


def register_model(name: Optional[str] = None, force: bool = False):
    """註冊模型"""
    return MODELS.register_module(name, force)


def register_dataset(name: Optional[str] = None, force: bool = False):
    """註冊資料集"""
    return DATASETS.register_module(name, force)