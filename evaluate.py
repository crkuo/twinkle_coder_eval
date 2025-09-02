# System path setup
import os
import sys
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([os.path.dirname(ROOT), os.path.dirname(os.path.dirname(ROOT))])

import argparse
import numpy as np
import json
from datetime import datetime


from typing import Callable, List
from concurrent.futures import ThreadPoolExecutor, as_completed
def multi_process_function(function: Callable,
                           parameters_per_node: List,
                           num_workers: int = 1,
                           desc: str = "Completing tasks"):
    """
    Execute a function in parallel across multiple workers using ThreadPoolExecutor.
    
    Args:
        function: The function to execute on each parameter set
        parameters_per_node: List of parameter sets to process
        num_workers: Number of worker threads to use
        desc: Description for progress tracking
    
    Returns:
        List of results from function execution
    """
    
    if num_workers > len(parameters_per_node) or num_workers > os.cpu_count():
        num_workers = min(os.cpu_count(), len(parameters_per_node))

    with ThreadPoolExecutor(num_workers) as executor:
        futures = []
        for param in parameters_per_node:
            future = executor.submit(function, param)
            futures.append(future)
            
        results = []
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    return results

from tqdm import tqdm
from typing import Callable, List

from tools.utils import write_jsonl, group_and_count, estimate_pass_at_k, read_jsonl
from tools.env_utils import get_env_var, load_environment
from engine.registry import BACKENDS, BENCHMARKS
from engine import Config

os.environ["TOKENIZERS_PARALLELISM"] = get_env_var("TOKENIZERS_PARALLELISM", "false")
# Load environment variables
load_environment()

