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
from tools.utils import make_chat_prompt, refine_text

@register_backend('vllm')
class VllmGenerator(Generator):
    def __init__(self,
                 model_name: str,
                 arguments: dict = None,
                 model_type: str = "Instruction",
                 batch_size: int = 1,
                 temperature: float = 0.0,
                 max_tokens: int = 1024,
                 # Backward compatibility parameters
                 tokenizer_name: str = None,
                 dtype: str = "bfloat16",
                 num_gpus: int = 1,
                 trust_remote_code: bool = True,
                 **kwargs
                ) -> None:
        super().__init__(model_name)

        print("Initializing a decoder model: {} ...".format(model_name))
        
        # Process vLLM parameters: arguments contains parameters passed to LLM(), with backward compatibility for direct parameters
        if arguments is None:
            arguments = {}
            
        # Set basic attributes, prioritizing direct parameters (backward compatibility)
        self.tokenizer_name = tokenizer_name or model_name
        self.model_type = model_type
        self.batch_size = batch_size
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.dtype = dtype
        self.num_gpus = num_gpus
        self.trust_remote_code = trust_remote_code
        
        # Prepare LLM initialization parameters, arguments take priority
        llm_args = {
            'model': self.model_name,
            'tokenizer': None,
            'max_model_len': self.max_tokens,
            'tensor_parallel_size': self.num_gpus,
            'trust_remote_code': self.trust_remote_code,
            'dtype': self.dtype,
        }
        
        # Update parameters from arguments
        llm_args.update(arguments)
        
        # If these parameters exist in arguments, update corresponding instance attributes
        if 'max_model_len' in arguments:
            self.max_tokens = arguments['max_model_len']
        if 'tensor_parallel_size' in arguments:
            self.num_gpus = arguments['tensor_parallel_size']
        if 'trust_remote_code' in arguments:
            self.trust_remote_code = arguments['trust_remote_code']
        if 'dtype' in arguments:
            self.dtype = arguments['dtype']
        
        # Add additional kwargs
        llm_args.update(kwargs)
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_name,
                                                       model_max_length = self.max_tokens,
                                                       trust_remote_code = self.trust_remote_code,
                                                       use_fast = True)

        self.model = LLM(**llm_args)
        print(f"vLLM model initialized with dtype: {self.dtype}, GPUs: {self.num_gpus}")
        
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