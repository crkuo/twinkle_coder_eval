import os, sys
if __name__ == '__main':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import env

from typing import List

from benchmark.base import Benchmark
from tools.sanitize import sanitize
from eval.execution import check_correctness
from tools.utils import refine_text, stream_jsonl, read_metafile
from engine.registry import register_benchmark

info = read_metafile(os.path.dirname(os.path.abspath(__file__)))

@register_benchmark('LeetCode')
class LeetCode(Benchmark):
    name: str = info.get("Name")
    path = os.path.join(env.DATASET_CACHE_FOLDER, "LeetCode", "20240121-Jul.jsonl")

    def __init__(self,
                 name: str = "LeetCode",
                 timeout: float = 3.0,
                 prompt_type: str = "Completion"): 
        super().__init__()
        
        self.name = name
        self.timeout = timeout
        self.prompt_type = prompt_type

        self.tasks = self.get_task()

    def prepare_dataset(self):
        """
        Download and prepare the LeetCode dataset from Hugging Face.
        """
        if os.path.exists(self.path):
            return
            
        print(f"Preparing LeetCode dataset at {self.path}...")
        
        # Create directory if it doesn't exist
        dataset_dir = os.path.dirname(self.path)
        os.makedirs(dataset_dir, exist_ok=True)
        
        try:
            # Try loading from Hugging Face
            print("Loading LeetCode dataset from Hugging Face...")

            
            # Try different possible dataset names for LeetCode
            dataset_names = [
                "TechxGenus/LeetCode-Contest"
            ]
            
            dataset_loaded = False
            for dataset_name in dataset_names:
                try:
                    from huggingface_hub import hf_hub_download
                    print(f"Trying to download from {dataset_name}...")
                    
                    # Download the dataset file
                    downloaded_file = hf_hub_download(
                        repo_id=dataset_name, 
                        filename=os.path.basename(self.path), 
                        local_dir=os.path.dirname(self.path),
                        repo_type="dataset"
                    )
                    
                    print(f"Successfully downloaded to {downloaded_file}")
                    dataset_loaded = True
                    break
                    
                except Exception as e:
                    print(f"Failed to load {dataset_name}: {e}")
                    continue
            
            if not dataset_loaded:
                raise Exception("No suitable dataset found")
                
        except Exception as e:
            print(f"Warning: Failed to load LeetCode dataset: {e}")
            print("LeetCode benchmark will run with empty dataset")

    def get_task(self):
        """
        Get the task data from the jsonl file into a dictionary.
        """
        tasks = {}
        
        if not os.path.exists(self.path):
            self.prepare_dataset()
            
        try:
            for task_data in stream_jsonl(filename=self.path):
                task_id = int(task_data["meta"]["questionId"])
                tasks[task_id] = task_data
        except FileNotFoundError:
            print(f"Warning: LeetCode dataset not found at {self.path}")
            # 返回空字典以避免程序崩潰
            return {}
        except (KeyError, ValueError):
            print(f"Warning: Invalid LeetCode dataset format")
            return {}
        
        return tasks
        
    def get_prompts(self):
        """
        Builds the prompt for the LM to generate from.
        """
        prompts = []
        for task_id, task_data in self.tasks.items():

            if self.prompt_type == "Completion":
                prompt = task_data.get('prompt', '')
            elif self.prompt_type == "Instruction":
                prompt = task_data.get('prompt_sft', task_data.get('prompt', ''))
            else:
                prompt = task_data.get('prompt', '')

            prompts.append(
                dict(
                    task_id = task_id,
                    prompt = refine_text(prompt)
                )
            )

        return prompts

    def postprocess_generation(self, generation):
        """
        Postprocess the generations.
        """
        return dict(
            task_id = generation['task_id'],
            completion_id = generation['completion_id'],
            solution = sanitize(generation['completion'])
        )
    
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

        code = (
            "\n".join(self.imports) + "\n\n"
            + solution['solution'] + "\n\n"
            + task_data.get('test', '')
        )
        
        result = check_correctness(solution['task_id'],
                                   solution['completion_id'],
                                   code,
                                   self.timeout)
        
        return result