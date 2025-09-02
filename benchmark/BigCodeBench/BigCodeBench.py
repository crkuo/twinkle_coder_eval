import os, sys
if __name__ == '__main':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from tools.env_utils import get_dataset_cache_folder

from typing import List, Literal

from benchmark.base import Benchmark
from tools.sanitize import sanitize
from tools.utils import refine_text, stream_jsonl, read_metafile
from engine.registry import register_benchmark
from eval.execution import check_correctness

info = read_metafile(os.path.dirname(os.path.abspath(__file__)))

@register_benchmark('BigCodeBench')
class BigCodeBench(Benchmark):
    name: str = info.get("Name")
    path = os.path.join(get_dataset_cache_folder(), "BigCodeBench", "bigcodebench.jsonl")

    def __init__(self,
                 name: str = "BigCodeBench",
                 timeout: float = 10.0,
                 prompt_type: Literal["Completion", "Instruction"] = "Completion"
                 ):
        
        super().__init__()
        
        self.name = name
        self.timeout = timeout
        self.prompt_type = "Completion"
        self.tasks = self.get_task()

    def prepare_dataset(self):
        """
        Download and prepare the BigCodeBench dataset from Hugging Face.
        """
        if os.path.exists(self.path):
            return
            
        print(f"Preparing BigCodeBench dataset at {self.path}...")
        
        # Create directory if it doesn't exist
        dataset_dir = os.path.dirname(self.path)
        os.makedirs(dataset_dir, exist_ok=True)
        
        try:
            # Load BigCodeBench dataset from Hugging Face
            print("Loading BigCodeBench dataset from Hugging Face...")
            from datasets import load_dataset
            
            dataset_loaded = False
            try:
                print("Trying to load bigcode/bigcodebench...")
                # Try different splits for BigCodeBench
                splits_to_try = ["v0.1.2", "v0.1.4", "v0.1.0_hf"]
                dataset = None
                for split in splits_to_try:
                    try:
                        dataset = load_dataset("bigcode/bigcodebench", split=split, trust_remote_code=True)
                        break
                    except:
                        continue
                if dataset is None:
                    raise Exception("No valid split found for bigcode/bigcodebench")
                
                print(f"Loaded {len(dataset)} tasks from bigcode/bigcodebench")
                dataset.to_json(self.path, lines=True, force_ascii=False)
                dataset_loaded = True
                
            except Exception as e:
                print(f"Failed to load bigcode/bigcodebench: {e}")
            
            if not dataset_loaded:
                print("Warning: Failed to load BigCodeBench dataset from any source")
                print("BigCodeBench benchmark will run with empty dataset")
                
        except Exception as e:
            print(f"Warning: Failed to load BigCodeBench dataset: {e}")
            print("BigCodeBench benchmark will run with empty dataset")

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
            print(f"Warning: BigCodeBench dataset not found at {self.path}")
            # 返回空字典以避免程序崩潰
            return {}
        
        return tasks
    
    def get_prompts(self):
        """
        Builds the prompt for the LM to generate from.
        """
        prompts = []
        for task_id, task_data in self.tasks.items():
            if self.prompt_type == "Completion":
                prompt = task_data.get('complete_prompt', task_data.get('prompt', ''))
            elif self.prompt_type == "Instruction":
                prompt = task_data.get('instruct_prompt', task_data.get('prompt', ''))
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
        if generation['task_id'] not in self.tasks:
            return dict(
                task_id = generation['task_id'],
                completion_id = generation['completion_id'],
                solution = ""
            )

        entry_point = self.tasks[generation['task_id']].get("entry_point", None)

        result = dict(
            task_id = generation['task_id'],
            completion_id = generation['completion_id'],
            solution = sanitize(generation['completion'], entry_point) if entry_point else generation['completion']
        )

        return result

    def process_results(self, solution):
        """
        Takes the list of LM generations and evaluates them against the test cases
        """
        assert solution['task_id'] in self.tasks
        task_data = self.tasks[solution['task_id']]

        code = (
            task_data.get("code_prompt", task_data.get("prompt", "")) + "\n" 
            + "    pass\n" + "\n"
            + solution['solution'] + "\n"
        )
        
        result = check_correctness(solution['task_id'],
                                    solution['completion_id'],
                                    code,
                                    self.timeout,
                                    tests=task_data["test"])
        
        return result