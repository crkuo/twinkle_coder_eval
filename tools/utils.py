import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([os.path.dirname(ROOT), os.path.dirname(os.path.dirname(ROOT))])
import re
import gzip
import json
import itertools
import numpy as np

from typing import Dict, List, Union, Iterable
from collections import defaultdict
# Conditional import for transformers - only used in vllm backend
try:
    from transformers import AutoTokenizer
    HAS_TRANSFORMERS = True
except ImportError:
    AutoTokenizer = None
    HAS_TRANSFORMERS = False

python_pattern = r"```python[ \t]*[\r\n]+(.*?)[ \t]*[\r\n]+```"
python_re = re.compile(python_pattern, re.DOTALL | re.IGNORECASE)

def extract_code_blocks(text: str, language: str = "python") -> list:
    """
    直接解析 markdown code fence，提取指定語言的代碼塊
    
    Args:
        text: markdown 文本
        language: 程式語言 (預設 python)
        
    Returns:
        list: 代碼塊列表
    """
    lines = text.split('\n')
    code_blocks = []
    current_block = []
    in_code_block = False
    
    for line in lines:
        stripped = line.strip()
        
        # 檢查代碼塊開始
        if stripped.startswith(f'```{language}'):
            in_code_block = True
            current_block = []
        elif stripped == '```' and in_code_block:
            # 代碼塊結束
            in_code_block = False
            if current_block:
                code_blocks.append('\n'.join(current_block))
        elif in_code_block:
            # 在代碼塊內，保留原始縮進
            current_block.append(line)
    
    return code_blocks

def python_extract(text: str) -> str:
    """
    從文本中提取 Python 代碼塊
    使用直接 markdown code fence 解析，優先選擇包含函數定義且語法正確的代碼塊
    """
    import ast
    
    # 使用直接 markdown 解析代替正則表達式
    code_blocks = extract_code_blocks(text, "python")
    
    # 如果沒有找到 python 代碼塊，嘗試通用代碼塊
    if not code_blocks:
        code_blocks = extract_code_blocks(text, "")
    
    # 如果還是沒有，嘗試原有的正則表達式方法作為後備
    if not code_blocks:
        matches = python_re.findall(text)
        code_blocks = [match.strip() for match in matches if match.strip()]
    
    if not code_blocks:
        return ""
    
    # 分類代碼塊：包含函數定義的優先
    function_blocks = []
    other_blocks = []
    
    for code_block in code_blocks:
        code = code_block.strip()
        if not code:
            continue
            
        # 檢查是否包含函數定義
        if 'def ' in code:
            function_blocks.append(code)
        else:
            other_blocks.append(code)
    
    # 優先處理包含函數定義的代碼塊
    candidates = function_blocks if function_blocks else other_blocks
    
    if not candidates:
        return ""
    
    # 如果只有一個候選，直接檢查並返回
    if len(candidates) == 1:
        code = candidates[0]
        try:
            ast.parse(code)
            return code
        except:
            return ""
    
    # 多個候選時，選擇最佳的一個
    best_code = ""
    best_score = -1
    
    for code in candidates:
        score = 0
        
        # 檢查語法是否正確
        try:
            ast.parse(code)
            score += 1000  # 語法正確是必要條件
        except:
            continue  # 語法錯誤的跳過
        
        # 包含函數定義的額外加分
        if 'def ' in code:
            score += 500
        
        # 檢查函數定義的完整性
        try:
            tree = ast.parse(code)
            function_count = sum(1 for node in ast.walk(tree) 
                               if isinstance(node, ast.FunctionDef))
            if function_count > 0:
                score += function_count * 100  # 每個函數定義加分
                
                # 檢查函數是否有返回語句
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        has_return = any(isinstance(n, ast.Return) 
                                       for n in ast.walk(node))
                        if has_return:
                            score += 50
        except:
            pass
        
        # 代碼長度作為次要標準
        score += len(code)
        
        if score > best_score:
            best_score = score
            best_code = code
    
    return best_code

