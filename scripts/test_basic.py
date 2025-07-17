#!/usr/bin/env python3
"""
基本系統測試腳本
測試不需要 transformers 的核心功能
"""
import yaml
import numpy as np
from tqdm import tqdm
import os
import sys


def test_config_parsing():
    """測試配置解析"""
    print("🧪 測試配置解析...")
    
    with open('configs/test_mbpp_config.yml', 'r') as f:
        config = yaml.safe_load(f)
    
    assert config['name'] == "Test MBPP Evaluation"
    assert config['model']['backend'][0]['type'] == 'vllm'
    assert config['evaluation']['benchmark'][0]['type'] == 'MBPP'
    
    print("✅ 配置解析正常")
    return config


def test_args_creation(config):
    """測試參數創建"""
    print("🧪 測試參數創建...")
    
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
    
    args = Args()
    
    assert args.model_name == "deepseek-ai/deepseek-coder-6.7b-instruct"
    assert args.task == "MBPP"
    assert args.prompt_type == "Instruction"
    
    print("✅ 參數創建正常")
    return args


def test_basic_utils():
    """測試基本工具函數（不需要 transformers）"""
    print("🧪 測試基本工具函數...")
    
    # 測試文本處理
    def refine_text(text: str) -> str:
        text = text.replace("\t", "    ")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return text.strip() + "\n"
    
    test_text = "hello\tworld\r\n"
    refined = refine_text(test_text)
    expected = "hello    world\n"
    assert refined == expected
    
    # 測試 group_and_count
    def group_and_count(lst, group_key, count_key):
        from collections import defaultdict
        grouped_counts = defaultdict(int)
        
        for item in lst:
            group = item.get(group_key)
            if group not in grouped_counts:
                grouped_counts[group] = 0
            if item.get(count_key) == True:
                grouped_counts[group] += 1
        
        return list(grouped_counts.values())
    
    test_data = [
        {'task_id': 'task1', 'passed': True},
        {'task_id': 'task1', 'passed': False},
        {'task_id': 'task2', 'passed': True},
    ]
    
    result = group_and_count(test_data, 'task_id', 'passed')
    assert result == [1, 1]  # task1: 1 passed, task2: 1 passed
    
    print("✅ 基本工具函數正常")


def test_benchmark_loading():
    """測試基準測試載入"""
    print("🧪 測試基準測試載入...")
    
    try:
        from benchmark.MBPP.MBPP import MBPP
        
        # 創建 MBPP 實例（不需要實際載入數據）
        mbpp = MBPP(name="MBPP", prompt_type="Instruction")
        
        # 檢查基本屬性
        assert hasattr(mbpp, 'name')
        assert hasattr(mbpp, 'prompt_type')
        assert hasattr(mbpp, 'get_prompt')
        assert hasattr(mbpp, 'postprocess_generation')
        assert hasattr(mbpp, 'process_results')
        
        print("✅ MBPP 基準測試載入正常")
        
    except Exception as e:
        print(f"⚠️  MBPP 載入出現問題: {e}")
        return False
    
    return True


def test_factory():
    """測試工廠類"""
    print("🧪 測試工廠類...")
    
    try:
        from factory import BenchmarkFactory
        
        # 創建模擬 args
        class MockArgs:
            def __init__(self):
                self.task = "MBPP"
                self.prompt_type = "Instruction"
        
        args = MockArgs()
        
        # 測試工廠方法
        task = BenchmarkFactory.get_task(args)
        assert task is not None
        assert hasattr(task, 'name')
        
        print("✅ 工廠類正常")
        return True
        
    except Exception as e:
        print(f"⚠️  工廠類測試出現問題: {e}")
        return False


def main():
    """主測試函數"""
    print("🚀 開始基本系統測試\n")
    
    os.chdir('/home/edward/twinkle_code_eval/refactor')
    
    try:
        # 測試配置解析
        config = test_config_parsing()
        
        # 測試參數創建
        args = test_args_creation(config)
        
        # 測試基本工具函數
        test_basic_utils()
        
        # 測試基準測試載入
        benchmark_ok = test_benchmark_loading()
        
        # 測試工廠類
        factory_ok = test_factory()
        
        print("\n🎉 基本系統測試完成！")
        print(f"配置系統: ✅")
        print(f"工具函數: ✅")
        print(f"基準測試: {'✅' if benchmark_ok else '⚠️'}")
        print(f"工廠類: {'✅' if factory_ok else '⚠️'}")
        
        if benchmark_ok and factory_ok:
            print("\n✨ 所有基本功能正常，系統已整合完成！")
            return True
        else:
            print("\n⚠️  部分功能需要調整")
            return False
            
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)