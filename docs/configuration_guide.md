# Configuration Guide

This document provides detailed information about YAML configuration files for the Twinkle Code Evaluator framework.

## 📁 Configuration File Structure

Configuration files use YAML format and define the complete evaluation setup including backends, benchmarks, and output settings.

### Example: `configs/test_mbpp_config.yml`

```yaml
name: "Test MBPP Evaluation"

backend:
  - type: openai
    arguments:
      # API credentials will be loaded from .env file or environment variables
      # Set OPENAI_API_KEY and OPENAI_BASE_URL in your .env file
    model_name: "Qwen3-30B-A3B"

evaluation:
  benchmark:
    - type: MBPPToy
      prompt_type: "Instruct"
      num_workers: 1
      num_samples: 1
      batch_size: 1
      log_batch_size: 1
      generate_args:
        temperature: 0.0
        max_tokens: 2048
      pass_at_k: 1

  output:
    keep_chat: false
    result_folder: "result/"
```

## 🔧 Configuration Sections

### 1. Experiment Metadata

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | No | None | Human-readable experiment name for identification |

**Example:**
```yaml
name: "GPT-4 MBPP Comprehensive Evaluation"
```

### 2. Backend Configuration

The `backend` section defines which model inference engine to use.

#### 2.1 Backend Structure

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | Yes | None | Backend type (`openai`, `vllm`, `custom`) |
| `model_name` | string | Yes | None | Model identifier/name |
| `arguments` | object | No | `{}` | Backend-specific arguments and server parameters |

#### 2.2 OpenAI Backend

```yaml
backend:
  - type: openai
    model_name: "gpt-4"
    arguments:
      # OpenAI client constructor parameters
      # API credentials loaded from .env automatically
      # api_key: "sk-your-key"      # Override .env if needed
      # base_url: "https://api.openai.com"  # Override .env if needed
      timeout: 30                   # Request timeout in seconds
      max_retries: 3               # Maximum retry attempts
```

**OpenAI Backend `arguments` Parameters:**

The `arguments` section contains parameters passed directly to the `OpenAI()` client constructor:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `api_key` | from .env | OpenAI API key (overrides `OPENAI_API_KEY` environment variable) |
| `base_url` | from .env | API endpoint URL (overrides `OPENAI_BASE_URL` environment variable) |
| `timeout` | 60 | Request timeout in seconds |
| `max_retries` | 2 | Maximum number of retry attempts |
| `organization` | None | OpenAI organization ID |
| `project` | None | OpenAI project ID |