def refine_text(text: str) -> str:
    text =  text.replace("\t", "    ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip() + "\n"

def format_test_example(q, tests, code: str=None):
    prompt = ">>> Problem:\n{}\n>>> Test Cases:\n{}\n".format(q.strip(), "\n".join(tests))
    if code:
        code = code.replace("\r", "").replace("\t", "    ")
        prompt += "\n>>> Code:\n```python\n{}\n```".format(code)
    return prompt

def make_chat_prompt(prompt: str,
                     tokenizer = None,
                     response_prefix: str = ""
                    ) -> str:
    """
    Create a chat prompt. This function is primarily used by the vllm backend.
    For other backends, it simply returns the original prompt with response_prefix.
    """
    # If no tokenizer provided (non-vllm backends), return simple format
    if tokenizer is None or not HAS_TRANSFORMERS:
        return response_prefix + prompt
    
    # Check if tokenizer has the expected attributes (for vllm backend)
    if not hasattr(tokenizer, 'chat_template'):
        return response_prefix + prompt
    
    # directly return prompt if it does not have a tokenizer.chat_template
    if tokenizer.chat_template:

        if 'ckpt' in tokenizer.name_or_path or 'checkpoint' in tokenizer.name_or_path or 'ckp' in tokenizer.name_or_path:

            return '''
### Instruction:
{}
### Response:
'''.format(prompt.strip()).lstrip()
        
        else:
            prompt = tokenizer.apply_chat_template(
            [
                {"role": "user", "content":  prompt},
            ],
            tokenize = False,
            add_generation_prompt = True
        ) + response_prefix
        
    # Handle bos_token if it exists
    if hasattr(tokenizer, 'bos_token') and tokenizer.bos_token and prompt.startswith(tokenizer.bos_token):
        return prompt[len(tokenizer.bos_token):]
    
    return prompt

def read_jsonl(filename: str) -> list[Dict]:
    """
    Reads an jsonl file to list
    """
    data = []
    with open(filename, 'r', encoding='utf-8') as fp:
        for line in fp:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(e)
    return data

def stream_jsonl(filename: str) -> Iterable[Dict]:
    """
    Parses each jsonl line and yields it as a dictionary
    """
    if filename.endswith(".gz"):
        with open(filename, "rb") as gzfp:
            with gzip.open(gzfp, 'rt') as fp:
                for line in fp:
                    if any(not x.isspace() for x in line):
                        yield json.loads(line)
    else:
        with open(filename, "r", encoding="utf-8") as fp:
            for line in fp:
                if any(not x.isspace() for x in line):
                    yield json.loads(line)


def write_jsonl(filename: str, data: Iterable[Dict], append: bool = False):
    """
    Writes an iterable of dictionaries to jsonl
    """
    if append:
        mode = 'ab'
    else:
        mode = 'wb'
    filename = os.path.expanduser(filename)
    if filename.endswith(".gz"):
        with open(filename, mode) as fp:
            with gzip.GzipFile(fileobj=fp, mode='wb') as gzfp:
                for x in data:
                    gzfp.write((json.dumps(x) + "\n").encode('utf-8'))
    else:
        with open(filename, mode) as fp:
            for x in data:
                fp.write((json.dumps(x) + "\n").encode('utf-8'))

def group_and_count(lst, group_key, count_key):

    grouped_counts = defaultdict(int)
    
    for item in lst:
        group = item.get(group_key)
        if group not in grouped_counts:
            grouped_counts[group] = 0
        if item.get(count_key) == True:
            grouped_counts[group] += 1
    
    return list(grouped_counts.values())

def estimate_pass_at_k(
    num_samples: Union[int, List[int], np.ndarray],
    num_correct: Union[List[int], np.ndarray],
    k: int
) -> np.ndarray:
    """
    Estimates pass@k of each problem and returns them in an array.
    """

    def estimator(n: int, c: int, k: int) -> float:
        """
        Calculates 1 - comb(n - c, k) / comb(n, k).
        """
        if n - c < k:
            return 1.0
        return 1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))

    if isinstance(num_samples, int):
        num_samples_it = itertools.repeat(num_samples, len(num_correct))
    else:
        assert len(num_samples) == len(num_correct)
        num_samples_it = iter(num_samples)

    return np.array([estimator(int(n), int(c), k) for n, c in zip(num_samples_it, num_correct)])


def read_metafile(path):
    import yaml
    if os.path.isdir(path):
        path = os.path.join(path, 'metafile.yml')
    if not os.path.exists(path):
        raise FileExistsError("metafile.yml is not found.")
    with open(path, 'r') as fp:
        info = yaml.load(fp, Loader=yaml.FullLoader)
    return info