def generate_config_signature(config_dict: dict, max_length: int = None) -> str:
    """
    Generate encrypted directory name based on configuration parameters.
    Uses SHA256 hash to avoid excessively long directory names.
    
    Args:
        config_dict: Configuration parameters dictionary
        max_length: Maximum length of generated signature
        
    Returns:
        Encrypted configuration signature string
    """
    import hashlib
    if max_length is None:
        max_length = get_env_var('CONFIG_SIGNATURE_MAX_LENGTH', '16', int)
    param_str = json.dumps(config_dict, sort_keys=True, separators=(',', ':'))
    hash_obj = hashlib.sha256(param_str.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()
    signature = hash_hex[:max_length]
    return signature

def remove_all_content_in_folder(folder_path):
    import shutil
    try:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
    except OSError as e:
        print(f"Error deleting folder: {e}")


def check_config(config: Config) -> Config:
    """
    Check and populate default values for evaluation configuration.
    
    Args:
        config: Original configuration object
        
    Returns:
        Config: Configuration object with populated default values
    """
    
    # Ensure backend configuration exists
    if not hasattr(config, 'backend') or not config.backend:
        config.backend = []
    
    # Process each backend configuration
    for backend_config in config.backend:
        if not hasattr(backend_config, 'model_name') or not backend_config.model_name:
            raise
        # Populate model_name default values
        if backend_config.type == 'openai':
            # Populate arguments default values
            if hasattr(backend_config, 'arguments') and backend_config.arguments:
                arguments = backend_config.arguments
            else:
                backend_config.arguments = {}
                arguments = backend_config.arguments
            # API Key default value
            if 'api_key' not in arguments or not arguments['api_key']:
                api_key = get_env_var('OPENAI_API_KEY') if backend_config.type == 'openai' else get_env_var(f'{backend_config.type.upper()}_API_KEY')
                if api_key:
                    arguments['api_key'] = api_key
            
            # Base URL default value
            if 'base_url' not in arguments or not arguments['base_url']:
                if backend_config.type == 'openai':
                    arguments['base_url'] = get_env_var('OPENAI_BASE_URL', 'https://api.openai.com')
                else:
                    base_url = get_env_var(f'{backend_config.type.upper()}_BASE_URL')
                    if base_url:
                        arguments['base_url'] = base_url
    
    # Ensure evaluation configuration exists
    if not hasattr(config, 'evaluation'):
        config.evaluation = type('evaluation', (), {})()
    
    # Ensure benchmark configuration exists
    if not hasattr(config.evaluation, 'benchmark') or not config.evaluation.benchmark:
        config.evaluation.benchmark = []
    
    # Process each benchmark configuration
    for benchmark_config in config.evaluation.benchmark:
        # Populate basic default values
        if not hasattr(benchmark_config, 'num_samples') or benchmark_config.num_samples is None:
            benchmark_config.num_samples = get_env_var('DEFAULT_NUM_SAMPLES', '1', int)
        
        if not hasattr(benchmark_config, 'num_workers') or benchmark_config.num_workers is None:
            benchmark_config.num_workers = get_env_var('DEFAULT_NUM_WORKERS', '1', int)
        
        if not hasattr(benchmark_config, 'pass_at_k') or benchmark_config.pass_at_k is None:
            benchmark_config.pass_at_k = get_env_var('DEFAULT_PASS_AT_K', '1', int)
        
        if not hasattr(benchmark_config, 'log_batch_size') or benchmark_config.log_batch_size is None:
            benchmark_config.log_batch_size = get_env_var('DEFAULT_LOG_BATCH_SIZE', None, int)
        
        # Ensure generate_args exists and populate default values
        if not hasattr(benchmark_config, 'generate_args') or not benchmark_config.generate_args:
            benchmark_config.generate_args = {}
        
        generate_args = benchmark_config.generate_args
        
        # Populate generation parameter defaults
        if 'temperature' not in generate_args:
            generate_args['temperature'] = get_env_var('DEFAULT_TEMPERATURE', '0.0', float)
        
        if 'max_tokens' not in generate_args:
            generate_args['max_tokens'] = get_env_var('DEFAULT_MAX_TOKENS', '512', int)
        
        if 'top_p' not in generate_args:
            generate_args['top_p'] = get_env_var('DEFAULT_TOP_P', '1.0', float)
        
        # Populate timeout default value (if benchmark supports it)
        if not hasattr(benchmark_config, 'timeout') or benchmark_config.timeout is None:
            benchmark_config.timeout = get_env_var('DEFAULT_TIMEOUT', '3.0', float)
    
    # Ensure output configuration exists
    if not hasattr(config.evaluation, 'output'):
        config.evaluation.output = type('output', (), {})()
    
    # Populate output directory default value
    if not hasattr(config.evaluation.output, 'result_folder') or not config.evaluation.output.result_folder:
        config.evaluation.output.result_folder = get_env_var('RESULT_FOLDER', './result')
    
    return config


def main():
    parser = argparse.ArgumentParser(description='Run evaluation using YAML config')
    parser.add_argument('config', help='Path to YAML config file')
    parser.add_argument('--open-batch-log', action='store_true', default=False, help='Log result by batch')
    parser.add_argument('--log-batch-size', type=int, default=1, help='Frequency to log result')
    parser.add_argument('--save-dir', help='Override save folder from config')
    
    args = parser.parse_args()
    

    config = Config.fromfile(args.config)
    config = check_config(config)  # 填入預設值
    print(config.dump())
    backend_configs = config.backend
    benchmark_configs = config.evaluation.benchmark

    if args.save_dir:
        save_folder = args.save_dir
    elif config.evaluation.output.result_folder:
        save_folder = config.evaluation.output.result_folder
    else:
        save_folder = './result'

    # Ensure save_folder would not indicate to a file.
    if os.path.exists(save_folder) and not os.path.isdir(save_folder):
        save_folder = os.path.dirname(save_folder)

    os.makedirs(save_folder, exist_ok=True)
    print(f"Results will be saved to: {save_folder}")
    global_results_save_path = os.path.join(save_folder, get_env_var('GLOBAL_RESULTS_FILENAME', 'results.json'))

    for bi, backend_config in enumerate(backend_configs):
        backend_type = backend_config.type
        print(f"\n=== Creating {bi+1}/{len(backend_configs)}: {backend_type} backend using registry ===")
        backend = BACKENDS.build(backend_config)

        model_name = backend.model_name
        for bmi, benchmark_config in enumerate(benchmark_configs):
            benchmark_type = benchmark_config.type
            num_samples = benchmark_config.get('num_samples', 1)
            num_workers = benchmark_config.num_workers if benchmark_config.num_workers  else 1
            
            generate_args = dict(benchmark_config.generate_args)
            config_dict_for_signature = {
                'backend': backend_type,
                'model_name': model_name,
                'num_samples': num_samples,
                'benchmark_type': benchmark_type,
                'generate_args': generate_args
            }
            experiment_signature = f"{benchmark_type}_{generate_config_signature(config_dict_for_signature)}"
            benchmark_result_folder = os.path.join(save_folder, experiment_signature)
            remove_all_content_in_folder(benchmark_result_folder)
            os.makedirs(benchmark_result_folder, exist_ok=True)

            config_save_path = os.path.join(benchmark_result_folder, get_env_var('CONFIG_FILENAME', 'config.json'))
            prompts_save_path = os.path.join(benchmark_result_folder, get_env_var('PROMPTS_FILENAME', 'prompts.jsonl'))
            generations_save_path = os.path.join(benchmark_result_folder, get_env_var('GENERATIONS_FILENAME', 'generations.jsonl'))
            solutions_save_path = os.path.join(benchmark_result_folder, get_env_var('SOLUTIONS_FILENAME', 'solutions.jsonl'))
            evalutions_save_path = os.path.join(benchmark_result_folder, get_env_var('EVALUATIONS_FILENAME', 'evaluations.jsonl'))
            result_save_path = os.path.join(benchmark_result_folder, get_env_var('RESULT_FILENAME', 'result.jsonl'))
            

            # Save benchmark config
            with open(config_save_path, 'w', encoding='utf-8') as fp:
                json.dump(dict(config_dict_for_signature), fp, indent = 2, ensure_ascii= False)
            print(f"Config saved to: {config_save_path}")
            

            print(f"\n=== Running Benchmark {bmi+1}/{len(benchmark_configs)}: {benchmark_type} ===")
            benchmark = BENCHMARKS.build(benchmark_config)

            prompts = benchmark.get_prompts()
            write_jsonl(prompts_save_path, prompts)

            model_name = backend_config.model_name
            log_batch_size = benchmark_config.get('log_batch_size', len(prompts))
            if args.open_batch_log:
                log_batch_size = args.log_batch_size
            
            for batch_start in tqdm(range(0, len(prompts), log_batch_size)):
                batch_prompts = prompts[batch_start:batch_start+log_batch_size]
                generations = backend.generate(
                    batch_prompts,
                    generate_args = generate_args,
                    num_samples = num_samples
                )
                write_jsonl(generations_save_path, generations, append=True)

                solutions = multi_process_function(
                    function=benchmark.postprocess_generation,
                    parameters_per_node=generations,
                    num_workers=num_workers,
                    desc="Post-processing solutions"
                )
                write_jsonl(solutions_save_path, solutions, append=True)

                evaluations = multi_process_function(
                    function=benchmark.process_results,
                    parameters_per_node=solutions,
                    num_workers=num_workers,
                    desc="Evaluating solutions"
                )
                write_jsonl(evalutions_save_path, evaluations, append=True)
            
            pass_at_k = benchmark_config.pass_at_k
            evaluations = read_jsonl(evalutions_save_path)
            result_list = group_and_count(evaluations, group_key='task_id', count_key='passed')
            pass_rate = float(np.mean(estimate_pass_at_k(num_samples=num_samples, num_correct=result_list, k=pass_at_k)))

            result = {
                "model_name": model_name,
                "backend": backend_type,
                "benchmark": benchmark_type,
                "score": pass_rate,
                "num_samples": num_samples,
                "parameters": generate_args,
                "total_prompts": len(prompts)
            }
            write_jsonl(result_save_path, [result], append=True)
            if os.path.exists(global_results_save_path):
                with open(global_results_save_path, 'r') as fp:
                    global_results = json.load(fp)
            else:
                global_results = {}
            global_results.update({os.path.relpath(benchmark_result_folder, save_folder):result})
            with open(global_results_save_path, 'w') as fp:
                json.dump(global_results, fp, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()




