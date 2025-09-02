"""
Evaluation Default Values Management
提供 evaluate.py 中使用的預設值管理功能
"""

import os
from typing import Dict, Any, Optional


def get_evaluation_defaults() -> Dict[str, Any]:
    """
    取得 evaluate.py 中所有的預設值
    
    Returns:
        Dict: 包含所有預設值的字典
    """
    defaults = {
        # 命令列參數預設值
        'open_batch_log': False,
        'log_batch_size': 1,
        'save_dir': None,  # 由 config 或 './result' 決定
        
        # 多進程處理預設值
        'num_workers': 1,
        'max_workers_cpu_limit': True,  # 限制為 CPU 核心數
        
        # 配置簽名預設值
        'config_signature_max_length': 16,
        
        # 結果目錄預設值
        'default_result_folder': './result',
        
        # 批次處理預設值
        'default_log_batch_size': None,  # 預設為 len(prompts)
        
        # 評估預設值
        'num_samples': 1,
        'pass_at_k': 1,
        
        # 環境變數預設值
        'tokenizers_parallelism': "false",
        
        # 文件名預設值
        'file_names': {
            'config': 'config.json',
            'prompts': 'prompts.jsonl',
            'generations': 'generations.jsonl', 
            'solutions': 'solutions.jsonl',
            'evaluations': 'evaluations.jsonl',
            'result': 'result.jsonl',
            'global_results': 'results.jsonl'
        }
    }
    
    return defaults


def apply_evaluation_defaults(config: Optional[Dict[str, Any]] = None, 
                            args: Optional[Any] = None) -> Dict[str, Any]:
    """
    應用預設值到配置和參數中
    
    Args:
        config: 配置字典（可選）
        args: 命令列參數對象（可選）
        
    Returns:
        Dict: 應用預設值後的完整配置
    """
    defaults = get_evaluation_defaults()
    
    # 建立最終配置
    final_config = {}
    
    # 應用預設值
    final_config.update(defaults)
    
    # 應用 config 中的值（如果存在）
    if config:
        # 處理後端配置預設值
        if 'backend' in config and isinstance(config['backend'], list):
            for backend_config in config['backend']:
                # 確保每個後端配置都有必要的屬性
                if 'model_name' not in backend_config:
                    backend_config['model_name'] = backend_config.get('type', 'unknown_model')
        
        # 處理評估配置預設值
        if 'evaluation' in config:
            eval_config = config['evaluation']
            
            # 處理 benchmark 配置
            if 'benchmark' in eval_config and isinstance(eval_config['benchmark'], list):
                for benchmark_config in eval_config['benchmark']:
                    # 應用 benchmark 預設值
                    benchmark_config.setdefault('num_samples', defaults['num_samples'])
                    benchmark_config.setdefault('num_workers', defaults['num_workers'])
                    benchmark_config.setdefault('pass_at_k', defaults['pass_at_k'])
                    
                    # 確保 generate_args 存在
                    if 'generate_args' not in benchmark_config:
                        benchmark_config['generate_args'] = {}
            
            # 處理輸出配置
            if 'output' not in eval_config:
                eval_config['output'] = {}
            
            if 'result_folder' not in eval_config['output']:
                eval_config['output']['result_folder'] = defaults['default_result_folder']
        
        final_config.update(config)
    
    # 應用命令列參數（優先級最高）
    if args:
        if hasattr(args, 'open_batch_log'):
            final_config['open_batch_log'] = args.open_batch_log
        if hasattr(args, 'log_batch_size'):
            final_config['log_batch_size'] = args.log_batch_size
        if hasattr(args, 'save_dir') and args.save_dir:
            final_config['save_dir'] = args.save_dir
    
    return final_config


def setup_evaluation_environment(config: Dict[str, Any]) -> None:
    """
    設定評估環境，應用環境變數等
    
    Args:
        config: 評估配置
    """
    defaults = get_evaluation_defaults()
    
    # 設定環境變數
    os.environ["TOKENIZERS_PARALLELISM"] = defaults['tokenizers_parallelism']
    
    # 確保結果目錄存在
    save_folder = config.get('save_dir') or \
                 config.get('evaluation', {}).get('output', {}).get('result_folder') or \
                 defaults['default_result_folder']
    
    # 如果指向的是文件而不是目錄，使用其父目錄
    if os.path.exists(save_folder) and not os.path.isdir(save_folder):
        save_folder = os.path.dirname(save_folder)
    
    os.makedirs(save_folder, exist_ok=True)
    return save_folder


def get_file_paths(benchmark_result_folder: str, 
                  file_names: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    取得所有結果文件的路徑
    
    Args:
        benchmark_result_folder: benchmark 結果目錄
        file_names: 自定義文件名（可選）
        
    Returns:
        Dict: 包含所有文件路徑的字典
    """
    if file_names is None:
        file_names = get_evaluation_defaults()['file_names']
    
    return {
        'config': os.path.join(benchmark_result_folder, file_names['config']),
        'prompts': os.path.join(benchmark_result_folder, file_names['prompts']),
        'generations': os.path.join(benchmark_result_folder, file_names['generations']),
        'solutions': os.path.join(benchmark_result_folder, file_names['solutions']),
        'evaluations': os.path.join(benchmark_result_folder, file_names['evaluations']),
        'result': os.path.join(benchmark_result_folder, file_names['result'])
    }


def get_worker_count(config_workers: Optional[int] = None, 
                    task_count: Optional[int] = None) -> int:
    """
    取得適當的 worker 數量
    
    Args:
        config_workers: 配置中指定的 worker 數量
        task_count: 任務數量
        
    Returns:
        int: 最終的 worker 數量
    """
    defaults = get_evaluation_defaults()
    
    # 使用配置值或預設值
    num_workers = config_workers or defaults['num_workers']
    
    # 限制 worker 數量
    max_workers = os.cpu_count()
    if task_count:
        max_workers = min(max_workers, task_count)
    
    return min(num_workers, max_workers)


# 使用範例
if __name__ == "__main__":
    # 取得所有預設值
    defaults = get_evaluation_defaults()
    print("Evaluation Defaults:")
    for key, value in defaults.items():
        print(f"  {key}: {value}")
    
    # 示例配置應用
    sample_config = {
        'evaluation': {
            'benchmark': [
                {'type': 'MBPP'},
                {'type': 'HumanEval', 'num_samples': 10}
            ]
        }
    }
    
    final_config = apply_evaluation_defaults(sample_config)
    print(f"\nApplied defaults to config:")
    print(f"Benchmark configs: {final_config['evaluation']['benchmark']}")