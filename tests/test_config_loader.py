"""
配置加载器测试

测试 ConfigLoader 的各项功能。
"""

import pytest
import os
import tempfile
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from config.loader import ConfigLoader


class TestConfigLoader:
    """ConfigLoader 测试类"""
    
    def test_load_config_file(self):
        """测试从 YAML 文件加载配置"""
        config_content = """
github:
  repo: "vllm-project/vllm-ascend"
  api_base: "https://api.github.com"

filters:
  triaged_label: "triaged"
  resolution_labels:
    - "invalid"
    - "wontfix"
    - "duplicated"
    - "wait-feedback"
    - "resolved"
  overdue_days: 7

excel:
  url: "https://docs.google.com/spreadsheets/d/abc123/edit"
  gid: "gid123"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()
            config_path = f.name
        
        loader = ConfigLoader()
        config = loader.load(config_path)
        
        os.unlink(config_path)
        
        assert config['github']['repo'] == "vllm-project/vllm-ascend"
        assert config['filters']['triaged_label'] == "triaged"
        assert len(config['filters']['resolution_labels']) == 5
        assert config['filters']['overdue_days'] == 7
        assert config['excel']['url'] == "https://docs.google.com/spreadsheets/d/abc123/edit"
    
    def test_get_repo_url(self):
        """测试生成仓库 API URL"""
        config = {
            'github': {
                'repo': 'vllm-project/vllm-ascend',
                'api_base': 'https://api.github.com'
            }
        }
        loader = ConfigLoader()
        url = loader.get_issues_url(config)
        assert url == "https://api.github.com/repos/vllm-project/vllm-ascend/issues"
    
    def test_use_defaults_when_missing_fields(self):
        """测试缺失配置项时使用默认值"""
        config_content = """
github:
  repo: "owner/repo"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            f.flush()
            config_path = f.name
        
        loader = ConfigLoader()
        config = loader.load(config_path)
        
        os.unlink(config_path)
        
        assert 'resolution_labels' in config['filters']
        assert 'invalid' in config['filters']['resolution_labels']
        assert config['filters']['overdue_days'] == 7
    
    def test_missing_config_file_raises_error(self):
        """测试配置文件不存在时抛出异常"""
        loader = ConfigLoader()
        with pytest.raises(FileNotFoundError):
            loader.load("/nonexistent/config.yaml")
    
    def test_get_excel_url(self):
        """测试获取 Excel URL"""
        config = {
            'excel': {
                'url': 'https://docs.google.com/spreadsheets/d/abc123/edit',
                'gid': 'gid123'
            }
        }
        loader = ConfigLoader()
        url = loader.get_excel_url(config)
        assert url == 'https://docs.google.com/spreadsheets/d/abc123/edit'
    
    def test_get_excel_gid(self):
        """测试获取 Excel GID"""
        config = {
            'excel': {
                'url': 'https://docs.google.com/spreadsheets/d/abc123/edit',
                'gid': 'gid123'
            }
        }
        loader = ConfigLoader()
        gid = loader.get_excel_gid(config)
        assert gid == 'gid123'
    
    def test_get_excel_gid_default(self):
        """测试获取默认 GID"""
        config = {
            'excel': {
                'url': 'https://docs.google.com/spreadsheets/d/abc123/edit'
            }
        }
        loader = ConfigLoader()
        gid = loader.get_excel_gid(config)
        assert gid == '0'