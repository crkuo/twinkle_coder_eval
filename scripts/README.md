# Scripts Directory

This directory contains testing and utility scripts for the twinkle_coder_evaluator framework.

## Testing Scripts

### `test_basic.py`
Basic system tests that verify core functionality:
- Configuration parsing
- Component initialization
- Factory pattern operations
- Basic utility functions

### `test_complete_workflow.py`
Comprehensive workflow tests including:
- End-to-end evaluation pipeline
- Configuration-driven evaluation
- Multi-component integration
- Result processing and validation

### `test_openai_simple.py`
OpenAI backend testing:
- API connection testing
- Simple message generation
- Error handling verification
- Integration with framework

## Usage

Run individual tests:
```bash
python scripts/test_basic.py
python scripts/test_complete_workflow.py
python scripts/test_openai_simple.py
```

Make sure to activate the virtual environment before running tests:
```bash
source ../.venv/bin/activate
```