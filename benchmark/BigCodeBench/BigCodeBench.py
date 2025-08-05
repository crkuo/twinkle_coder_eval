import os, sys
if __name__ == '__main':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import env

from typing import List, Literal

from benchmark.base import Benchmark
from sanitize import sanitize
from utils import refine_text, stream_jsonl, read_metafile
from engine.registry import register_benchmark

info = read_metafile(os.path.dirname(os.path.abspath(__file__)))

@register_benchmark('BigCodeBench')
class BigCodeBench(Benchmark):
    name: str = info.get("Name")
    fullset_path = os.path.join(env.DATASET_CACHE_FOLDER, "BigCodeBench", "BigCodeBench.jsonl")
    subset_path = os.path.join(env.DATASET_CACHE_FOLDER, "BigCodeBench", "BigCodeBench_Hard.jsonl")

    def __init__(self,
                 name: str = "BigCodeBench",
                 timeout: float = 10.0,
                 prompt_type: Literal["Completion", "Instruction"] = "Completion"
                 ):
        
        super().__init__()
        
        self.name = name
        self.timeout = timeout
        self.prompt_type = prompt_type

        if self.name == "BigCodeHard":
            self.path = self.subset_path
        elif self.name == "BigCodeBench":
            self.path = self.fullset_path

        self.tasks = self.get_task()

    def prepare_dataset(self):
        """
        Download dataset if not exists - placeholder implementation
        """
        if os.path.exists(self.path):
            return
        # TODO: 實現實際的下載邏輯
        print(f"Dataset not found at {self.path}. Please download BigCodeBench dataset.")
        pass

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
    
    def get_prompt(self):
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
            task_data.get("code_prompt", task_data.get("prompt", "")) + "\n" 
            + "    pass\n" + "\n"
            + solution['solution'] + "\n"
        )
        
        # BigCodeBench 需要特殊的執行邏輯，暫時用 pass 跳過
        # TODO: 實現 BigCodeBench 特定的測試執行邏輯
        try:
            # 這裡需要實現 BigCodeBench 的 unit test 執行
            # from eval.unit_test import check_correctness
            # result = check_correctness(solution['task_id'],
            #                           solution['completion_id'],
            #                           code,
            #                           task_data["test"],
            #                           self.timeout)
            pass
        except:
            pass
        
        # 暫時返回假結果
        result = {
            'task_id': solution['task_id'],
            'completion_id': solution['completion_id'],
            'passed': False,
            'result': 'not implemented: BigCodeBench evaluation pending',
            'solution': solution.get('solution', '')
        }
        
        return result