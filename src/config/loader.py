"""
配置加载器模块

负责加载 YAML 配置文件并提供配置访问接口。
"""

import yaml
import os
from typing import Dict, Any, List
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    'github': {
        'api_base': 'https://api.github.com',
        'repo': 'vllm-project/vllm-ascend'
    },
    'filters': {
        'triaged_label': 'triaged',
        'resolution_labels': ['invalid', 'wontfix', 'duplicated', 'wait-feedback', 'resolved'],
        'overdue_days': 7,
        'lookback_days': 2
    },
    'excel': {
        'url': None,
        'gid': '0'
    },
    'pipeline': {
        'schedule': {
            'times': ["08:00", "14:00", "19:00"]
        }
    },
    'data_sync': {
        'enabled': True,
        'schedule': {
            'day': 'monday',
            'time': '07:00'
        }
    },
    'assignee_rules': {
        'special_labels': ['gqa-model', '310P']
    }
}


class ConfigLoader:
    """
    配置加载器类
    
    加载 YAML 配置文件，应用默认值，并提供配置访问方法。
    
    Attributes:
        config: 加载后的配置字典
    
    Example:
        loader = ConfigLoader()
        config = loader.load('config.yaml')
        overdue_days = loader.get_overdue_days(config)
    """
    
    def __init__(self):
        """初始化配置加载器"""
        self.config: Dict[str, Any] = None
    
    def load(self, config_path: str) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
        
        Returns:
            加载并应用默认值后的配置字典
        
        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 解析错误
        """
        if not os.path.exists(config_path):
            logger.error(f"Config file not found: {config_path}")
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        logger.info(f"Loading config from: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.config = self._apply_defaults(self.config)
        logger.info("Config loaded successfully")
        
        return self.config
    
    def _apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用默认配置值
        
        对于缺失的配置项，使用默认值填充。
        
        Args:
            config: 原始配置字典
        
        Returns:
            应用默认值后的配置字典
        """
        result = {}
        
        for key, default_value in DEFAULT_CONFIG.items():
            if key not in config:
                result[key] = default_value
                logger.debug(f"Using default value for '{key}'")
            elif isinstance(default_value, dict):
                result[key] = {**default_value, **config[key]}
            else:
                result[key] = config[key]
        
        for key, value in config.items():
            if key not in DEFAULT_CONFIG:
                result[key] = value
        
        return result
    
    def get_issues_url(self, config: Dict[str, Any]) -> str:
        """
        获取 Issues API URL
        
        Args:
            config: 配置字典
        
        Returns:
            Issues API URL
        """
        api_base = config['github']['api_base']
        repo = config['github']['repo']
        url = f"{api_base}/repos/{repo}/issues"
        logger.debug(f"Issues URL: {url}")
        return url
    
    def get_resolution_labels(self, config: Dict[str, Any]) -> List[str]:
        """
        获取已处理标签列表
        
        Args:
            config: 配置字典
        
        Returns:
            已处理标签列表
        """
        labels = config['filters']['resolution_labels']
        logger.debug(f"Resolution labels: {labels}")
        return labels
    
    def get_overdue_days(self, config: Dict[str, Any]) -> int:
        """
        获取超期天数
        
        Args:
            config: 配置字典
        
        Returns:
            超期天数
        """
        days = config['filters']['overdue_days']
        logger.debug(f"Overdue days: {days}")
        return days
    
    def get_triaged_label(self, config: Dict[str, Any]) -> str:
        """
        获取 triaged 标签名称
        
        Args:
            config: 配置字典
        
        Returns:
            triaged 标签名称
        """
        label = config['filters']['triaged_label']
        logger.debug(f"Triaged label: {label}")
        return label
    
    def get_lookback_days(self, config: Dict[str, Any]) -> int:
        """
        获取回溯天数
        
        Args:
            config: 配置字典
        
        Returns:
            回溯天数
        """
        days = config['filters'].get('lookback_days', 2)
        logger.debug(f"Lookback days: {days}")
        return days
    
    def get_repo(self, config: Dict[str, Any]) -> str:
        """
        获取仓库名
        
        Args:
            config: 配置字典
        
        Returns:
            仓库名（格式：owner/repo）
        """
        repo = config['github']['repo']
        logger.debug(f"Repo: {repo}")
        return repo
    
    def get_excel_url(self, config: Dict[str, Any]) -> str:
        """
        获取 Excel/Google Sheets URL
        
        Args:
            config: 配置字典
        
        Returns:
            Google Sheets URL
        """
        url = config['excel'].get('url')
        logger.debug(f"Excel URL: {url}")
        return url
    
    def get_excel_gid(self, config: Dict[str, Any]) -> str:
        """
        获取 Excel/Google Sheets GID
        
        Args:
            config: 配置字典
        
        Returns:
            Google Sheets GID
        """
        gid = config['excel'].get('gid', '0')
        logger.debug(f"Excel GID: {gid}")
        return gid

    def get_data_sync_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取数据同步配置
        
        Args:
            config: 配置字典
        
        Returns:
            数据同步配置字典
        """
        default_config = {
            'enabled': True,
            'schedule': {
                'day': 'monday',
                'time': '07:00'
            }
        }
        
        sync_config = config.get('data_sync', default_config)
        return sync_config
    
    def get_special_labels(self, config: Dict[str, Any]) -> List[str]:
        """
        获取特殊 label 列表
        
        特殊 label 的 issue 直接分配给对应负责人，不看时间线。
        
        Args:
            config: 配置字典
        
        Returns:
            特殊 label 列表
        """
        default_labels = ['gqa-model', '310P']
        special_labels = config.get('assignee_rules', {}).get('special_labels', default_labels)
        logger.debug(f"Special labels: {special_labels}")
        return special_labels
    
    def get_pipeline_schedule(self, config: Dict[str, Any]) -> List[str]:
        """
        获取 Pipeline 调度时间列表
        
        Args:
            config: 配置字典
        
        Returns:
            调度时间列表，如 ["08:00", "14:00", "19:00"]
        """
        default_times = ["08:00", "14:00", "19:00"]
        pipeline_config = config.get('pipeline', {})
        schedule_config = pipeline_config.get('schedule', {})
        times = schedule_config.get('times', default_times)
        
        logger.debug(f"Pipeline schedule times: {times}")
        return times