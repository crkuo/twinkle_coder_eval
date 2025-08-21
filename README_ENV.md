# Environment Configuration

This project uses environment variables for secure configuration management. Follow these steps to set up your environment:

## Setup

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file with your actual values:**
   ```bash
   # Example .env content
   DATASET_CACHE_FOLDER=cache
   OPENAI_API_KEY=your_actual_api_key_here
   OPENAI_BASE_URL=https://your-api-url.com/api/
   RESULT_FOLDER=result
   DEBUG=false
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration Options

### Required Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (when using OpenAI backend)
- `OPENAI_BASE_URL`: OpenAI API base URL (optional, defaults to https://api.openai.com)

### Optional Environment Variables

- `DATASET_CACHE_FOLDER`: Directory for storing benchmark datasets (default: `cache`)
- `RESULT_FOLDER`: Directory for storing evaluation results (default: `result`)
- `REQUESTS_ROUND_LIMIT`: Maximum continuation rounds for OpenAI requests when finish_reason='length' (default: `20`)
- `DEBUG`: Enable debug logging (default: `false`)

### Custom Backend Support

For custom OpenAI-compatible backends:
- `CUSTOM_API_KEY`: API key for custom backend
- `CUSTOM_BASE_URL`: Base URL for custom backend

## Usage

The system will automatically load environment variables from `.env` file when running evaluations. You no longer need to hardcode API keys in configuration files.

### Advanced Configuration

#### Request Handling

- `REQUESTS_ROUND_LIMIT`: Controls how many times the OpenAI backend will attempt to continue generation when the response is truncated due to length limits. This is useful for generating longer code solutions that might exceed token limits in a single request.

### Example Config File

```yaml
name: "Test MBPP Evaluation"

backend:
  - type: openai
    arguments:
      # API credentials will be loaded from .env file
    model_name: "gpt-4"

evaluation:
  benchmark:
    - type: MBPP
      prompt_type: "Instruct"
      num_samples: 1
```

## Security

- Never commit `.env` files to version control
- The `.env` file is already included in `.gitignore`
- Use `.env.example` as a template for sharing configuration structure
- Environment variables take precedence over configuration file values

## Migration from env.py

This system replaces the old `env.py` approach with secure environment variable management using `python-dotenv`. All benchmark modules now automatically load configuration from environment variables.