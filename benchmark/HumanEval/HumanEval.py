import os, sys
if __name__ == '__main':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import env

from typing import List

from benchmark.base import Benchmark
from sanitize import sanitize
from eval.execution import check_correctness
from utils import refine_text, stream_jsonl, read_metafile
from engine.registry import register_benchmark

info = read_metafile(os.path.dirname(os.path.abspath(__file__)))

@register_benchmark('HumanEval')
class HumanEval(Benchmark):
    name: str = info.get("Name")
    path = os.path.join(env.DATASET_CACHE_FOLDER, "HumanEval", "HumanEval.jsonl")

    def __init__(self,
                 name: str = "HumanEval",
                 timeout: float = 3.0,
                 prompt_type: str = "Completion"): 
        super().__init__()
        
        self.name = name
        self.timeout = timeout
        self.prompt_type = prompt_type
        self.tasks = self.get_task()

    def prepare_dataset(self):
        """
        Download and prepare the HumanEval dataset from OpenAI's GitHub repository.
        """
        if os.path.exists(self.path):
            return
            
        print(f"Preparing HumanEval dataset at {self.path}...")
        
        # Create directory if it doesn't exist
        dataset_dir = os.path.dirname(self.path)
        os.makedirs(dataset_dir, exist_ok=True)
        
        try:
            # Method 1: Try downloading from OpenAI's GitHub repository
            import requests
            import gzip
            import json
            
            github_url = "https://github.com/openai/human-eval/raw/master/data/HumanEval.jsonl.gz"
            
            print("Downloading HumanEval dataset from OpenAI GitHub...")
            response = requests.get(github_url, timeout=60)
            response.raise_for_status()
            
            # Decompress and save the dataset
            decompressed_data = gzip.decompress(response.content).decode('utf-8')
            with open(self.path, 'w', encoding='utf-8') as f:
                f.write(decompressed_data)
                    
            print(f"Successfully downloaded HumanEval dataset to {self.path}")
            
        except Exception as github_error:
            print(f"Failed to download from GitHub: {github_error}")
            
            # Method 2: Fallback to Hugging Face datasets
            try:
                print("Trying Hugging Face datasets as fallback...")
                from datasets import load_dataset
                
                dataset = load_dataset("openai_humaneval", split="test", trust_remote_code=True)
                
                # Convert to the expected format and save as JSONL
                with open(self.path, 'w', encoding='utf-8') as f:
                    for item in dataset:
                        # Convert to expected format
                        task_data = {
                            "task_id": item["task_id"],
                            "prompt": item["prompt"],
                            "canonical_solution": item["canonical_solution"],
                            "test": item["test"],
                            "entry_point": item["entry_point"]
                        }
                        f.write(json.dumps(task_data, ensure_ascii=False) + '\n')
                        
                print(f"Successfully prepared HumanEval dataset from Hugging Face to {self.path}")
                
            except Exception as hf_error:
                print(f"Failed to load from Hugging Face: {hf_error}")
        
        # Validate the downloaded dataset
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line:
                        test_data = json.loads(first_line)
                        required_fields = ["task_id", "prompt", "test", "entry_point"]
                        if all(field in test_data for field in required_fields):
                            print("Dataset validation successful!")
                        else:
                            print(f"Warning: Dataset may be missing required fields: {required_fields}")
            except Exception as e:
                print(f"Warning: Could not validate dataset format: {e}")
        else:
            raise RuntimeError("Dataset preparation failed - file not found after download attempt")

    def get_task(self):
        """
        Get the task data from the jsonl file into a dictionary.
        """
        tasks = {}
        
        if not os.path.exists(self.path):
            self.prepare_dataset()
            
        try:
            for task_data in stream_jsonl(filename=self.path):
                task_id = int(task_data["task_id"].split("/")[-1])
                tasks[task_id] = task_data
        except FileNotFoundError:
            print(f"Warning: HumanEval dataset not found at {self.path}")
            # 返回空字典以避免程序崩潰
            return {}
        
        return tasks

    def get_prompt(self):
        """
        Builds the prompt for the LM to generate from.
        """
        assert self.prompt_type == "Completion", f"Prompt type must be Completion for HumanEval"

        prompts = []
        for task_id, task_data in self.tasks.items():
            prompts.append(
                dict(
                    task_id = task_id,
                    prompt = refine_text(task_data['prompt'])
                )
            )
        return prompts

    def postprocess_generation(self, generation):
        """
        Postprocess the generations.
        """
        if generation['task_id'] not in self.tasks:
            return dict(
                task_id = generation['task_id'],
                completion_id = generation['completion_id'],
                solution = ""
            )

        entry_point = self.tasks[generation['task_id']]["entry_point"]

        result = dict(
            task_id = generation['task_id'],
            completion_id = generation['completion_id'],
            solution = sanitize(generation['completion'], entry_point)
        )

        return result

    def process_results(self, solution):
        """
        Takes the list of LM generations and evaluates them against the test cases
        """
        if solution['task_id'] not in self.tasks:
            return {
                'task_id': solution['task_id'],
                'completion_id': solution['completion_id'],
                'passed': False,
                'result': 'failed: task not found',
                'solution': solution.get('solution', '')
            }

        task_data = self.tasks[solution['task_id']]

        code = ("\n".join(self.imports) + "\n"
                    + task_data["prompt"] + "\n"
                    + "    pass\n" + "\n"
                    + solution['solution'] + "\n"
                    + task_data['test'] + "\n"
                    + f"check({task_data['entry_point']})"
                )
        
        result = check_correctness(solution['task_id'],
                                   solution['completion_id'],
                                   code,
                                   self.timeout)
        
        return result