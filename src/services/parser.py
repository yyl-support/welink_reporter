"""
Issue 解析服务模块

负责解析原始 Issue 数据并筛选出 triaged 的 Issue。
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from src.models.issue import IssueInfo
from src.utils.logger import get_logger

logger = get_logger(__name__)

DATA_SOURCE_FILE = r"C:\Users\Administrator\.local\share\opencode\tool-output\tool_e49e0646a001ZsrKha1BzGVCKT"


class IssueParser:
    """
    Issue 解析器类
    
    从数据源解析 Issue 数据，筛选带有 triaged 标签的 Issue。
    
    Attributes:
        data_source: 数据源文件路径
        lookback_days: 回溯天数
    
    Example:
        parser = IssueParser(data_source="data.json", lookback_days=2)
        triaged_issues = parser.parse()
    """
    
    def __init__(
        self,
        data_source: str = DATA_SOURCE_FILE,
        lookback_days: int = 2
    ):
        """
        初始化 Issue 解析器
        
        Args:
            data_source: 数据源文件路径
            lookback_days: 回溯天数，只处理最近更新的 Issue
        """
        self.data_source = data_source
        self.lookback_days = lookback_days
        
        logger.info(
            f"IssueParser initialized: "
            f"lookback_days={lookback_days}, "
            f"data_source={data_source}"
        )
    
    def load_raw_data(self) -> List[Dict[str, Any]]:
        """
        加载原始数据
        
        Args:
            data_source: 数据源文件路径
        
        Returns:
            原始 Issue 数据列表
        
        Raises:
            FileNotFoundError: 数据源文件不存在
            json.JSONDecodeError: JSON 解析错误
        """
        logger.info(f"Loading raw data from: {self.data_source}")
        
        if not os.path.exists(self.data_source):
            logger.error(f"Data source not found: {self.data_source}")
            raise FileNotFoundError(f"Data source not found: {self.data_source}")
        
        with open(self.data_source, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        logger.info(f"Loaded {len(raw_data)} raw issues")
        
        return raw_data
    
    def is_triaged(self, issue_data: Dict[str, Any]) -> bool:
        """
        检查 Issue 是否带有 triaged 标签
        
        Args:
            issue_data: Issue 数据字典
        
        Returns:
            是否带有 triaged 标签
        """
        labels = issue_data.get('labels', [])
        return any(label.get('name') == 'triaged' for label in labels)
    
    def is_recently_updated(
        self,
        issue_data: Dict[str, Any],
        cutoff_time: datetime
    ) -> bool:
        """
        检查 Issue 是否在指定时间后更新
        
        Args:
            issue_data: Issue 数据字典
            cutoff_time: 截止时间
        
        Returns:
            是否在截止时间后更新
        """
        updated_at_str = issue_data.get('updated_at', '')
        if not updated_at_str:
            return False
        
        try:
            updated_at = datetime.fromisoformat(
                updated_at_str.replace('Z', '+00:00')
            )
            return updated_at >= cutoff_time
        except ValueError as e:
            logger.warning(f"Invalid updated_at format: {e}")
            return False
    
    def parse_issue(self, issue_data: Dict[str, Any]) -> IssueInfo:
        """
        解析单个 Issue 数据
        
        Args:
            issue_data: Issue 数据字典
        
        Returns:
            IssueInfo 实例
        """
        labels = issue_data.get('labels', [])
        label_names = [label.get('name', '') for label in labels]
        
        return IssueInfo(
            number=issue_data['number'],
            title=issue_data.get('title', ''),
            html_url=issue_data.get('html_url', ''),
            events_url=issue_data.get('events_url', ''),
            created_at=issue_data.get('created_at', ''),
            updated_at=issue_data.get('updated_at', ''),
            state=issue_data.get('state', 'open'),
            labels=label_names
        )
    
    def parse(self) -> List[IssueInfo]:
        """
        解析并筛选 triaged Issue
        
        筛选条件：
        1. 带有 triaged 标签
        2. 在 lookback_days 内更新
        
        Returns:
            筛选后的 IssueInfo 列表
        """
        logger.info("Starting issue parsing...")
        
        raw_data = self.load_raw_data()
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)
        logger.info(f"Looking for issues updated since: {cutoff_time.isoformat()}")
        
        triaged_issues = []
        
        for issue_data in raw_data:
            if not self.is_triaged(issue_data):
                continue
            
            if not self.is_recently_updated(issue_data, cutoff_time):
                continue
            
            issue_info = self.parse_issue(issue_data)
            triaged_issues.append(issue_info)
        
        logger.info(
            f"Found {len(triaged_issues)} triaged issues "
            f"from last {self.lookback_days} days"
        )
        
        return triaged_issues