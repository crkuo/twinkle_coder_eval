import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([os.path.dirname(ROOT), os.path.dirname(os.path.dirname(ROOT))])

from typing import List, Dict
from backend.base import Generator
from utils import refine_text
from engine.registry import register_backend

@register_backend('mock')
class MockGenerator(Generator):
    def __init__(self,
                 model_name: str = "mock-model",
                 model_type: str = "Chat",
                 batch_size: int = 1,
                 temperature: float = 0.0,
                 max_tokens: int = 1024,
                 **kwargs
               ) -> None:
        super().__init__(model_name)

        print("Initializing Mock Generator: {} ...".format(model_name))
        self.model_name = model_name
        self.model_type = model_type
        self.batch_size = batch_size
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        print(f"Mock Generator initialized")
        print(f"Model: {model_name}")
        print(f"Model type: {model_type}")

    def is_chat(self) -> bool:
        return self.model_type == "Chat"

    def generate(self,
                 prompt_set: List[Dict],
                 num_samples: int = 200,
                 eos: List[str] = None,
                 response_prefix: str = "",
                 response_suffix: str = ""
                ) -> List[str]:

        print("Using Mock Generator")
        print(f"Generating {num_samples} samples for {len(prompt_set)} prompts")
        
        # 模擬代碼生成
        sample_prompts = []
        for prompt_data in prompt_set:
            for _ in range(num_samples):
                sample_prompts.append(prompt_data)

        generations = []
        
        for i, prompt_data in enumerate(sample_prompts):
            task_id = prompt_data['task_id']
            completion_id = i
            
            # 模擬生成的代碼解決方案
            if task_id == 10:  # MBPP task 10 
                mock_solution = """def small_nnum(numbers, n):
    return sorted(numbers)[:n]"""
            else:
                mock_solution = f"def solution(x):\n    return x * 2  # Mock solution for task {task_id}"
            
            result = {
                'task_id': task_id,
                'completion_id': completion_id,
                'completion': refine_text(mock_solution)
            }
            generations.append(result)

        return generations