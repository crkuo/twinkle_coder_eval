import os
import argparse
import numpy as np
import hashlib
import json
from pathlib import Path
from datetime import datetime

# 設置環境變數
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# 添加路徑
import sys
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([os.path.dirname(ROOT), os.path.dirname(os.path.dirname(ROOT))])

from tqdm import tqdm
from typing import Callable, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# 導入 refactor 模組
from utils import refine_text, write_jsonl, group_and_count, estimate_pass_at_k
from engine.registry import BACKENDS, BENCHMARKS
from engine.config import Config


def multi_process_function(function: Callable,
                           parameters: List,
                           num_workers: int = 1,
                           desc: str = "Completing tasks"):
    
    if num_workers > len(parameters) or num_workers > os.cpu_count():
        num_workers = min(os.cpu_count(), len(parameters))

    with ThreadPoolExecutor(num_workers) as executor:
        futures = []
        for param in parameters:
            future = executor.submit(function, param)
            futures.append(future)
            
        results = []
        for future in tqdm(as_completed(futures), total=len(futures), desc=desc):
            result = future.result()
            results.append(result)

    return results


def dynamic_import_benchmark(benchmark_type: str):
    """
    動態導入 benchmark 模組
    """
    try:
        module_name = f"benchmark.{benchmark_type}.{benchmark_type}"
        __import__(module_name)
        print(f"Successfully imported {benchmark_type} benchmark")
    except ImportError as e:
        print(f"Warning: Failed to import {benchmark_type}: {e}")
        # 嘗試其他可能的路徑
        try:
            alt_module_name = f"benchmark.{benchmark_type}"
            __import__(alt_module_name)
            print(f"Successfully imported {benchmark_type} benchmark (alternative path)")
        except ImportError:
            print(f"Failed to import {benchmark_type} benchmark from any path")


