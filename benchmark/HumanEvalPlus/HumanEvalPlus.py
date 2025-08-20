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

@register_benchmark('HumanEvalPlus')
class HumanEvalPlus(Benchmark):
    name: str = info.get("Name")
    path = os.path.join(env.DATASET_CACHE_FOLDER, "HumanEvalPlus", "HumanEvalPlus.jsonl")

    def __init__(self,
                 name: str = "HumanEvalPlus",
                 timeout: float = 3.0,
                 prompt_type: str = "Completion"): 
        super().__init__()
        
        self.name = name
        self.timeout = timeout
        self.prompt_type = prompt_type
        self.tasks = self.get_task()

    def prepare_dataset(self):
        """
        Download and prepare the HumanEval+ dataset from Hugging Face.
        """
        if os.path.exists(self.path):
            return
            
        print(f"Preparing HumanEval+ dataset at {self.path}...")
        
        # Create directory if it doesn't exist
        dataset_dir = os.path.dirname(self.path)
        os.makedirs(dataset_dir, exist_ok=True)
        
        try:
            # Load HumanEval+ dataset from Hugging Face
            print("Loading HumanEval+ dataset from Hugging Face...")
            from datasets import load_dataset
            import json
            
            dataset = load_dataset("evalplus/humanevalplus", split="test", trust_remote_code=True)
            print(f"Loaded {len(dataset)} tasks from HumanEval+ dataset")
            
            dataset.to_json(self.path, lines=True, force_ascii=False)
            print(f"Successfully prepared HumanEval+ dataset from Hugging Face to {self.path}")
            
        except Exception as hf_error:
            print(f"Failed to load from Hugging Face: {hf_error}")

        
        # Validate the downloaded dataset
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line:
                        import json
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
            print(f"Warning: HumanEval+ dataset not found at {self.path}")
            # 返回空字典以避免程序崩潰
            return {}
        
        return tasks

    def get_prompts(self):
        """
        Builds the prompt for the LM to generate from.
        """
        assert self.prompt_type == "Completion", f"Prompt type must be Completion for HumanEval+"

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