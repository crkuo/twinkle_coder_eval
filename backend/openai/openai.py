import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([os.path.dirname(ROOT), os.path.dirname(os.path.dirname(ROOT))])

from openai import OpenAI
import httpx
from tqdm import tqdm
from typing import List

from backend.base import Generator
from utils import make_chat_prompt, refine_text

class OpenaiGenerator(Generator):
    def __init__(self,
                 model_name: str,
                 model_type: str = "Chat",
                 batch_size : int = 1,
                 temperature : float = 0.0,
                 max_tokens : int = 1024,
                 eos: List[str] = None,
                 api_key: str = "token-abc123",
                 base_url: str = "https://4123-210-242-28-146.ngrok-free.app/v1",
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
            base_url=base_url,
            api_key=api_key,
            http_client=httpx.Client(verify=False)
        )
        
        print(f"OpenAI client initialized with base_url: {base_url}")
        print(f"Model: {model_name}")
        print(f"Model type: {model_type}")

    def is_chat(self) -> bool:
        return self.model_type == "Chat"

    def generate(self, prompts: List[str],
                 num_samples: int = 200,
                 response_prefix: str = ""
                ) -> List[str]:

        # 如果是 Chat 模式，構建 chat prompt（但這裡直接使用原始 prompt）
        if self.is_chat():
            print("Using Chat Completion API")
        else:
            print("Using Text Completion API")
        
        print(f"First prompt: {prompts[0]}")
        sample_prompts = [prompt for prompt in prompts for _ in range(num_samples)]

        assert len(sample_prompts) == (len(prompts) * num_samples)
        assert all(sample_prompts[i:i + num_samples] == [sample_prompts[i]] * num_samples for i in range(0, len(sample_prompts), num_samples))

        generations = []

        for batch_start in tqdm(range(0, len(sample_prompts), self.batch_size)):
            batch = sample_prompts[batch_start : batch_start + self.batch_size]
            
            batch_generations = []
            for prompt in batch:
                try:
                    full_prompt = response_prefix + prompt
                    
                    if self.is_chat():
                        # 使用 Chat Completion API
                        messages = [{"role": "user", "content": full_prompt}]
                        
                        response = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=messages,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens,
                            stop=self.eos
                        )
                        
                        generation = response.choices[0].message.content
                        batch_generations.append(refine_text(generation))
                        
                    else:
                        # 使用 Text Completion API
                        response = self.client.completions.create(
                            model=self.model_name,
                            prompt=full_prompt,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens,
                            stop=self.eos
                        )
                        
                        generation = response.choices[0].text
                        batch_generations.append(refine_text(prompt + "\n" + generation))
                        
                except Exception as e:
                    print(f"API 調用錯誤: {e}")
                    batch_generations.append(f"# Error: {str(e)}")

            generations.extend(batch_generations)

        grouped_generatuons = [generations[i:i + num_samples] for i in range(0, len(generations), num_samples)]
        assert len(grouped_generatuons) == len(prompts)
        assert all(len(grouped_generatuons[i]) == num_samples for i in range(len(grouped_generatuons)))

        return grouped_generatuons