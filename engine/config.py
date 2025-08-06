"""
簡化版配置系統
基於 mmengine 設計但適合 refactor 需求
"""
import copy
import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from argparse import Action


class ConfigDict(dict):
    """
    擴展的字典類，支持點操作符訪問
    簡化版本的 mmengine ConfigDict
    """
    
    def __init__(self, *args, **kwargs):
        # 避免遞迴問題
        object.__setattr__(self, '_initialized', False)
        super().__init__()
        
        # 處理初始化參數
        for arg in args:
            if isinstance(arg, dict):
                for key, value in arg.items():
                    self[key] = self._hook(value)
        
        for key, value in kwargs.items():
            self[key] = self._hook(value)
        
        object.__setattr__(self, '_initialized', True)
    
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        self[name] = value
    
    def __deepcopy__(self, memo):
        return ConfigDict(copy.deepcopy(dict(self), memo))
    
    def _hook(self, value):
        """轉換嵌套字典為 ConfigDict"""
        if isinstance(value, dict):
            return ConfigDict(value)
        elif isinstance(value, (list, tuple)):
            return type(value)(self._hook(item) for item in value)
        return value
    
    def __setitem__(self, key, value):
        super().__setitem__(key, self._hook(value))
    
    def merge_from_dict(self, options: Dict[str, Any]):
        """
        合併字典到配置中
        支持深度合併嵌套字典
        """
        def _merge_dict(source: dict, update: dict):
            for key, value in update.items():
                if key in source and isinstance(source[key], dict) and isinstance(value, dict):
                    _merge_dict(source[key], value)
                else:
                    source[key] = value
        
        _merge_dict(self, options)
    
    def dump(self, file_path: str):
        """保存配置到文件"""
        file_path = Path(file_path)
        
        # 轉換為普通字典
        def _to_dict(obj):
            if isinstance(obj, ConfigDict):
                return {k: _to_dict(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return type(obj)(_to_dict(item) for item in obj)
            return obj
        
        data = _to_dict(self)
        
        if file_path.suffix in ['.yml', '.yaml']:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")


class DictAction(Action):
    """
    命令行參數解析器
    用於解析 key=value 格式的參數
    """
    
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs == 0:
            raise ValueError('nargs for DictAction must be "*" or "+"')
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)
    
    def __call__(self, parser, namespace, values, option_string=None):
        options = {}
        for item in values:
            if '=' not in item:
                raise ValueError(f"Invalid format: {item}. Expected key=value")
            
            key, value = item.split('=', 1)
            
            # 嘗試解析值類型
            try:
                # 嘗試解析為數字
                if '.' in value:
                    value = float(value)
                else:
                    value = int(value)
            except ValueError:
                # 嘗試解析為布林值
                if value.lower() in ['true', 'false']:
                    value = value.lower() == 'true'
                # 否則保持為字符串
            
            # 支持嵌套鍵
            keys = key.split('.')
            current = options
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value
        
        setattr(namespace, self.dest, options)


class Config:
    """
    配置管理器
    簡化版本的 mmengine Config
    """
    
    def __init__(self, cfg_dict: Optional[Dict] = None, filename: Optional[str] = None):
        if cfg_dict is None:
            cfg_dict = {}
        
        self._cfg_dict = ConfigDict(cfg_dict)
        self._filename = filename
    
    @staticmethod
    def fromfile(filename: str, use_predefined_variables: bool = True) -> 'Config':
        """
        從文件載入配置
        """
        file_path = Path(filename)
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {filename}")
        
        # 載入基礎配置
        cfg_dict = Config._load_config_file(file_path)
        
        # 處理 _base_ 繼承
        if '_base_' in cfg_dict:
            base_cfg = Config._load_base_configs(cfg_dict['_base_'], file_path.parent)
            # 合併基礎配置和當前配置
            merged_cfg = Config._merge_configs(base_cfg, cfg_dict)
            # 移除 _base_ 鍵
            merged_cfg.pop('_base_', None)
            cfg_dict = merged_cfg
        
        return Config(cfg_dict, filename)
    
    @staticmethod
    def _load_config_file(file_path: Path) -> Dict:
        """載入配置文件"""
        if file_path.suffix in ['.yml', '.yaml']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        else:
            raise ValueError(f"Unsupported config file format: {file_path.suffix}")
    
    @staticmethod
    def _load_base_configs(base_configs: Union[str, List[str]], parent_dir: Path) -> Dict:
        """載入基礎配置"""
        if isinstance(base_configs, str):
            base_configs = [base_configs]
        
        merged_base = {}
        for base_path in base_configs:
            if not os.path.isabs(base_path):
                base_path = parent_dir / base_path
            
            base_cfg = Config._load_config_file(Path(base_path))
            merged_base = Config._merge_configs(merged_base, base_cfg)
        
        return merged_base
    
    @staticmethod
    def _merge_configs(base: Dict, override: Dict) -> Dict:
        """深度合併配置"""
        merged = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = Config._merge_configs(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        
        return merged
    
    def __getattr__(self, name):
        return getattr(self._cfg_dict, name)
    
    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            setattr(self._cfg_dict, name, value)
    
    def __getitem__(self, key):
        return self._cfg_dict[key]
    
    def __setitem__(self, key, value):
        self._cfg_dict[key] = value
    
    def __contains__(self, key):
        return key in self._cfg_dict
    
    def get(self, key, default=None):
        return self._cfg_dict.get(key, default)
    
    def keys(self):
        return self._cfg_dict.keys()
    
    def values(self):
        return self._cfg_dict.values()
    
    def items(self):
        return self._cfg_dict.items()
    
    def merge_from_dict(self, options: Dict[str, Any]):
        """合併配置"""
        self._cfg_dict.merge_from_dict(options)
    
    def dump(self, file_path: str):
        """保存配置"""
        self._cfg_dict.dump(file_path)
    
    def copy(self):
        """深度複製配置"""
        return Config(copy.deepcopy(self._cfg_dict), self._filename)
    
    def __repr__(self):
        return f"Config(filename={self._filename})"
    
    def __str__(self):
        return str(self._cfg_dict)