For more details, see [OpenAI API Reference](https://platform.openai.com/docs/api-reference/introduction).

```yaml
backend:
  - type: openai
    model_name: "gpt-4"
    arguments:
      timeout: 30
```

#### 2.3 vLLM Backend

```yaml
backend:
  - type: vllm
    model_name: "deepseek-ai/deepseek-coder-6.7b-instruct"
    arguments:
      # vLLM LLM constructor parameters
      dtype: "bfloat16"
      tensor_parallel_size: 1
      trust_remote_code: true
      max_model_len: 4096
      gpu_memory_utilization: 0.9
```

**vLLM Backend `arguments` Parameters:**

The `arguments` section contains parameters passed directly to the `LLM()` constructor:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `dtype` | `"auto"` | Model precision (`"bfloat16"`, `"float16"`, `"float32"`, `"auto"`) |
| `tensor_parallel_size` | `1` | Number of GPUs for tensor parallelism |
| `trust_remote_code` | `false` | Allow execution of custom model code |
| `max_model_len` | model default | Maximum sequence length |
| `gpu_memory_utilization` | `0.9` | GPU memory utilization ratio |
| `swap_space` | `4` | CPU swap space in GB |
| `cpu_offload_gb` | `0` | CPU offload memory in GB |
| `quantization` | None | Quantization method (`"awq"`, `"gptq"`, etc.) |

For more details, see [vLLM.LLM API Reference](https://docs.vllm.ai/en/latest/api/vllm/index.html#vllm.LLM)
```yaml
backend:
  - type: vllm
    model_name: "model-name"
    batch_size: 4                # Framework parameter
    temperature: 0.0             # Framework parameter
    max_tokens: 2048            # Framework parameter
    arguments:
      dtype: "bfloat16"          # vLLM LLM() parameter
      tensor_parallel_size: 2    # vLLM LLM() parameter
```

#### 2.4 Official API References

For complete parameter documentation, refer to the official API references:

- **vLLM Backend**: [vLLM.LLM API Reference](https://docs.vllm.ai/en/latest/api/vllm/index.html#vllm.LLM)
- **OpenAI Backend**: [OpenAI API Reference](https://platform.openai.com/docs/api-reference/introduction) 

> 💡 **Tip**: The `arguments` field maps directly to the constructor parameters in these APIs. Any parameter documented in the official APIs can be used in the `arguments` section.

### 3. Parameter Priority and Backward Compatibility

#### 3.1 OpenAI Backend Priority

1. **Highest Priority**: Parameters in `arguments`
2. **Medium Priority**: Environment variables (`.env` file)
3. **Lowest Priority**: Default values

```yaml
# Example: api_key resolution
backend:
  - type: openai
    arguments:
      api_key: "config-key"  # Used (highest priority)
# Even if OPENAI_API_KEY="env-key" in .env, "config-key" will be used
```

#### 3.2 vLLM Backend Priority

1. **Highest Priority**: Parameters in `arguments`
2. **Medium Priority**: Direct constructor parameters (backward compatibility)
3. **Lowest Priority**: Default values

```yaml
# Example: dtype resolution
backend:
  - type: vllm
    dtype: "float16"          # Ignored (backward compatibility)
    arguments:
      dtype: "bfloat16"       # Used (highest priority)
```

### 4. Evaluation Configuration

The `evaluation` section defines benchmarks and their parameters.

#### 3.1 Benchmark Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Benchmark name (`MBPP`, `HumanEval`, `BigCodeBench`, etc.) |
| `prompt_type` | string | No | Prompt format (`"Instruct"`, `"Chat"`, `"Base"`) |
| `num_samples` | integer | No | Number of solutions per problem (default: 1) |
| `num_workers` | integer | No | Parallel processing workers (default: 1) |
| `pass_at_k` | integer | No | Pass@k evaluation metric (default: 1) |
| `generate_args` | object | No | Model generation parameters |

`generate_args` follow the generation arguments that correspond to their backend:
- OpenAI: [Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)
- vLLM: [vLLM.LLM.generate](https://docs.vllm.ai/en/v0.9.2/api/vllm/index.html#vllm.LLM.generate)
 

#### 3.2 Benchmark Types

**MBPP Family:**
```yaml
benchmark:
  - type: MBPP          # Full dataset (374 problems)
  - type: MBPPPlus      # Enhanced version (399 problems)  
  - type: MBPPToy       # Testing subset (10 problems)
```

**HumanEval Family:**
```yaml
benchmark:
  - type: HumanEval     # Original dataset (164 problems)
  - type: HumanEvalPlus # Enhanced with more tests (164 problems)
```

**BigCodeBench Family:**
```yaml
benchmark:
  - type: BigCodeBench     # Full dataset (1140+ problems)
  - type: BigCodeBenchHard # Challenging subset (473+ problems)
```

**Other Benchmarks:**
```yaml
benchmark:
  - type: LeetCode      # Algorithm problems (300+ problems)
```

#### 3.3 Processing Parameters

```yaml
benchmark:
  - type: MBPP
    num_samples: 10        # Generate 10 solutions per problem
    num_workers: 4         # Use 4 parallel workers
    batch_size: 8          # Process 8 prompts at once
    log_batch_size: 100    # Log progress every 100 problems
    timeout: 5.0           # Code execution timeout (seconds)
```

**Processing Parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `num_samples` | `1` | Solutions generated per problem |
| `num_workers` | `1` | Parallel workers for post-processing |
| `batch_size` | - | Batch size for model inference |
| `log_batch_size` | all | Progress logging frequency |
| `timeout` | `3.0` | Code execution timeout |

### 5. Output Configuration

```yaml
output:
  keep_chat: false           # Save chat conversation history
  result_folder: "result/"   # Output directory
```

**Output Parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `keep_chat` | `false` | Preserve conversation context |
| `result_folder` | `"result/"` | Output directory path |

## 📝 Complete Configuration Examples

### Single Benchmark Evaluation

```yaml
name: "GPT-4 MBPP Evaluation"

backend:
  - type: openai
    model_name: "gpt-4"

evaluation:
  benchmark:
    - type: MBPP
      prompt_type: "Chat"
      num_samples: 20
      generate_args:
        temperature: 0.0
        max_tokens: 1024
      pass_at_k: 1

  output:
    result_folder: "results/gpt4_mbpp/"
```

### Multi-Benchmark Evaluation

```yaml
name: "Comprehensive Code Evaluation"

backend:
  - type: openai
    model_name: "gpt-4"

evaluation:
  benchmark:
    - type: MBPP
      num_samples: 10
      generate_args:
        temperature: 0.0
        
    - type: HumanEval
      num_samples: 10
      generate_args:
        temperature: 0.0
        
    - type: BigCodeBench
      num_samples: 5
      generate_args:
        temperature: 0.2
        max_tokens: 2048

  output:
    result_folder: "results/comprehensive/"
```

### High-Performance Configuration

```yaml
name: "High-Throughput Evaluation"

backend:
  - type: vllm
    model_name: "deepseek-ai/deepseek-coder-6.7b-instruct"
    arguments:
      dtype: "bfloat16"
      num_gpus: 2

evaluation:
  benchmark:
    - type: MBPP
      num_samples: 100
      num_workers: 8
      batch_size: 16
      log_batch_size: 50
      generate_args:
        temperature: 0.8
        max_tokens: 1024
        top_p: 0.95
```

## 🔄 Configuration Inheritance

You can use `_base_` for configuration inheritance:

```yaml
# base_config.yml
_base_: "configs/base/openai_base.yml"

name: "Custom Evaluation"

evaluation:
  benchmark:
    - type: MBPP
      num_samples: 50  # Override base value
```

## 🛠️ Best Practices

### 1. Environment Integration
- Use `.env` files for sensitive information
- Let the system auto-fill missing parameters
- Override environment defaults in config when needed

### 2. Performance Tuning
- Start with small `num_samples` for testing
- Adjust `batch_size` based on GPU memory
- Use `num_workers` = number of CPU cores for post-processing
- Set appropriate `timeout` for code execution

### 3. Reproducibility
- Set `temperature: 0.0` for deterministic results
- Use specific model versions
- Document configuration parameters

### 4. Resource Management
- Monitor memory usage with large batch sizes
- Use appropriate `dtype` for vLLM (bfloat16 recommended)
- Adjust timeout based on problem complexity

## ⚠️ Common Issues

### Configuration Validation Errors
```yaml
# ❌ Missing required fields
backend:
  - type: openai  # Missing model_name

# ✅ Correct format
backend:
  - type: openai
    model_name: "gpt-4"
```

### Path Issues
```yaml
# ❌ Problematic paths
result_folder: "../../../results"

# ✅ Safe paths
result_folder: "results/"
result_folder: "/absolute/path/to/results"
```

### Memory Issues
```yaml
# ❌ Too aggressive for limited resources
num_samples: 100
batch_size: 32
num_workers: 16

# ✅ Conservative settings
num_samples: 10
batch_size: 4
num_workers: 2
```