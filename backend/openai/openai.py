import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([os.path.dirname(ROOT), os.path.dirname(os.path.dirname(ROOT))])

from openai import OpenAI
from tqdm import tqdm
from typing import List, Dict

from backend.base import Generator
from tools.utils import refine_text
from tools.env_utils import get_api_key, get_api_base_url, load_environment, get_env_var
from engine.registry import register_backend
import time
import json
@register_backend('openai')
class OpenaiGenerator(Generator):
    def __init__(self,
                 model_name: str,
                 arguments: dict,
                 model_type: str = "Chat"
               ) -> None:
        super().__init__(model_name)
        
        # Load environment variables
        load_environment()
        
        # Prepare OpenAI client arguments with environment fallbacks
        client_args = dict(arguments)
        
        # Use environment variables if not provided in config
        if 'api_key' not in client_args or not client_args['api_key']:
            env_api_key = get_api_key('openai')
            if env_api_key:
                client_args['api_key'] = env_api_key
                print("Using API key from environment variables")
            else:
                raise ValueError("API key not found in config or environment variables. Please set OPENAI_API_KEY in .env file")
        
        if 'base_url' not in client_args or not client_args['base_url']:
            env_base_url = get_api_base_url('openai')
            if env_base_url:
                client_args['base_url'] = env_base_url
                print(f"Using base URL from environment: {env_base_url}")
        
        # 初始化 OpenAI 客戶端
        self.client = OpenAI(**client_args)
        self.model_type = model_type
        print(f"OpenAI client initialized with base_url: {client_args.get('base_url')}")

        
    def is_chat(self) -> bool:
        return self.model_type == "Chat"

    def generate_with_stream_auto_continue(self, prompt, create_params, max_rounds=None):
        """
        串流 + 自動續寫。
        規則：
        - 若 finish_reason == "length"，就把目前已產生文字當成 assistant 回到對話裡，接著讓 user 說「Please continue.」
        - 最多續寫 max_rounds 輪（包含第 1 輪）
        """
        # Use environment variable if max_rounds not specified
        if max_rounds is None:
            max_rounds = get_env_var('REQUESTS_ROUND_LIMIT', '20', int)
        
        s = time.time()
        base_messages = [{"role": "user", "content": prompt}]
        current_messages = list(base_messages)
        full_text = ""
        final_finish_reason = "stop"
        num_response = 0
        for round_idx in range(max_rounds):
            try:
                current_params = create_params.copy()
                current_params["messages"] = current_messages
                
                response = self.client.chat.completions.create(**current_params)
                choice = response.choices[0]
                message = choice.message
                content = message.content if message.content is not None else ""
                finish_reason = choice.finish_reason
                
                full_text += content
                final_finish_reason = finish_reason
                num_response += 1
                if finish_reason != "length":
                    # 正常完成（"stop" 或其他），結束
                    break
                
                # 被切斷：把已產生片段放回歷史，再要求繼續
                current_messages += [
                    {"role": "assistant", "content": content if content else ""},
                    {"role": "user", "content": "Please continue where you left off, without repeating."},
                ]
                
            except Exception as e:
                print(f"串流獲取回應時出錯 (輪次 {round_idx + 1}): {e}")
                final_finish_reason = 'error'
                break
        e = time.time()
        result = {
            "generation": full_text,
            "finish_reason": final_finish_reason,
            "num_response": num_response,
            "time_elapsed": e-s
        }
        return result
    def generate_with_normal_mode(self, prompt:str, create_params:dict, max_rounds=20):
        s = time.time()
        messages = [{"role": "user", "content": prompt}]
        full_text = ""
        final_finish_reason = "stop"
        finish_reason = None
        num_response = 0
        
        for round_idx in range(max_rounds):
            try:
                create_params['messages'] = messages
                response = self.client.chat.completions.create(**create_params)
                choice = response.choices[0]
                message = choice.message
                finish_reason = choice.finish_reason
                final_finish_reason = finish_reason
                text = message.content if message.content is not None else ""
                full_text += text
                num_response += 1
                if finish_reason != 'length':
                    break
                messages += [
                    {"role": "assistant", "content": text},
                    {"role": "user", "content": "Please continue where you left off, without repeating."},
                ]
            except Exception as e:
                import traceback
                print(f"獲取回應時出錯 (輪次 {round_idx + 1}): {e}")
                print(traceback.format_exc())
                final_finish_reason = 'error'
                break
        e = time.time()
        result = {
            "generation": full_text,
            "finish_reason": final_finish_reason,
            "num_response": num_response,
            "time_elapsed": e-s
        }
        return result
            

    def generate(self,
                 prompt_set: List[Dict],
                 num_samples: int = 200,
                 eos: List[str] = None,
                 response_prefix: str = "",
                 response_suffix: str = "",
                 batch_size = 1,
                 generate_args: dict = ""
                ) -> List[str]:
        # 構建樣本提示
        sample_prompts = []
        for prompt_data in prompt_set:
            for _ in range(num_samples):
                sample_prompts.append(prompt_data)

        assert len(sample_prompts) == (len(prompt_set) * num_samples)
        assert all(sample_prompts[i:i + num_samples] == [sample_prompts[i]] * num_samples for i in range(0, len(sample_prompts), num_samples))

        generations = []
        create_params = generate_args
        create_params.update({"model": self.model_name})
        if eos and len(eos) > 0 and isinstance(eos, list):
            create_params["stop"] = eos
        use_stream = create_params.get('stream', False)
        for batch_start in range(0, len(sample_prompts), batch_size):
            batch = sample_prompts[batch_start : batch_start + batch_size]
            batch_generations = []
            for prompt_data in batch:
                try:
                    prompt_text = prompt_data['prompt']
                    task_id = prompt_data['task_id']
                    completion_id = batch_start + len(batch_generations)
                    
                    full_prompt = response_prefix + prompt_text +response_suffix
                    if use_stream:
                        generation_result = self.generate_with_stream_auto_continue(full_prompt, create_params)
                    else:
                        generation_result = self.generate_with_normal_mode(full_prompt, create_params)
                    generation = generation_result.get("generation", "")
                    finish_reason = generation_result.get("finish_reason", "")
                    time_elapsed = generation_result.get("time_elapsed", 0)
                    num_requests = generation_result.get("num_response", 1)
                    result = {
                        'task_id': task_id,
                        'completion_id': completion_id,
                        'completion': refine_text(generation) if generation else "",
                        'finish_reason': finish_reason,
                        'time_elapsed': time_elapsed,
                        'num_requests': num_requests
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