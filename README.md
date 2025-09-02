# 🌟 Twinkle Code Evaluator

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.8%2B-green.svg)](https://python.org)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black.svg)](https://github.com/psf/black)

**Twinkle Code Evaluator** is a production-ready, extensible framework designed for systematic evaluation of Large Language Models (LLMs) on code generation tasks. It provides a unified interface for running multiple benchmarks across different model backends, with support for both API-based models (OpenAI, Claude) and locally-hosted models (vLLM, Hugging Face).


## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/twinkle_code_eval.git
cd twinkle_code_eval

# Install basic dependencies
pip install -r requirements.txt

# For BigCodeBench evaluation, install additional dependencies
pip install -r requirements-BigCodeBench.txt
```

### Environment Setup

1. **Create environment file**:
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env and set your API keys
   nano .env
   ```


### Basic Usage

1. **Configure your evaluation ([Configuration Guide](docs/configuration_guide.md))**:
   ```bash
   # Copy and edit a configuration file
   cp configs/test_mbpp_config.yml my_config.yml
   # Edit my_config.yml to set your API keys and preferences
   ```

2. **Run evaluation**:
   ```bash
   # YAML configuration (recommended)
   python evaluate.py my_config.yml
   ```

3. **Check results**:
   ```bash
   # Results are saved to result/{model_name}/{benchmark_type}_{config_signature}/
   ls result/
   ```

## 📖 Documentation

- **[Configuration Guide](docs/configuration_guide.md)** - Comprehensive YAML configuration documentation with examples
- **[Design Documentation](docs/design_docs/)** - Framework architecture and design decisions

### Backend API References

For detailed parameter configuration, refer to the official API documentation:

- **vLLM Backend**: [vLLM.LLM API Reference](https://docs.vllm.ai/en/latest/api/vllm/index.html#vllm.LLM) a - Parameters for the `arguments` field
- **OpenAI Backend**: [OpenAI API Reference](https://platform.openai.com/docs/api-reference/introduction) - Client initialization parameters

## 📊 Supported Benchmarks

| Benchmark | Description | Tasks | Language | Source |
|-----------|-------------|-------|----------|---------|
| **MBPP** | Mostly Basic Python Problems | 374 | Python | [Google Research](https://github.com/google-research/google-research/tree/master/mbpp) |
| **MBPPPlus** | Enhanced version of MBPP with more tests | 399 | Python | [MBPP Plus](https://github.com/google-research/google-research/tree/master/mbpp) |
| **MBPPToy** | Lightweight testing subset (tasks 10-19) | 10 | Python | MBPP subset |
| **HumanEval** | Function completion tasks | 164 | Python | [OpenAI HumanEval](https://github.com/openai/human-eval) |
| **HumanEvalPlus** | HumanEval with additional test cases | 164 | Python | [EvalPlus](https://github.com/evalplus/evalplus) |
| **BigCodeBench** | Complex multi-file projects | 1140+ | Python | [BigCode](https://huggingface.co/datasets/bigcode/bigcodebench) ⚠️ |
| **BigCodeBenchHard** | Challenging subset of BigCodeBench | 473+ | Python | [BigCode Hard](https://huggingface.co/datasets/bigcode/bigcodebench-hard) ⚠️ |
| **LeetCode** | Algorithm and data structure problems | 300+ | Python | LeetCode problems |

> ⚠️ **BigCodeBench Requirements**: For BigCodeBench and BigCodeBenchHard, additional dependencies are required:
> ```bash
> pip install -r requirements-BigCodeBench.txt
> ```
> These benchmarks use complex libraries including TensorFlow, Django, OpenCV, and others.

## 🔌 Supported Backends

| Backend | Description | Use Case | Features |
|---------|-------------|----------|----------|
| **OpenAI** | Official OpenAI API | GPT-3.5, GPT-4, and compatible APIs | • Chat/Completion modes<br/>• Stream auto-continuation<br/>• Environment variable config<br/>• Direct client parameter passing |
| **vLLM** | High-performance inference engine | Local models, high-throughput evaluation | • GPU acceleration<br/>• Batch processing<br/>• Memory optimization<br/>• Direct LLM parameter passing |

## 📖 Configuration Examples

### Single Benchmark Evaluation

```yaml
# configs/single_eval.yml
name: "GPT-4 MBPP Evaluation"

backend:
  - type: openai
    arguments:
      # API credentials loaded from .env file
      # Set OPENAI_API_KEY in your .env file
    model_name: "gpt-4"

evaluation:
  benchmark:
    - type: MBPP
      prompt_type: "Chat"
      num_samples: 10
      generate_args:
        temperature: 0.0
        max_tokens: 1024
```
> 💡 **Tip**: The `generate_args` field maps directly to the constructor parameters in these APIs. Any parameter documented in the official APIs can be used in the `generate_args` section.

For detailed parameter configuration, refer to the official API documentation:

- OpenAI: [Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)
- vLLM: [vLLM.LLM.generate](https://docs.vllm.ai/en/v0.9.2/api/vllm/index.html#vllm.LLM.generate)

### Multi-Benchmark Evaluation

```yaml
# configs/comprehensive_eval.yml
name: "Comprehensive Code Evaluation"

backend:
  - type: openai
    arguments:
      # API key from .env file
    model_name: "gpt-4"

evaluation:
  benchmark:
    - type: MBPP
      num_samples: 20
      generate_args:
        temperature: 0.0
        
    - type: HumanEval
      num_samples: 20
      generate_args:
        temperature: 0.0
        
    - type: BigCodeBench
      num_samples: 5
      generate_args:
        temperature: 0.2

# Note: BigCodeBench requires additional dependencies
# pip install -r requirements-BigCodeBench.txt
```

### Local Model with vLLM

```yaml
# configs/local_model.yml
name: "Local Model Evaluation"

backend:
  - type: vllm
    arguments:
      # Direct vLLM LLM() constructor parameters
      dtype: "bfloat16"
      tensor_parallel_size: 1
      trust_remote_code: true
      max_model_len: 2048
    model_name: "deepseek-ai/deepseek-coder-6.7b-instruct"

evaluation:
  benchmark:
    - type: MBPP
      prompt_type: "Instruction"
      num_samples: 10
      generate_args:
        batch_size: 4
```

## 🔧 Backend Configuration Details

### Understanding the `arguments` Parameter

The `arguments` parameter in backend configuration serves different purposes for each backend type:

#### OpenAI Backend
The `arguments` parameter contains **OpenAI client initialization parameters** that are passed directly to the `OpenAI()` constructor:

```yaml
backend:
  - type: openai
    arguments:
      api_key: "your-api-key"        # Direct to OpenAI(api_key=...)
      base_url: "custom-endpoint"    # Direct to OpenAI(base_url=...)
      timeout: 30                    # Direct to OpenAI(timeout=...)
      max_retries: 3                 # Direct to OpenAI(max_retries=...)
    model_name: "gpt-4"
```

**Environment Variable Fallback**: If `api_key` or `base_url` are not provided in `arguments`, they will be automatically loaded from environment variables (`OPENAI_API_KEY`, `OPENAI_BASE_URL`).

#### vLLM Backend
The `arguments` parameter contains **vLLM LLM constructor parameters** that are passed directly to the `LLM()` constructor:

```yaml
backend:
  - type: vllm
    arguments:
      dtype: "bfloat16"              # Direct to LLM(dtype=...)
      tensor_parallel_size: 2        # Direct to LLM(tensor_parallel_size=...)
      max_model_len: 4096           # Direct to LLM(max_model_len=...)
      trust_remote_code: true        # Direct to LLM(trust_remote_code=...)
      gpu_memory_utilization: 0.9    # Direct to LLM(gpu_memory_utilization=...)
    model_name: "your-model-path"
```

**Backward Compatibility**: Direct parameters in the constructor (like `dtype: "bfloat16"` at the same level as `arguments`) are still supported but will be overridden by values in `arguments` if both are present.

### Parameter Priority and Merging

For both backends, the parameter resolution follows this priority:

1. **Highest Priority**: Values in `arguments` 
2. **Medium Priority**: Environment variables (OpenAI only)
3. **Lowest Priority**: Direct constructor parameters (backward compatibility)

## 🛠️ Advanced Usage

### Adding Custom Benchmarks

1. **Create benchmark class**:
   ```python
   from benchmark.base import Benchmark
   from engine.registry import register_benchmark
   
   @register_benchmark('MyBenchmark')
   class MyBenchmark(Benchmark):
       def get_prompts(self):
           # Return list of prompt dictionaries
           pass
           
       def postprocess_generation(self, generation):
           # Clean and format generated code
           pass
           
       def process_results(self, solution):
           # Evaluate solution correctness
           pass
   ```

### Adding Custom Backends

1. **Implement backend class**:
   ```python
   from backend.base import Generator
   from engine.registry import register_backend
   
   @register_backend('mybackend')
   class MyBackend(Generator):
       def generate(self, prompt_set, num_samples=1, **kwargs):
           # Implement model inference logic
           return generations
   ```

## 📈 Results Analysis

### Directory Structure
```
result/
├── {model_name}/
│   ├── {benchmark}_{config_signature}/
│   │   ├── prompts.jsonl          # Input prompts
│   │   ├── generations.jsonl      # Raw model outputs
│   │   ├── solutions.jsonl        # Processed solutions
│   │   ├── evaluation.jsonl       # Execution results
│   │   └── result.json           # Final metrics
```

### Metrics

- **Pass@k**: Probability that at least one of k generated solutions is correct
- **Execution Rate**: Percentage of solutions that execute without syntax errors
- **Test Coverage**: Percentage of test cases passed


## 🔧 Development

### Project Structure
```
├── backend/           # Model inference backends
├── benchmark/         # Evaluation benchmarks  
├── engine/           # Core framework (registry, config)
├── eval/             # Code execution and evaluation
├── tools/            # Utilities and helper scripts
├── configs/          # Configuration templates
├── evaluate.py       # Main evaluation script
└── tests/            # Test suite
```



## 🤝 Community

- **Issues**: [GitHub Issues](../../issues)

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for providing accessible LLM APIs
- **vLLM Team** for high-performance inference engine
- **Benchmark Authors** for creating evaluation datasets:
  - MBPP: Austin et al.
  - HumanEval: Chen et al.
  - BigCodeBench: Zhuo et al.

## 📊 Citation

If you use this framework in your research, please cite:

```bibtex
@software{twinkle_code_evaluator,
  title={Twinkle Code Evaluator: A Modular Framework for LLM Code Generation Evaluation},
  author={Your Name},
  year={2024},
  url={https://github.com/your-org/twinkle_code_eval}
}
```

---

**Made with ❤️ by the Twinkle Team**