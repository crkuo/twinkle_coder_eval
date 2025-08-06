# 🌟 Twinkle Code Evaluator

A comprehensive, modular framework for evaluating Large Language Models (LLMs) on code generation benchmarks.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.8%2B-green.svg)](https://python.org)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black.svg)](https://github.com/psf/black)

## ✨ Features

- 🚀 **Multiple Backends**: OpenAI API, vLLM, and extensible backend system
- 📊 **Rich Benchmarks**: MBPP, HumanEval, BigCodeBench, LeetCode, and more
- ⚙️ **Configuration-Driven**: YAML-based experiment configuration
- 🔄 **Dynamic Loading**: Automatic component discovery and registration
- 📈 **Comprehensive Metrics**: Pass@k evaluation with detailed analysis
- 🛡️ **Safe Execution**: Sandboxed code execution environment
- 📁 **Smart Results**: Parameter-based directory generation prevents overwrites

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/twinkle_code_eval.git
cd twinkle_code_eval/refactor

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

1. **Configure your evaluation**:
   ```bash
   # Copy and edit a configuration file
   cp configs/test_mbpp_config.yml my_config.yml
   # Edit my_config.yml to set your API keys and preferences
   ```

2. **Run evaluation**:
   ```bash
   python tools/run_evaluation.py my_config.yml
   ```

3. **Check results**:
   ```bash
   # Results are saved to result/{model_name}/{benchmark_type}_{config_signature}/
   ls result/
   ```

## 📊 Supported Benchmarks

| Benchmark | Description | Tasks | Language |
|-----------|-------------|-------|----------|
| **MBPP** | Mostly Basic Python Problems | 374 | Python |
| **HumanEval** | Function completion tasks | 164 | Python |
| **BigCodeBench** | Complex multi-file projects | 1140+ | Python |
| **LeetCode** | Algorithm and data structures | 300+ | Python |
| **MBPPPlus** | Enhanced version of MBPP | 378+ | Python |
| **TestMBPP** | Lightweight testing subset | 4 | Python |

## 🔌 Supported Backends

| Backend | Description | Use Case |
|---------|-------------|----------|
| **OpenAI** | Official OpenAI API | GPT-3.5, GPT-4, and compatible APIs |
| **vLLM** | High-performance inference | Local models, high-throughput evaluation |
| **Mock** | Testing backend | Development, CI/CD pipelines |

## 📖 Configuration Examples

### Single Benchmark Evaluation

```yaml
# configs/single_eval.yml
name: "GPT-4 MBPP Evaluation"

model:
  backend:
    - type: openai
      server_params:
        api_key: YOUR_API_KEY_HERE
        base_url: https://api.openai.com/v1
      model_name: "gpt-4"

evaluation:
  benchmark:
    - type: MBPP
      prompt_type: "Chat"
      params:
        num_samples: 10
        temperature: 0.0
        max_tokens: 1024
```

### Multi-Benchmark Evaluation

```yaml
# configs/comprehensive_eval.yml
name: "Comprehensive Code Evaluation"

model:
  backend:
    - type: openai
      server_params:
        api_key: YOUR_API_KEY_HERE
      model_name: "gpt-4"

evaluation:
  benchmark:
    - type: MBPP
      params:
        num_samples: 20
        temperature: 0.0
        
    - type: HumanEval
      params:
        num_samples: 20
        temperature: 0.0
        
    - type: BigCodeBench
      params:
        num_samples: 5
        temperature: 0.2
```

### Local Model with vLLM

```yaml
# configs/local_model.yml
name: "Local Model Evaluation"

model:
  backend:
    - type: vllm
      server_params:
        dtype: "bfloat16"
        num_gpus: 1
        trust_remote_code: true
      model_name: "deepseek-ai/deepseek-coder-6.7b-instruct"

evaluation:
  benchmark:
    - type: MBPP
      prompt_type: "Instruction"
      params:
        num_samples: 10
        batch_size: 4
```

## 🛠️ Advanced Usage

### Adding Custom Benchmarks

1. **Create benchmark class**:
   ```python
   from benchmark.base import Benchmark
   from engine.registry import register_benchmark
   
   @register_benchmark('MyBenchmark')
   class MyBenchmark(Benchmark):
       def get_prompt(self):
           # Return list of prompt dictionaries
           pass
           
       def postprocess_generation(self, generation):
           # Clean and format generated code
           pass
           
       def process_results(self, solution):
           # Evaluate solution correctness
           pass
   ```

2. **Create metafile.yml**:
   ```yaml
   # benchmark/MyBenchmark/metafile.yml
   Name: MyBenchmark
   Paper: https://arxiv.org/abs/example
   Repository: https://github.com/example/benchmark
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

### Example Results
```json
{
  "benchmark": "MBPP",
  "score": 0.847,
  "num_samples": 10,
  "total_prompts": 374,
  "pass_at_1": 0.723,
  "pass_at_5": 0.847,
  "pass_at_10": 0.892
}
```

## 🔧 Development

### Project Structure
```
refactor/
├── backend/           # Model inference backends
├── benchmark/         # Evaluation benchmarks  
├── engine/           # Core framework (registry, config)
├── eval/             # Code execution and evaluation
├── tools/            # CLI tools and utilities
├── configs/          # Configuration templates
└── tests/            # Test suite
```

### Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and add tests
4. **Run tests**: `python -m pytest tests/`
5. **Submit a pull request**

### Code Style
- Follow PEP 8 guidelines
- Use type hints where possible
- Add docstrings for public methods
- Format with Black: `black .`

## 🤝 Community

- **Issues**: [GitHub Issues](https://github.com/your-org/twinkle_code_eval/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/twinkle_code_eval/discussions)
- **Documentation**: [Wiki](https://github.com/your-org/twinkle_code_eval/wiki)

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