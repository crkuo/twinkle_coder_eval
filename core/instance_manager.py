"""
實例管理器
統一管理後端、基準測試和其他元件的實例化
"""
import logging
from typing import Any, Dict, List, Optional

from ..engine import Config, ConfigDict
from .backend_factory import BackendFactory
from .benchmark_factory import BenchmarkFactory


class InstanceManager:
    """
    實例管理器
    提供統一的實例化和管理接口
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 初始化工廠
        self.backend_factory = BackendFactory(config)
        self.benchmark_factory = BenchmarkFactory(config)
        
        # 快取已創建的實例
        self._backend_cache = {}
        self._benchmark_cache = {}
    
    def create_backend(self, backend_config: Dict[str, Any], use_cache: bool = True) -> Any:
        """
        創建後端實例
        
        Args:
            backend_config: 後端配置
            use_cache: 是否使用快取
            
        Returns:
            後端實例
        """
        backend_type = backend_config.get('type', 'unknown')
        
        # 檢查快取
        if use_cache and backend_type in self._backend_cache:
            self.logger.debug(f"Using cached backend: {backend_type}")
            return self._backend_cache[backend_type]
        
        # 創建新實例
        backend_instance = self.backend_factory.create_backend(backend_config)
        
        # 快取實例
        if use_cache:
            self._backend_cache[backend_type] = backend_instance
        
        return backend_instance
    
    def create_benchmark(self, benchmark_config: Dict[str, Any], use_cache: bool = True) -> Any:
        """
        創建基準測試實例
        
        Args:
            benchmark_config: 基準測試配置
            use_cache: 是否使用快取
            
        Returns:
            基準測試實例
        """
        benchmark_type = benchmark_config.get('type', 'unknown')
        
        # 生成快取鍵（包含重要參數）
        cache_key = self._generate_benchmark_cache_key(benchmark_config)
        
        # 檢查快取
        if use_cache and cache_key in self._benchmark_cache:
            self.logger.debug(f"Using cached benchmark: {benchmark_type}")
            return self._benchmark_cache[cache_key]
        
        # 創建新實例
        benchmark_instance = self.benchmark_factory.create_benchmark(benchmark_config)
        
        # 快取實例
        if use_cache:
            self._benchmark_cache[cache_key] = benchmark_instance
        
        return benchmark_instance
    
    def create_multiple_benchmarks(self, benchmark_configs: List[Dict[str, Any]], use_cache: bool = True) -> List[Any]:
        """
        創建多個基準測試實例
        
        Args:
            benchmark_configs: 基準測試配置列表
            use_cache: 是否使用快取
            
        Returns:
            基準測試實例列表
        """
        benchmarks = []
        for config in benchmark_configs:
            try:
                benchmark = self.create_benchmark(config, use_cache)
                benchmarks.append(benchmark)
            except Exception as e:
                self.logger.error(f"Failed to create benchmark from config {config}: {e}")
                # 繼續創建其他基準測試
        
        return benchmarks
    
    def create_all_components_from_config(self, config: Optional[Config] = None) -> Dict[str, Any]:
        """
        從配置創建所有元件
        
        Args:
            config: 配置對象，如果不提供則使用初始化時的配置
            
        Returns:
            包含所有元件的字典
        """
        if config is None:
            config = self.config
        
        if config is None:
            raise ValueError("No config provided")
        
        components = {}
        
        # 創建後端
        try:
            backend_config = self._extract_backend_config(config)
            if backend_config:
                components['backend'] = self.create_backend(backend_config)
                self.logger.info("Backend created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create backend: {e}")
            raise
        
        # 創建基準測試
        try:
            benchmark_configs = self._extract_benchmark_configs(config)
            if benchmark_configs:
                components['benchmarks'] = self.create_multiple_benchmarks(benchmark_configs)
                self.logger.info(f"Created {len(components['benchmarks'])} benchmarks")
            else:
                components['benchmarks'] = []
        except Exception as e:
            self.logger.error(f"Failed to create benchmarks: {e}")
            components['benchmarks'] = []
        
        # 創建輸出處理器
        try:
            output_config = self._extract_output_config(config)
            components['output_processor'] = self._create_output_processor(output_config)
            self.logger.info("Output processor created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create output processor: {e}")
            components['output_processor'] = None
        
        return components
    
    def _extract_backend_config(self, config: Config) -> Optional[Dict[str, Any]]:
        """
        從配置中提取後端配置
        """
        if 'model' not in config:
            return None
        
        model_config = config['model']
        if 'backend' not in model_config:
            return None
        
        backend_list = model_config['backend']
        if not backend_list:
            return None
        
        # 獲取第一個後端配置
        first_backend = backend_list[0] if isinstance(backend_list, list) else backend_list
        return first_backend if isinstance(first_backend, dict) else None
    
    def _extract_benchmark_configs(self, config: Config) -> List[Dict[str, Any]]:
        """
        從配置中提取基準測試配置
        """
        if 'evaluation' not in config:
            return []
        
        evaluation_config = config['evaluation']
        if 'benchmark' not in evaluation_config:
            return []
        
        benchmark_configs = evaluation_config['benchmark']
        if not isinstance(benchmark_configs, list):
            return []
        
        return benchmark_configs
    
    def _extract_output_config(self, config: Config) -> Dict[str, Any]:
        """
        從配置中提取輸出配置
        """
        if 'evaluation' not in config:
            return {}
        
        evaluation_config = config['evaluation']
        return evaluation_config.get('output', {})
    
    def _create_output_processor(self, output_config: Dict[str, Any]) -> Any:
        """
        創建輸出處理器
        """
        # 簡單的輸出處理器實現
        class OutputProcessor:
            def __init__(self, path: str = "./output", keep_chat: bool = False):
                self.path = path
                self.keep_chat = keep_chat
            
            def process_output(self, results: Dict[str, Any]) -> Dict[str, Any]:
                """
                處理輸出結果
                """
                return {
                    'output_path': self.path,
                    'keep_chat': self.keep_chat,
                    'results': results
                }
        
        return OutputProcessor(
            path=output_config.get('path', './output'),
            keep_chat=output_config.get('keep_chat', False)
        )
    
    def _generate_benchmark_cache_key(self, benchmark_config: Dict[str, Any]) -> str:
        """
        生成基準測試快取鍵
        """
        # 包含重要參數來區分不同的實例
        key_parts = [
            benchmark_config.get('type', 'unknown'),
            str(benchmark_config.get('few_shot_examples', 0)),
            str(benchmark_config.get('timeout', 3.0)),
            str(benchmark_config.get('test_range', []))
        ]
        return '_'.join(key_parts)
    
    def clear_cache(self):
        """
        清除快取
        """
        self._backend_cache.clear()
        self._benchmark_cache.clear()
        self.logger.info("Instance cache cleared")
    
    def get_backend_info(self) -> Dict[str, Any]:
        """
        獲取後端資訊
        """
        return {
            'available_backends': self.backend_factory.list_available_backends(),
            'cached_backends': list(self._backend_cache.keys())
        }
    
    def get_benchmark_info(self) -> Dict[str, Any]:
        """
        獲取基準測試資訊
        """
        return {
            'available_benchmarks': self.benchmark_factory.list_available_benchmarks(),
            'cached_benchmarks': list(self._benchmark_cache.keys())
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        獲取系統資訊
        """
        return {
            'backend_info': self.get_backend_info(),
            'benchmark_info': self.get_benchmark_info(),
            'config_loaded': self.config is not None
        }


# 便利函數
def create_instance_manager(config: Optional[Config] = None) -> InstanceManager:
    """
    創建實例管理器
    """
    return InstanceManager(config)


def create_all_components(config: Config) -> Dict[str, Any]:
    """
    便利函數：從配置創建所有元件
    """
    manager = InstanceManager(config)
    return manager.create_all_components_from_config()


def create_components_from_config_file(config_path: str) -> Dict[str, Any]:
    """
    便利函數：從配置文件創建所有元件
    """
    from ..engine import Config
    
    config = Config.fromfile(config_path)
    return create_all_components(config)