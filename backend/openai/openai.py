import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([os.path.dirname(ROOT), os.path.dirname(os.path.dirname(ROOT))])

from openai import OpenAI
import httpx
from tqdm import tqdm
from typing import List, Dict

from backend.base import Generator
from utils import make_chat_prompt, refine_text
from engine.registry import register_backend

@register_backend('openai')
class OpenaiGenerator(Generator):
    def __init__(self,
                 model_name: str,
                 server_params: dict,
                 model_type: str = "Chat",
                 batch_size : int = 1,
                 temperature : float = 0.0,
                 max_tokens : int = 1024,
                 eos: List[str] = None,
                 **kwargs
               ) -> None:
        super().__init__(model_name)

        print("Initializing OpenAI client: {} ...".format(model_name))
        self.model_name = model_name
        self.model_type = model_type
        self.batch_size = batch_size
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.eos = eos
        
        # 初始化 OpenAI 客戶端
        self.client = OpenAI(
            **server_params
        )
        
        print(f"OpenAI client initialized with base_url: {server_params.get('base_url')}")
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

        # 如果是 Chat 模式，構建 chat prompt（但這裡直接使用原始 prompt）
        if self.is_chat():
            print("Using Chat Completion API")
        else:
            print("Using Text Completion API")
        
        print(f"First prompt: {prompt_set[0]['prompt'] if prompt_set else 'None'}")
        
        # 構建樣本提示
        sample_prompts = []
        for prompt_data in prompt_set:
            for _ in range(num_samples):
                sample_prompts.append(prompt_data)

        assert len(sample_prompts) == (len(prompt_set) * num_samples)
        assert all(sample_prompts[i:i + num_samples] == [sample_prompts[i]] * num_samples for i in range(0, len(sample_prompts), num_samples))

        generations = []

        for batch_start in tqdm(range(0, len(sample_prompts), self.batch_size)):
            batch = sample_prompts[batch_start : batch_start + self.batch_size]
            
            batch_generations = []
            for prompt_data in batch:
                try:
                    prompt_text = prompt_data['prompt']
                    task_id = prompt_data['task_id']
                    completion_id = batch_start + len(batch_generations)
                    
                    full_prompt = response_prefix + prompt_text
                    
                    if self.is_chat():
                        # 使用 Chat Completion API
                        messages = [{"role": "user", "content": full_prompt}]
                        
                        # 過濾 None 值避免 API 錯誤
                        create_params = {
                            "model": self.model_name,
                            "messages": messages,
                            "temperature": self.temperature,
                            "max_tokens": self.max_tokens
                        }
                        
                        # 只有當 stop 不是 None 且不為空時才加入
                        if self.eos and len(self.eos) > 0:
                            create_params["stop"] = self.eos
                        
                        response = self.client.chat.completions.create(**create_params)
                        
                        generation = response.choices[0].message.content
                        
                        # 組裝結果格式，與 VllmGenerator 保持一致
                        result = {
                            'task_id': task_id,
                            'completion_id': completion_id,
                            'completion': refine_text(generation) if generation is not None else ""
                        }
                        batch_generations.append(result)
                        
                    else:
                        # 使用 Text Completion API
                        complete_params = {
                            "model": self.model_name,
                            "prompt": full_prompt,
                            "temperature": self.temperature,
                            "max_tokens": self.max_tokens
                        }
                        
                        # 只有當 stop 不是 None 且不為空時才加入
                        if self.eos and len(self.eos) > 0:
                            complete_params["stop"] = self.eos
                            
                        response = self.client.completions.create(**complete_params)
                        
                        generation = response.choices[0].text
                        
                        # 組裝結果格式
                        result = {
                            'task_id': task_id,
                            'completion_id': completion_id,
                            'completion': refine_text(generation)
                        }
                        batch_generations.append(result)
                        
                except Exception as e:
                    print(f"API 調用錯誤: {e}")
                    error_result = {
                        'task_id': task_id,
                        'completion_id': completion_id,
                        'completion': f"# Error: {str(e)}"
                    }
                    batch_generations.append(error_result)

            generations.extend(batch_generations)

        grouped_generations = [generations[i:i + num_samples] for i in range(0, len(generations), num_samples)]
        assert len(grouped_generations) == len(prompt_set)
        assert all(len(grouped_generations[i]) == num_samples for i in range(len(grouped_generations)))
        return sum(grouped_generations, [])