# 添加路徑
import os
import sys
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([os.path.dirname(ROOT), os.path.dirname(os.path.dirname(ROOT))])

import argparse
import numpy as np
import json
from datetime import datetime

os.environ["TOKENIZERS_PARALLELISM"] = "false"

from typing import Callable, List
from concurrent.futures import ThreadPoolExecutor, as_completed
def multi_process_function(function: Callable,
                           parameters_per_node: List,
                           num_workers: int = 1,
                           desc: str = "Completing tasks"):
    
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
from engine.registry import BACKENDS, BENCHMARKS
from engine import Config

def generate_config_signature(config_dict: dict, max_length: int = 16) -> str:
    import hashlib
    """
    根據配置參數生成加密的目錄名稱
    使用 SHA256 哈希以避免過長的目錄名
    
    Args:
        config_dict: 配置參數字典
        max_length: 生成簽名的最大長度
        
    Returns:
        加密的配置簽名字符串
    """
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


def main():
    parser = argparse.ArgumentParser(description='Run evaluation using YAML config')
    parser.add_argument('config', help='Path to YAML config file')
    parser.add_argument('--open-batch-log', action='store_true', default=False, help='Log result by batch')
    parser.add_argument('--log-batch-size', type=int, default=1, help='Frequency to log result')
    parser.add_argument('--save-dir', help='Override save folder from config')
    
    args = parser.parse_args()
    

    config = Config.fromfile(args.config)
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
    global_results_save_path = os.path.join(save_folder, 'results.jsonl')

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

            config_save_path = os.path.join(benchmark_result_folder, 'config.json')
            prompts_save_path = os.path.join(benchmark_result_folder, "prompts.jsonl")
            generations_save_path = os.path.join(benchmark_result_folder, 'generations.jsonl')
            solutions_save_path = os.path.join(benchmark_result_folder, "solutions.jsonl")
            evalutions_save_path = os.path.join(benchmark_result_folder, "evaluations.jsonl")
            result_save_path = os.path.join(benchmark_result_folder, "result.jsonl")
            

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




