import os, sys
if __name__ == '__main':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from tools.env_utils import get_dataset_cache_folder

from typing import List

from benchmark.base import Benchmark
from tools.sanitize import sanitize
from eval.execution import check_correctness
from tools.utils import refine_text, stream_jsonl, read_metafile
from engine.registry import register_benchmark

info = read_metafile(os.path.dirname(os.path.abspath(__file__)))

@register_benchmark('MBPPPlus')
class MBPPPlus(Benchmark):
    name: str = info.get("Name")
    path = os.path.join(get_dataset_cache_folder(), "MBPPPlus", "MBPPPlus.jsonl")

    def __init__(self,
                 name: str = "MBPPPlus",
                 timeout: float = 3.0,
                 prompt_type: str = "Instruction"):
        
        super().__init__()
        self.name = name
        self.timeout = timeout
        self.prompt_type = prompt_type

        self.tasks = self.get_task()

    def prepare_dataset(self):
        """
        Download and prepare the MBPPPlus dataset from Hugging Face.
        """
        if os.path.exists(self.path):
            return
            
        print(f"Preparing MBPPPlus dataset at {self.path}...")
        
        # Create directory if it doesn't exist
        dataset_dir = os.path.dirname(self.path)
        os.makedirs(dataset_dir, exist_ok=True)
        
        try:
            # Load MBPPPlus dataset from Hugging Face
            print("Loading MBPPPlus dataset from Hugging Face...")
            from datasets import load_dataset
            # Try MBPPPlus dataset sources
            dataset_names = [
                "evalplus/mbppplus"
            ]
            
            dataset_loaded = False
            for dataset_name in dataset_names:
                try:
                    print(f"Trying to load {dataset_name}...")
                    dataset = load_dataset(dataset_name, split="test", trust_remote_code=True)
                    
                    print(f"Loaded {len(dataset)} tasks from {dataset_name}")
                    dataset.to_json(self.path, lines=True, force_ascii=False)
                    dataset_loaded = True
                    
                except Exception as e:
                    print(f"Failed to load {dataset_name}: {e}")
                    continue
            
            if not dataset_loaded:
                print("Warning: Failed to load MBPPPlus dataset from any source")
                print("MBPPPlus benchmark will run with empty dataset")
                
        except Exception as e:
            print(f"Warning: Failed to load MBPPPlus dataset: {e}")
            print("MBPPPlus benchmark will run with empty dataset")

    def get_task(self):
        """
        Get the task data from the jsonl file into a dictionary.
        """
        tasks = {}
        
        if not os.path.exists(self.path):
            self.prepare_dataset()
            
        try:
            for task_data in stream_jsonl(filename=self.path):
                task_id = int(task_data["task_id"])
                tasks[task_id] = task_data
        except FileNotFoundError:
            print(f"Warning: MBPPPlus dataset not found at {self.path}")
            # 返回空字典以避免程序崩潰
            return {}
        
        return tasks
    
    def format_prompt(self, 
                     problem: str,
                     test: str,
                     ) -> str:
        prompt = problem + "\n" + test
        return prompt
    
    def get_prompts(self):
        """
        Builds the prompt for the LM to generate from.
        """
        assert self.prompt_type == "Instruction", f"Prompt type must be Instruction for {self.name}"

        prompts = []
        for task_id, task_data in self.tasks.items():
            prompt = self.format_prompt(task_data["prompt"], task_data["test_list"][0])
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
        result = dict(
            task_id = generation['task_id'],
            completion_id = generation['completion_id'],
            solution = sanitize(generation['completion'])
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

        if self.name == "MBPPPlus":
            test_code = task_data.get('test', '')
        elif self.name == "MBPPBase":
            test_imports = task_data.get('test_imports', [])
            test_list = task_data.get('test_list', [])
            test_code = "\n".join(test_imports) + "\n\n" + "\n".join(test_list)
        else:
            test_code = task_data.get('test', '')
        
        code = (
            "\n".join(self.imports) + "\n\n"
            + solution['solution'] + "\n\n"
            + "\n".join(task_data.get('test_imports', [])) + "\n\n"
            + test_code + "\n\n"
        )
        
        result = check_correctness(solution['task_id'],
                                   solution['completion_id'],
                                   code,
                                   self.timeout)
        
        return result