"""
基於 TDD 的 YAML 計劃測試 - 使用模組化配置解析器
"""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from core.config import (
    load_yaml_plan_file,
    extract_plan_name,
    extract_model_config,
    extract_backend_name,
    extract_server_config,
    extract_instance_config,
    extract_benchmark_list,
    extract_output_path,
    extract_keep_chat_setting,
    PlanRunner
)

class TestYAMLPlanLoader:
    """YAML 計劃加載器測試"""
    
    def test_load_yaml_plan_file(self):
        """測試加載 YAML 計劃文件"""
        test_file = Path(__file__).parent / 'test_yaml_plan.yml'
        config = load_yaml_plan_file(str(test_file))
        assert config is not None
        assert 'name' in config
    
    def test_extract_plan_name(self):
        """測試提取計劃名稱"""
        test_file = Path(__file__).parent / 'test_yaml_plan.yml'
        config = load_yaml_plan_file(str(test_file))
        plan_name = extract_plan_name(config)
        assert plan_name == 'openai_test'
    
    def test_extract_model_config(self):
        """測試提取模型配置"""
        test_file = Path(__file__).parent / 'test_yaml_plan.yml'
        config = load_yaml_plan_file(str(test_file))
        model_config = extract_model_config(config)
        assert model_config is not None
        assert isinstance(model_config, dict)
    
    def test_extract_backend_name(self):
        """測試提取後端名稱"""
        test_file = Path(__file__).parent / 'test_yaml_plan.yml'
        config = load_yaml_plan_file(str(test_file))
        backend_name = extract_backend_name(config)
        assert backend_name == 'twinkle_test_grok'
    
    def test_extract_server_config(self):
        """測試提取服務器配置"""
        test_file = Path(__file__).parent / 'test_yaml_plan.yml'
        config = load_yaml_plan_file(str(test_file))
        server_config = extract_server_config(config)
        assert isinstance(server_config, dict)
        assert 'base_url' in server_config
    
    def test_extract_instance_config(self):
        """測試提取實例配置"""
        test_file = Path(__file__).parent / 'test_yaml_plan.yml'
        config = load_yaml_plan_file(str(test_file))
        instance_config = extract_instance_config(config)
        assert isinstance(instance_config, dict)
        assert 'model' in instance_config

class TestBenchmarkConfig:
    """基準測試配置測試"""
    
    def test_extract_benchmark_list(self):
        """測試提取基準測試列表"""
        test_file = Path(__file__).parent / 'test_yaml_plan.yml'
        config = load_yaml_plan_file(str(test_file))
        benchmark_list = extract_benchmark_list(config)
        assert isinstance(benchmark_list, list)
        assert len(benchmark_list) > 0
    

class TestOutputConfig:
    """輸出配置測試"""
    
    def test_extract_output_path(self):
        """測試提取輸出路徑"""
        test_file = Path(__file__).parent / 'test_yaml_plan.yml'
        config = load_yaml_plan_file(str(test_file))
        output_path = extract_output_path(config)
        assert output_path == './report'
    
    def test_extract_keep_chat_setting(self):
        """測試提取保持聊天設置"""
        test_file = Path(__file__).parent / 'test_yaml_plan.yml'
        config = load_yaml_plan_file(str(test_file))
        keep_chat = extract_keep_chat_setting(config)
        assert keep_chat == True

class TestPlanRunner:
    """計劃運行器測試"""
    
    def test_initialize_plan_runner(self):
        """測試初始化計劃運行器"""
        test_file = Path(__file__).parent / 'test_yaml_plan.yml'
        runner = PlanRunner(str(test_file))
        assert runner is not None
        assert runner.config is not None
    
    def test_run_plan_execution(self):
        """測試運行計劃執行"""
        test_file = Path(__file__).parent / 'test_yaml_plan.yml'
        runner = PlanRunner(str(test_file))
        result = runner.run_plan_execution()
        assert result['status'] == 'success'
        assert 'plan_name' in result
    
    def test_validate_plan_config(self):
        """測試驗證計劃配置"""
        test_file = Path(__file__).parent / 'test_yaml_plan.yml'
        runner = PlanRunner(str(test_file))
        is_valid = runner.validate_plan_config()
        assert is_valid == True