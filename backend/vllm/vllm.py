import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([os.path.dirname(ROOT), os.path.dirname(os.path.dirname(ROOT))])

import gc
import torch
from loguru import logger

from tqdm import tqdm
from typing import List, Dict

from transformers import AutoTokenizer

from vllm import LLM, SamplingParams
from vllm.distributed.parallel_state import destroy_distributed_environment, destroy_model_parallel

from backend.base import Generator
from engine.registry import register_backend
from utils import make_chat_prompt, refine_text

@register_backend('vllm')
class VllmGenerator(Generator):
    def __init__(self,
                 model_name: str,
                 server_params: dict = None,
                 model_type: str = "Instruction",
                 batch_size: int = 1,
                 temperature: float = 0.0,
                 max_tokens: int = 1024,
                 # 向後兼容參數
                 tokenizer_name: str = None,
                 dtype: str = "bfloat16",
                 num_gpus: int = 1,
                 trust_remote_code: bool = True,
                 **kwargs
                ) -> None:
        super().__init__(model_name)

        print("Initializing a decoder model: {} ...".format(model_name))
        
        # 參數處理邏輯：優先使用 server_params，向後兼容直接參數
        if server_params is None:
            server_params = {}
            
        # 合併參數，server_params 優先
        self.tokenizer_name = server_params.get('tokenizer_name', tokenizer_name) or model_name
        self.model_type = model_type
        self.batch_size = batch_size
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.dtype = server_params.get('dtype', dtype)
        self.num_gpus = server_params.get('num_gpus', num_gpus)
        self.trust_remote_code = server_params.get('trust_remote_code', trust_remote_code)
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_name,
                                                       model_max_length = self.max_tokens,
                                                       trust_remote_code = self.trust_remote_code,
                                                       use_fast = True)

        self.model = LLM(model = self.model_name,
                         tokenizer = None,
                         max_model_len = self.max_tokens,
                         tensor_parallel_size = self.num_gpus,
                         trust_remote_code = self.trust_remote_code)
        
        self.model.set_tokenizer(tokenizer = self.tokenizer)

    def is_chat(self) -> bool:
        if self.model_type == "Chat":
            assert self.tokenizer.chat_template is not None
            return True
        else:
            return False
        
    def release_memory(self):
        destroy_model_parallel
        destroy_distributed_environment()
        del self.model.llm_engine.model_executor
        del self.model
        gc.collect()
        torch.cuda.empty_cache()

    def generate(self,
                 prompt_set: List[Dict],
                 num_samples: int = 200,
                 eos: List[str] = None,
                 response_prefix: str = "",
                 response_suffix: str = ""
                ) -> List[str]:

        if self.is_chat():
            for prompt in prompt_set:
                prompt['prompt'] = make_chat_prompt(prompt['prompt'], self.tokenizer, response_prefix)

        logger.info("Example Prompt:\n{}", prompt_set[0]['prompt'])

        sampling_params = SamplingParams(
            n = num_samples,
            temperature = self.temperature,
            max_tokens = self.max_tokens,
            top_p = 1.0,
            stop = eos,
        )

        generation_set = []

        for batch_start in tqdm(range(0, len(prompt_set), self.batch_size)):
            batch_prompt = prompt_set[batch_start : batch_start + self.batch_size]
            batch_outputs = self.model.generate(
                [prompt['prompt'] for prompt in batch_prompt],
                sampling_params,
                use_tqdm = False,
            )

            for prompt, output in zip(batch_prompt, batch_outputs):

                completions = [completion.text for completion in output.outputs]

                if not self.is_chat():
                    completions = [refine_text(prompt["prompt"] + "\n\n" + response_prefix + sample + response_suffix) for sample in completions]
                else:
                    completions = [refine_text(response_prefix + sample + response_suffix) for sample in completions]

                for completion_id, completion in enumerate(completions):
                    generation_set.append({
                        'task_id': prompt['task_id'],
                        'completion_id': completion_id,
                        'completion': completion
                    })

        assert len(generation_set) == len(prompt_set) * num_samples, "Number of generations does not match the expected number."

        self.release_memory()

        return generation_set