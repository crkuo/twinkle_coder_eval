import os
import argparse
import numpy as np
from pathlib import Path

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
import yaml
from utils import refine_text, write_jsonl, group_and_count, estimate_pass_at_k
from backend.vllm.vllm import VllmGenerator
from factory import BenchmarkFactory


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


def create_args_from_config(config_path: str):
    """
    從 YAML 配置文件創建 args 對象
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    class Args:
        def __init__(self):
            # 模型配置
            model_config = config.get('model', {})
            backend_config = model_config.get('backend', [{}])[0]
            
            self.model_name = backend_config.get('model_name', 'default_model')
            self.tokenizer_name = backend_config.get('tokenizer_name')
            self.model_type = backend_config.get('model_type', 'Instruction')
            self.num_gpus = backend_config.get('num_gpus', 1)
            self.batch_size = backend_config.get('batch_size', 1)
            self.temperature = backend_config.get('temperature', 0.0)
            self.trust_remote_code = backend_config.get('trust_remote_code', True)
            self.max_tokens = backend_config.get('max_tokens', 1024)
            
            # 評估配置
            eval_config = config.get('evaluation', {})
            benchmark_config = eval_config.get('benchmark', [{}])[0]
            
            self.task = benchmark_config.get('type', 'MBPP')
            self.prompt_type = benchmark_config.get('prompt_type', 'Instruction')
            self.num_samples = eval_config.get('num_samples', 200)
            self.num_workers = eval_config.get('num_workers', 1)
            
            # 提示配置
            self.prompt_prefix = eval_config.get('prompt_prefix', '')
            self.prompt_suffix = eval_config.get('prompt_suffix', '')
            self.response_prefix = eval_config.get('response_prefix', '')
            self.response_suffix = eval_config.get('response_suffix', '')
            
            # 輸出配置
            output_config = eval_config.get('output', {})
            self.save_path = output_config.get('path', './output')
    
    return Args()


def main():
    parser = argparse.ArgumentParser(description='Run evaluation using YAML config')
    parser.add_argument('config', help='Path to YAML config file')
    parser.add_argument('--save-path', help='Override save path from config')
    
    args = parser.parse_args()
    
    # 從配置文件創建 args
    config_args = create_args_from_config(args.config)
    
    # 覆蓋保存路徑（如果提供）
    if args.save_path:
        config_args.save_path = args.save_path
    
    save_path = config_args.save_path
    os.makedirs(save_path, exist_ok=True)
    print(f"Results will be saved to: {save_path}")

    # 創建基準測試
    task = BenchmarkFactory.get_task(config_args)
    print(f"Loaded benchmark: {config_args.task}")

    # 創建後端
    decoder = VllmGenerator(
        model_name=config_args.model_name,
        model_type=config_args.model_type,
        tokenizer_name=config_args.tokenizer_name,
        num_gpus=config_args.num_gpus,
        batch_size=config_args.batch_size,
        temperature=config_args.temperature,
        trust_remote_code=config_args.trust_remote_code,
        max_tokens=config_args.max_tokens
    )
    print(f"Loaded model: {config_args.model_name}")

    # 獲取提示
    prompts = task.get_prompt()
    print(f"Generated {len(prompts)} prompts")

    # 處理提示前後綴
    for prompt in prompts:
        prompt['prompt'] = refine_text(config_args.prompt_prefix + prompt['prompt'] + config_args.prompt_suffix)
    
    write_jsonl(os.path.join(save_path, "prompts.jsonl"), prompts)
    print("Saved prompts.jsonl")

    # 設置停止詞
    end_words = task.general_stop_words + task.completion_stop_words if config_args.model_type == "Base" else task.general_stop_words
    
    # 生成回應
    print("Starting generation...")
    generations = decoder.generate(
        prompts,
        config_args.num_samples,
        end_words,
        config_args.response_prefix,
        config_args.response_suffix
    )
    write_jsonl(os.path.join(save_path, "generations.jsonl"), generations)
    print("Saved generations.jsonl")

    # 後處理解決方案
    print("Post-processing solutions...")
    solutions = multi_process_function(
        function=task.postprocess_generation,
        parameters=generations,
        num_workers=config_args.num_workers,
        desc="Post-processing solutions"
    )
    write_jsonl(os.path.join(save_path, "solutions.jsonl"), solutions)
    print("Saved solutions.jsonl")

    # 評估解決方案
    print("Evaluating solutions...")
    evaluations = multi_process_function(
        function=task.process_results,
        parameters=solutions,
        num_workers=config_args.num_workers,
        desc="Evaluating solutions"
    )
    write_jsonl(os.path.join(save_path, "evaluation.jsonl"), evaluations)
    print("Saved evaluation.jsonl")

    # 計算分數
    result_list = group_and_count(evaluations, group_key='task_id', count_key='passed')
    pass_rate = float(np.mean(estimate_pass_at_k(num_samples=config_args.num_samples, num_correct=result_list, k=1)))
    
    result = {"score": pass_rate}
    write_jsonl(os.path.join(save_path, "result.json"), [result])
    
    print(f"Pass@1: {pass_rate:.4f}")
    print(f"Results saved to: {save_path}")


if __name__ == "__main__":
    main()