"""
调度配置测试
"""

import pytest
from src.config.loader import ConfigLoader


class TestPipelineScheduleConfig:
    """Pipeline 调度配置测试"""
    
    def test_get_pipeline_schedule_default(self):
        """测试默认 Pipeline 调度时间"""
        loader = ConfigLoader()
        config = {}
        
        times = loader.get_pipeline_schedule(config)
        
        assert times == ["08:00", "14:00", "19:00"]
    
    def test_get_pipeline_schedule_from_config(self):
        """测试从配置读取 Pipeline 调度时间"""
        loader = ConfigLoader()
        config = {
            'pipeline': {
                'schedule': {
                    'times': ["09:00", "15:00", "21:00"]
                }
            }
        }
        
        times = loader.get_pipeline_schedule(config)
        
        assert times == ["09:00", "15:00", "21:00"]
    
    def test_get_pipeline_schedule_partial_config(self):
        """测试部分配置"""
        loader = ConfigLoader()
        config = {
            'pipeline': {}
        }
        
        times = loader.get_pipeline_schedule(config)
        
        assert times == ["08:00", "14:00", "19:00"]


class TestDataSyncScheduleConfig:
    """数据同步调度配置测试"""
    
    def test_get_data_sync_config_default(self):
        """测试默认数据同步配置"""
        loader = ConfigLoader()
        config = {}
        
        sync_config = loader.get_data_sync_config(config)
        
        assert sync_config['enabled'] == True
        assert sync_config['schedule']['day'] == 'monday'
        assert sync_config['schedule']['time'] == '07:00'
    
    def test_get_data_sync_config_from_yaml(self):
        """测试从 YAML 配置读取"""
        loader = ConfigLoader()
        config = {
            'data_sync': {
                'enabled': False,
                'schedule': {
                    'day': 'tuesday',
                    'time': '10:00'
                }
            }
        }
        
        sync_config = loader.get_data_sync_config(config)
        
        assert sync_config['enabled'] == False
        assert sync_config['schedule']['day'] == 'tuesday'
        assert sync_config['schedule']['time'] == '10:00'