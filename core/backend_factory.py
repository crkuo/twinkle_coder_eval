"""
後端工廠模組
專門處理後端實例化
"""
import importlib
import inspect
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from ..engine import BACKENDS, Config, ConfigDict


class BackendFactory:
    """
    後端工廠
    負責管理和實例化各種後端 (VLLM, OpenAI, etc.)
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._discover_and_register_backends()
    
    def _discover_and_register_backends(self):
        """
        自動發現並註冊可用的後端
        """
        backend_base_path = Path(__file__).parent.parent / 'backend'
        
        if not backend_base_path.exists():
            self.logger.warning(f"Backend directory not found: {backend_base_path}")
            return
        
        # 掃描 backend 目錄
        for backend_dir in backend_base_path.iterdir():
            if backend_dir.is_dir() and backend_dir.name not in ['__pycache__']:
                self._try_load_backend(backend_dir)
    
    def _try_load_backend(self, backend_dir: Path):
        """
        嘗試載入後端模組
        """
        try:
            backend_name = backend_dir.name
            
            # 嘗試載入後端模組
            if (backend_dir / f'{backend_name}.py').exists():
                # 單檔案後端 (如 backend/vllm/vllm.py)
                module_path = f'refactor.backend.{backend_name}.{backend_name}'
            else:
                # 查找可能的主檔案
                possible_files = ['__init__.py', 'main.py', f'{backend_name}_generator.py']
                main_file = None
                for file_name in possible_files:
                    if (backend_dir / file_name).exists():
                        main_file = file_name
                        break
                
                if not main_file:
                    self.logger.debug(f"No main file found in {backend_dir}")
                    return
                
                module_name = main_file.replace('.py', '') if main_file != '__init__.py' else backend_name
                module_path = f'refactor.backend.{backend_name}.{module_name}'
            
            # 動態載入模組
            backend_module = importlib.import_module(module_path)
            
            # 查找後端類
            backend_class = self._find_backend_class(backend_module, backend_name)
            if backend_class:
                # 註冊後端
                BACKENDS.register_module(backend_name)(backend_class)
                self.logger.info(f"Registered backend: {backend_name}")
            
        except ImportError as e:
            self.logger.debug(f"Could not load backend {backend_dir.name}: {e}")
        except Exception as e:
            self.logger.warning(f"Error loading backend {backend_dir.name}: {e}")
    
    def _find_backend_class(self, module, backend_name: str) -> Optional[Type]:
        """
        在模組中查找後端類
        """
        # 常見的後端類名模式
        possible_names = [
            f'{backend_name.upper()}Generator',
            f'{backend_name.lower()}Generator', 
            f'{backend_name.capitalize()}Generator',
            f'{backend_name}Generator',
            f'{backend_name.upper()}',
            f'{backend_name.capitalize()}',
            'Generator'
        ]
        
        for class_name in possible_names:
            if hasattr(module, class_name):
                cls = getattr(module, class_name)
                if inspect.isclass(cls) and self._is_valid_backend_class(cls):
                    return cls
        
        return None
    
    def _is_valid_backend_class(self, cls: Type) -> bool:
        """
        檢查是否為有效的後端類
        """
        # 檢查是否有 generate 方法
        if not hasattr(cls, 'generate'):
            return False
        
        # 檢查是否繼承自 Generator 基類（可選）
        if hasattr(cls, '__bases__'):
            for base in cls.__bases__:
                if 'Generator' in base.__name__:
                    return True
        
        # 或者檢查是否有正確的方法簽名
        try:
            generate_method = getattr(cls, 'generate')
            if callable(generate_method):
                return True
        except:
            pass
        
        return False
    
    def create_backend(self, backend_config: Dict[str, Any]) -> Any:
        """
        創建後端實例
        
        Args:
            backend_config: 後端配置字典，必須包含 'type' 欄位
            
        Returns:
            後端實例
        """
        if 'type' not in backend_config:
            raise ValueError("Backend config must contain 'type' field")
        
        backend_type = backend_config['type']
        
        # 獲取後端類
        backend_class = BACKENDS.get(backend_type)
        if backend_class is None:
            available_backends = BACKENDS.list_modules()
            raise KeyError(
                f"Backend '{backend_type}' not found. "
                f"Available backends: {available_backends}"
            )
        
        # 構建初始化參數
        init_params = self._build_init_params(backend_config, backend_class)
        
        # 實例化後端
        try:
            backend_instance = backend_class(**init_params)
            self.logger.info(f"Successfully created backend: {backend_type}")
            return backend_instance
        except Exception as e:
            self.logger.error(f"Failed to create backend {backend_type}: {e}")
            raise
    
    def _build_init_params(self, config: Dict[str, Any], backend_class: Type) -> Dict[str, Any]:
        """
        構建初始化參數
        根據後端類的 __init__ 方法簽名動態構建參數
        """
        # 複製配置並移除 type 欄位
        params = config.copy()
        params.pop('type', None)
        
        # 獲取類的 __init__ 方法簽名
        try:
            init_signature = inspect.signature(backend_class.__init__)
        except (ValueError, TypeError):
            # 如果無法獲取簽名，直接使用所有參數
            self.logger.warning(f"Cannot inspect {backend_class.__name__}.__init__, using all parameters")
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
                f"Missing required parameters for {backend_class.__name__}: {missing_required}"
            )
        
        return valid_params
    
    def list_available_backends(self) -> List[str]:
        """
        列出可用的後端
        """
        return BACKENDS.list_modules()
    
    def get_backend_info(self, backend_name: str) -> Dict[str, Any]:
        """
        獲取後端資訊
        """
        backend_class = BACKENDS.get(backend_name)
        if backend_class is None:
            raise ValueError(f"Backend '{backend_name}' not found")
        
        info = {
            'name': backend_name,
            'class': backend_class.__name__,
            'module': backend_class.__module__,
            'doc': backend_class.__doc__
        }
        
        # 獲取初始化參數資訊
        try:
            init_signature = inspect.signature(backend_class.__init__)
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
def create_backend_factory(config: Optional[Config] = None) -> BackendFactory:
    """
    創建後端工廠
    """
    return BackendFactory(config)


def create_backend(backend_config: Dict[str, Any]) -> Any:
    """
    便利函數：直接創建後端實例
    """
    factory = BackendFactory()
    return factory.create_backend(backend_config)


def list_available_backends() -> List[str]:
    """
    便利函數：列出可用後端
    """
    factory = BackendFactory()
    return factory.list_available_backends()