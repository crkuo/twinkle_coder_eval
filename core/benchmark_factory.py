"""
基準測試工廠模組
專門處理基準測試實例化
"""
import importlib
import inspect
import logging
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from ..engine import BENCHMARKS, Config, ConfigDict


class BenchmarkFactory:
    """
    基準測試工廠
    負責管理和實例化各種基準測試 (MBPP, HumanEval, etc.)
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._discover_and_register_benchmarks()
    
    def _discover_and_register_benchmarks(self):
        """
        自動發現並註冊可用的基準測試
        """
        benchmark_base_path = Path(__file__).parent.parent / 'benchmark'
        
        if not benchmark_base_path.exists():
            self.logger.warning(f"Benchmark directory not found: {benchmark_base_path}")
            return
        
        # 掃描 benchmark 目錄
        for benchmark_dir in benchmark_base_path.iterdir():
            if benchmark_dir.is_dir() and benchmark_dir.name not in ['__pycache__']:
                self._try_load_benchmark(benchmark_dir)
    
    def _try_load_benchmark(self, benchmark_dir: Path):
        """
        嘗試載入基準測試模組
        """
        try:
            benchmark_name = benchmark_dir.name
            
            # 嘗試載入基準測試模組
            if (benchmark_dir / f'{benchmark_name}.py').exists():
                # 單檔案基準測試 (如 benchmark/MBPP/MBPP.py)
                module_path = f'refactor.benchmark.{benchmark_name}.{benchmark_name}'
            else:
                # 查找可能的主檔案
                possible_files = ['__init__.py', 'main.py', f'{benchmark_name.lower()}.py']
                main_file = None
                for file_name in possible_files:
                    if (benchmark_dir / file_name).exists():
                        main_file = file_name
                        break
                
                if not main_file:
                    self.logger.debug(f"No main file found in {benchmark_dir}")
                    return
                
                module_name = main_file.replace('.py', '') if main_file != '__init__.py' else benchmark_name
                module_path = f'refactor.benchmark.{benchmark_name}.{module_name}'
            
            # 動態載入模組
            benchmark_module = importlib.import_module(module_path)
            
            # 查找基準測試類
            benchmark_class = self._find_benchmark_class(benchmark_module, benchmark_name)
            if benchmark_class:
                # 註冊基準測試
                BENCHMARKS.register_module(benchmark_name)(benchmark_class)
                self.logger.info(f"Registered benchmark: {benchmark_name}")
            
        except ImportError as e:
            self.logger.debug(f"Could not load benchmark {benchmark_dir.name}: {e}")
        except Exception as e:
            self.logger.warning(f"Error loading benchmark {benchmark_dir.name}: {e}")
    
    def _find_benchmark_class(self, module, benchmark_name: str) -> Optional[Type]:
        """
        在模組中查找基準測試類
        """
        # 常見的基準測試類名模式
        possible_names = [
            benchmark_name,  # 直接使用目錄名 (如 MBPP)
            f'{benchmark_name}Benchmark',
            f'{benchmark_name}Dataset', 
            f'{benchmark_name}Evaluator',
            f'{benchmark_name.upper()}',
            f'{benchmark_name.lower()}',
            f'{benchmark_name.capitalize()}'
        ]
        
        for class_name in possible_names:
            if hasattr(module, class_name):
                cls = getattr(module, class_name)
                if inspect.isclass(cls) and self._is_valid_benchmark_class(cls):
                    return cls
        
        return None
    
    def _is_valid_benchmark_class(self, cls: Type) -> bool:
        """
        檢查是否為有效的基準測試類
        """
        # 檢查是否有必要的方法
        required_methods = ['get_prompt', 'postprocess_generation', 'process_results']
        
        for method_name in required_methods:
            if not hasattr(cls, method_name):
                return False
        
        # 檢查是否繼承自 Benchmark 基類（可選）
        if hasattr(cls, '__bases__'):
            for base in cls.__bases__:
                if 'Benchmark' in base.__name__:
                    return True
        
        # 如果有必要的方法，也認為是有效的
        return True
    
    def create_benchmark(self, benchmark_config: Dict[str, Any]) -> Any:
        """
        創建基準測試實例
        
        Args:
            benchmark_config: 基準測試配置字典，必須包含 'type' 欄位
            
        Returns:
            基準測試實例
        """
        if 'type' not in benchmark_config:
            raise ValueError("Benchmark config must contain 'type' field")
        
        benchmark_type = benchmark_config['type']
        
        # 獲取基準測試類
        benchmark_class = BENCHMARKS.get(benchmark_type)
        if benchmark_class is None:
            available_benchmarks = BENCHMARKS.list_modules()
            raise KeyError(
                f"Benchmark '{benchmark_type}' not found. "
                f"Available benchmarks: {available_benchmarks}"
            )
        
        # 構建初始化參數
        init_params = self._build_init_params(benchmark_config, benchmark_class)
        
        # 實例化基準測試
        try:
            benchmark_instance = benchmark_class(**init_params)
            self.logger.info(f"Successfully created benchmark: {benchmark_type}")
            return benchmark_instance
        except Exception as e:
            self.logger.error(f"Failed to create benchmark {benchmark_type}: {e}")
            raise
    
    def _build_init_params(self, config: Dict[str, Any], benchmark_class: Type) -> Dict[str, Any]:
        """
        構建初始化參數
        根據基準測試類的 __init__ 方法簽名動態構建參數
        """
        # 複製配置並移除 type 欄位
        params = config.copy()
        params.pop('type', None)
        
        # 獲取類的 __init__ 方法簽名
        try:
            init_signature = inspect.signature(benchmark_class.__init__)
        except (ValueError, TypeError):
            # 如果無法獲取簽名，直接使用所有參數
            self.logger.warning(f"Cannot inspect {benchmark_class.__name__}.__init__, using all parameters")
            return params
        
        # 構建有效參數字典
        valid_params = {}
        missing_required = []
        
        for param_name, param in init_signature.parameters.items():
            if param_name == 'self':
                continue
            
            if param_name in params:
                valid_params[param_name] = params[param_name]
            elif param.default is not inspect.Parameter.empty:
                # 有預設值，不需要提供
                pass
            else:
                # 必要參數但未提供
                missing_required.append(param_name)
        
        if missing_required:
            raise ValueError(
                f"Missing required parameters for {benchmark_class.__name__}: {missing_required}"
            )
        
        return valid_params
    
    def create_multiple_benchmarks(self, benchmark_configs: List[Dict[str, Any]]) -> List[Any]:
        """
        創建多個基準測試實例
        
        Args:
            benchmark_configs: 基準測試配置列表
            
        Returns:
            基準測試實例列表
        """
        benchmarks = []
        for config in benchmark_configs:
            try:
                benchmark = self.create_benchmark(config)
                benchmarks.append(benchmark)
            except Exception as e:
                self.logger.error(f"Failed to create benchmark from config {config}: {e}")
                # 繼續創建其他基準測試
        
        return benchmarks
    
    def list_available_benchmarks(self) -> List[str]:
        """
        列出可用的基準測試
        """
        return BENCHMARKS.list_modules()
    
    def get_benchmark_info(self, benchmark_name: str) -> Dict[str, Any]:
        """
        獲取基準測試資訊
        """
        benchmark_class = BENCHMARKS.get(benchmark_name)
        if benchmark_class is None:
            raise ValueError(f"Benchmark '{benchmark_name}' not found")
        
        info = {
            'name': benchmark_name,
            'class': benchmark_class.__name__,
            'module': benchmark_class.__module__,
            'doc': benchmark_class.__doc__
        }
        
        # 嘗試載入 metafile.yml
        benchmark_dir = Path(__file__).parent.parent / 'benchmark' / benchmark_name
        metafile_path = benchmark_dir / 'metafile.yml'
        
        if metafile_path.exists():
            try:
                with open(metafile_path, 'r', encoding='utf-8') as f:
                    metafile = yaml.safe_load(f)
                    info['metafile'] = metafile
            except Exception as e:
                self.logger.warning(f"Failed to read metafile for {benchmark_name}: {e}")
        
        # 獲取初始化參數資訊
        try:
            init_signature = inspect.signature(benchmark_class.__init__)
            params = {}
            for param_name, param in init_signature.parameters.items():
                if param_name == 'self':
                    continue
                
                param_info = {
                    'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                    'default': param.default if param.default != inspect.Parameter.empty else 'Required',
                    'required': param.default == inspect.Parameter.empty
                }
                params[param_name] = param_info
            
            info['parameters'] = params
        except:
            info['parameters'] = {}
        
        return info


# 便利函數
def create_benchmark_factory(config: Optional[Config] = None) -> BenchmarkFactory:
    """
    創建基準測試工廠
    """
    return BenchmarkFactory(config)


def create_benchmark(benchmark_config: Dict[str, Any]) -> Any:
    """
    便利函數：直接創建基準測試實例
    """
    factory = BenchmarkFactory()
    return factory.create_benchmark(benchmark_config)


def create_multiple_benchmarks(benchmark_configs: List[Dict[str, Any]]) -> List[Any]:
    """
    便利函數：直接創建多個基準測試實例
    """
    factory = BenchmarkFactory()
    return factory.create_multiple_benchmarks(benchmark_configs)


def list_available_benchmarks() -> List[str]:
    """
    便利函數：列出可用基準測試
    """
    factory = BenchmarkFactory()
    return factory.list_available_benchmarks()