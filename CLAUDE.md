# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Repository Overview

**Twinkle Code Evaluator** is a comprehensive, modular framework for evaluating Large Language Models (LLMs) on code generation benchmarks. It provides a unified interface for running multiple code evaluation benchmarks across different model backends.

## Architecture Design

### 🏗️ Core Architecture Principles

The framework follows a **Plugin-based Architecture** with three main components:

1. **Backend Layer** - Model inference interfaces
2. **Benchmark Layer** - Evaluation task definitions  
3. **Engine Layer** - Core coordination and configuration management

```
┌─────────────────────────────────────────────────────────┐
│                    Engine Layer                         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Registry    │  │ Config       │  │ Evaluation     │  │
│  │ System      │  │ Management   │  │ Orchestrator   │  │
│  └─────────────┘  └──────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────┘
           │                                    │
┌─────────────────────┐                ┌──────────────────┐
│   Backend Layer     │                │  Benchmark Layer │
│  ┌─────────────────┐│                │ ┌──────────────┐ │
│  │ OpenAI Backend  ││                │ │ MBPP         │ │
│  │ vLLM Backend    ││                │ │ HumanEval    │ │
│  │                 ││                │ │ BigCodeBench │ │
│  └─────────────────┘│                │ │ LeetCode     │ │
└─────────────────────┘                │ │ MBPPPlus     │ │
                                       │ └──────────────┘ │
                                       └──────────────────┘
```

### 🚀 Key Design Patterns

#### 1. Registry Pattern with Dynamic Loading
```python
# Automatic registration with decorators
@register_backend('openai')
class OpenaiGenerator(Generator):
    pass

# Dynamic loading with fallback
backend_cls = BACKENDS.get_module("NewBackend", "backend.{name}.{name}")
```

#### 2. Configuration-Driven Development
```yaml
# Unified YAML configuration format
model:
  backend:
    - type: openai
      server_params:
        api_key: YOUR_API_KEY_HERE
      model_name: "gpt-4"

evaluation:
  benchmark:
    - type: MBPP
      prompt_type: "Chat"
      params:
        num_samples: 10
        temperature: 0.0
```

#### 3. Parameter-based Directory Generation
- Automatically generates unique result directories based on configuration parameters
- Prevents result overwrites when running multiple experiments
- Format: `result/{model_name}/{benchmark_type}_{config_signature}/`

## Directory Structure

```
refactor/
├── backend/              # Model inference backends
│   ├── base.py          # Abstract base class
│   ├── openai/          # OpenAI API backend
│   └── vllm/            # vLLM high-performance backend
├── benchmark/           # Evaluation benchmarks
│   ├── base.py         # Abstract benchmark class
│   ├── MBPP/           # Mostly Basic Python Problems
│   ├── HumanEval/      # Classic code evaluation
│   ├── BigCodeBench/   # Complex coding tasks
│   ├── LeetCode/       # Algorithm problems
│   ├── MBPPPlus/       # Enhanced MBPP
│   └── MBPPToy/        # Lightweight testing benchmark
├── engine/             # Core framework
│   ├── registry.py     # Component registration system
│   ├── config.py       # YAML configuration management
│   └── __init__.py     # Module initialization
├── eval/               # Execution and evaluation
│   └── execution.py    # Safe code execution
├── tools/              # Utilities and runners
│   ├── env_utils.py      # Environment variable utilities
│   ├── utils.py          # General utility functions  
│   └── DEPRECATED_run_evaluation.md # Migration guide
├── configs/            # Configuration templates
├── utils.py           # Helper functions
├── sanitize.py        # Code sanitization
└── requirements.txt   # Dependencies
```

## Core Components

### 🎯 Backend System
- **Purpose**: Unified interface for different LLM inference engines
- **Implementations**: OpenAI API, vLLM
- **Key Features**:
  - Automatic batch processing
  - Error handling and retries
  - Chat and completion modes
  - Parameter validation

### 📊 Benchmark System
- **Purpose**: Standardized evaluation tasks for code generation
- **Available Benchmarks**:
  - **MBPP**: Basic Python programming problems
  - **HumanEval**: Function completion tasks
  - **BigCodeBench**: Complex multi-file projects
  - **LeetCode**: Algorithm and data structure problems
  - **MBPPPlus**: Enhanced version of MBPP
  - **MBPPToy**: Lightweight testing subset

### ⚙️ Engine System
- **Registry**: Dynamic component loading and management
- **Config**: YAML-based configuration with inheritance
- **Orchestration**: Multi-benchmark, multi-backend coordination

## Key Features

### 🔄 Dynamic Component Loading
```python
# Load new benchmarks at runtime
leetcode_benchmark = BENCHMARKS.get_module("LeetCode", "benchmark.{name}.{name}")

# Auto-discovery of components
new_backend = BACKENDS.get("CustomBackend")
```

### 📁 Intelligent Result Management
- Configuration-based directory naming prevents overwrites
- Structured output: prompts → generations → solutions → evaluations
- JSON/JSONL format for easy analysis
- Automatic pass@k metric calculation

### 🛡️ Safe Code Execution
- Sandboxed execution environment
- Timeout protection
- Resource limits
- Error capture and reporting

### 📈 Comprehensive Metrics
- Pass@k evaluation (k=1,5,10,...)
- Execution success rates
- Syntax error analysis
- Performance benchmarking

## Usage Patterns

### Basic Single Benchmark
```bash
python evaluate.py configs/test_mbpp_config.yml
```

### Multi-Benchmark Evaluation
```yaml
# configs/multi_benchmark.yml
evaluation:
  benchmark:
    - type: MBPP
      params: {num_samples: 10}
    - type: HumanEval  
      params: {num_samples: 5}
```

### Custom Backend Configuration
```yaml
model:
  backend:
    - type: openai
      server_params:
        api_key: YOUR_KEY
        base_url: https://api.custom-llm.com
      model_name: "custom-model-v1"
```

## Extension Points

### Adding New Benchmarks
1. Inherit from `benchmark.base.Benchmark`
2. Implement required abstract methods
3. Add `@register_benchmark('YourBenchmark')` decorator
4. Create metafile.yml with metadata

### Adding New Backends
1. Inherit from `backend.base.Generator`
2. Implement `generate()` method
3. Add `@register_backend('YourBackend')` decorator
4. Handle initialization and cleanup

### Custom Metrics
1. Extend evaluation functions in benchmark classes
2. Add metric calculation in `process_results()`
3. Update result aggregation logic

## Best Practices

### Configuration Management
- Use base configurations with inheritance
- Store sensitive data in environment variables
- Validate configurations before execution
- Document parameter effects

### Performance Optimization
- Use appropriate batch sizes for your hardware
- Enable caching for repeated experiments
- Monitor memory usage with large models
- Utilize parallel processing for evaluation

### Result Analysis
- Always save intermediate results (generations, solutions)
- Use configuration signatures for experiment tracking
- Implement proper logging and monitoring
- Archive results with metadata

## Development Workflow

1. **Setup Environment**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Tests**:
   ```bash
   python evaluate.py configs/test_mbpp_config.yml
   ```

3. **Add Components**: Follow extension patterns above

4. **Validate**: Test with simple configurations before complex models

5. **Document**: Update configuration examples and documentation

## Integration Notes

This framework is designed for:
- **Research**: Academic evaluation and benchmarking
- **Industry**: Model validation and comparison
- **Development**: Rapid prototyping and testing
- **CI/CD**: Automated model evaluation pipelines

The modular design allows for easy integration with existing ML workflows, experiment tracking systems, and deployment pipelines.