def generate_timestamp() -> str:
    """
    生成時間戳字符串用於目錄命名
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    parser = argparse.ArgumentParser(description='Run evaluation using YAML config')
    parser.add_argument('config', help='Path to YAML config file')
    parser.add_argument('--save-path', help='Override save path from config')
    
    args = parser.parse_args()
    
    # 使用 Config.fromfile 載入配置（MMOCR 風格）
    config = Config.fromfile(args.config)
    print(f"Loaded config from: {args.config}")
    
    # 獲取基準測試配置列表
    benchmark_configs = config.evaluation.benchmark
    assert len(benchmark_configs) > 0, "No benchmarks specified in config"
    
    # 統一使用 for-loop 處理所有 benchmark（無論是 1 個還是多個）
    all_results = []
    for i, benchmark_config in enumerate(benchmark_configs):
        benchmark_type = benchmark_config['type']
        print(f"\n=== Running Benchmark {i+1}/{len(benchmark_configs)}: {benchmark_type} ===")
        
        # 動態導入 benchmark
        dynamic_import_benchmark(benchmark_type)
        
        # 從 params 中提取參數
        benchmark_params = benchmark_config.get('params', {})
        
        # 構建輸出路徑，使用時間戳
        experiment_name = config.get('experiment_name') or config.model.backend[0].model_name
        timestamp = generate_timestamp()
        
        # 生成基於時間戳的目錄名
        save_path = os.path.join('result', experiment_name, timestamp)
        if args.save_path:
            save_path = os.path.join(args.save_path, timestamp)
        
        os.makedirs(save_path, exist_ok=True)
        print(f"Results will be saved to: {save_path}")
        print(f"Timestamp: {timestamp}")
        
        # 保存配置文件到輸出目錄
        config_save_path = os.path.join(save_path, "config.json")
        with open(config_save_path, 'w', encoding='utf-8') as f:
            # 將配置轉換為可序列化的字典
            config_dict = {
                'model': dict(config.model),
                'evaluation': dict(config.evaluation),
                'experiment_name': config.get('experiment_name', experiment_name),
                'benchmark_type': benchmark_type,
                'benchmark_params': benchmark_params,
                'timestamp': timestamp
            }
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        print(f"Config saved to: {config_save_path}")
        
        # 使用 registry 構建 benchmark
        task = BENCHMARKS.build(benchmark_config)
        print(f"Loaded benchmark: {benchmark_type}")
        
        # 創建後端（所有 benchmark 共用同一個模型）
        backend_config = config.model.backend[0]
        backend_type = backend_config['type']
        print(f"Creating {backend_type} backend using registry...")
        
        # 合併 backend 參數和 benchmark 參數
        merged_backend_config = dict(backend_config)
        merged_backend_config.update(benchmark_params)
        
        decoder = BACKENDS.build(merged_backend_config)
        model_name = backend_config['model_name']
        print(f"Loaded model: {model_name}")
        
        # 獲取提示
        prompts = task.get_prompt()
        print(f"Generated {len(prompts)} prompts")
        
        # 處理提示前後綴（從 params 中獲取）
        prompt_prefix = benchmark_params.get('prompt_prefix', '')
        prompt_suffix = benchmark_params.get('prompt_suffix', '')
        response_prefix = benchmark_params.get('response_prefix', '')
        response_suffix = benchmark_params.get('response_suffix', '')
        
        for prompt in prompts:
            prompt['prompt'] = refine_text(prompt_prefix + prompt['prompt'] + prompt_suffix)
        
        write_jsonl(os.path.join(save_path, "prompts.jsonl"), prompts)
        print("Saved prompts.jsonl")
        
        # 設置停止詞
        model_type = merged_backend_config.get('model_type', 'Chat')
        end_words = task.general_stop_words + task.completion_stop_words if model_type == "Base" else task.general_stop_words
        
        # 生成回應
        print("Starting generation...")
        num_samples = benchmark_params.get('num_samples', 1)
        generations = decoder.generate(
            prompts,
            num_samples,
            end_words,
            response_prefix,
            response_suffix
        )
        write_jsonl(os.path.join(save_path, "generations.jsonl"), generations)
        print("Saved generations.jsonl")
        
        # 後處理解決方案
        print("Post-processing solutions...")
        num_workers = benchmark_params.get('num_workers', 1)
        solutions = multi_process_function(
            function=task.postprocess_generation,
            parameters=generations,
            num_workers=num_workers,
            desc="Post-processing solutions"
        )
        write_jsonl(os.path.join(save_path, "solutions.jsonl"), solutions)
        print("Saved solutions.jsonl")
        
        # 評估解決方案
        print("Evaluating solutions...")
        evaluations = multi_process_function(
            function=task.process_results,
            parameters=solutions,
            num_workers=num_workers,
            desc="Evaluating solutions"
        )
        write_jsonl(os.path.join(save_path, "evaluation.jsonl"), evaluations)
        print("Saved evaluation.jsonl")
        
        # 計算分數
        result_list = group_and_count(evaluations, group_key='task_id', count_key='passed')
        pass_rate = float(np.mean(estimate_pass_at_k(num_samples=num_samples, num_correct=result_list, k=1)))
        
        result = {
            "benchmark": benchmark_type,
            "score": pass_rate,
            "num_samples": num_samples,
            "total_prompts": len(prompts)
        }
        write_jsonl(os.path.join(save_path, "result.json"), [result])
        
        print(f"Pass@1: {pass_rate:.4f}")
        print(f"Results saved to: {save_path}")
        
        all_results.append(result)
    
    # 輸出總結
    print(f"\n=== Evaluation Summary ===")
    for result in all_results:
        print(f"{result['benchmark']}: Pass@1 = {result['score']:.4f} ({result['total_prompts']} prompts, {result['num_samples']} samples each)")
    
    if len(all_results) > 1:
        avg_score = np.mean([r['score'] for r in all_results])
        print(f"Average Pass@1: {avg_score:.4f}")


if __name__ == "__main__":
    main()