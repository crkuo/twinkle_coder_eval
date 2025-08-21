"""
Environment utilities for loading configuration from .env files
"""
import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False
    print("Warning: python-dotenv not installed. Environment variables will be loaded from system only.")


def load_environment() -> None:
    """
    Load environment variables from .env file if it exists
    """
    if not HAS_DOTENV:
        return
    
    # Find .env file in project root
    project_root = Path(__file__).parent.parent  # refactor/
    env_file = project_root / '.env'
    
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment variables from {env_file}")
    else:
        print(f"No .env file found at {env_file}")


def get_dataset_cache_folder() -> str:
    """
    Get the dataset cache folder path from environment or use default
    
    Returns:
        str: Path to dataset cache folder
    """
    # Load environment if not already loaded
    load_environment()
    
    # Get from environment variable or use default
    cache_folder = os.getenv('DATASET_CACHE_FOLDER', 'cache')
    
    # Make it relative to project root if it's not absolute
    if not os.path.isabs(cache_folder):
        project_root = Path(__file__).parent.parent  # refactor/
        cache_folder = str(project_root / cache_folder)
    
    # Ensure directory exists
    os.makedirs(cache_folder, exist_ok=True)
    
    return cache_folder


def get_result_folder() -> str:
    """
    Get the result folder path from environment or use default
    
    Returns:
        str: Path to result folder
    """
    load_environment()
    
    result_folder = os.getenv('RESULT_FOLDER', 'result')
    
    # Make it relative to project root if it's not absolute
    if not os.path.isabs(result_folder):
        project_root = Path(__file__).parent.parent  # refactor/
        result_folder = str(project_root / result_folder)
    
    return result_folder


def get_api_key(backend_type: str = 'openai') -> Optional[str]:
    """
    Get API key from environment variables
    
    Args:
        backend_type: Type of backend ('openai', 'custom', etc.)
        
    Returns:
        str or None: API key if found
    """
    load_environment()
    
    if backend_type.lower() == 'openai':
        return os.getenv('OPENAI_API_KEY')
    elif backend_type.lower() == 'custom':
        return os.getenv('CUSTOM_API_KEY')
    else:
        # Try generic pattern: {BACKEND}_API_KEY
        key_name = f'{backend_type.upper()}_API_KEY'
        return os.getenv(key_name)


def get_api_base_url(backend_type: str = 'openai') -> Optional[str]:
    """
    Get API base URL from environment variables
    
    Args:
        backend_type: Type of backend ('openai', 'custom', etc.)
        
    Returns:
        str or None: Base URL if found
    """
    load_environment()
    
    if backend_type.lower() == 'openai':
        return os.getenv('OPENAI_BASE_URL', 'https://api.openai.com')
    elif backend_type.lower() == 'custom':
        return os.getenv('CUSTOM_BASE_URL')
    else:
        # Try generic pattern: {BACKEND}_BASE_URL
        url_name = f'{backend_type.upper()}_BASE_URL'
        return os.getenv(url_name)


def get_env_var(key: str, default: str = None, var_type: type = str):
    """
    Get environment variable with type conversion and default value
    
    Args:
        key: Environment variable name
        default: Default value if not found
        var_type: Target type (str, int, float, bool)
        
    Returns:
        Environment variable value converted to specified type
    """
    load_environment()
    
    value = os.getenv(key, default)
    
    if value is None:
        return None
        
    try:
        if var_type == bool:
            return str(value).lower() in ('true', '1', 'yes', 'on')
        elif var_type == int:
            return int(value)
        elif var_type == float:
            return float(value)
        else:
            return str(value)
    except (ValueError, TypeError):
        # If conversion fails, return default
        if default is not None:
            return var_type(default) if var_type != bool else (str(default).lower() in ('true', '1', 'yes', 'on'))
        return None


def is_debug_enabled() -> bool:
    """
    Check if debug mode is enabled from environment
    
    Returns:
        bool: True if debug is enabled
    """
    return get_env_var('DEBUG', 'false', bool)


# Legacy compatibility - maintain the same interface as env.py
ROOT = Path(__file__).parent.parent  # refactor/
DATASET_CACHE_FOLDER = get_dataset_cache_folder()
BENCHMARK_FOLDER = str(ROOT / "benchmark")