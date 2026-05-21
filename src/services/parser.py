"""
Issue 解析服务模块

负责从 GitHub API 获取并解析 Issue 数据，筛选出 triaged 的 Issue。
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from src.models.issue import IssueInfo
from src.utils.http import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IssueParser:
    """
    Issue 解析器类
    
    从 GitHub API 获取 Issue 数据，筛选带有 triaged 标签的 Issue。
    
    Attributes:
        repo: GitHub 仓库名
        lookback_days: 回溯天数
        http_client: HTTP 客户端
    
    Example:
        parser = IssueParser(repo="owner/repo", lookback_days=2)
        triaged_issues = parser.parse()
    """
    
    def __init__(
        self,
        repo: str = "vllm-project/vllm-ascend",
        lookback_days: int = 2,
        http_client: HttpClient = None
    ):
        """
        初始化 Issue 解析器
        
        Args:
            repo: GitHub 仓库名（格式：owner/repo）
            lookback_days: 回溯天数，只处理最近更新的 Issue
            http_client: HTTP 客户端
        """
        self.repo = repo
        self.lookback_days = lookback_days
        self.http_client = http_client or HttpClient()
        
        logger.info(
            f"IssueParser initialized: "
            f"repo={repo}, lookback_days={lookback_days}"
        )
    
    def build_issues_url(self) -> str:
        """构建 Issues API URL"""
        return f"https://api.github.com/repos/{self.repo}/issues"
    
    def fetch_issues_from_api(self) -> List[Dict[str, Any]]:
        """
        从 GitHub API 获取 Issues
        
        Returns:
            原始 Issue 数据列表
        """
        url = self.build_issues_url()
        logger.info(f"Fetching issues from: {url}")
        
        params = {
            'state': 'all',
            'per_page': 100
        }
        
        full_url = f"{url}?state=all&per_page=100"
        raw_data = self.http_client.get_with_delay(full_url)
        
        if raw_data is None:
            logger.error("Failed to fetch issues from GitHub API")
            return []
        
        logger.info(f"Fetched {len(raw_data)} issues from GitHub API")
        
        return raw_data
    
    def load_raw_data(self) -> List[Dict[str, Any]]:
        """
        加载原始数据
        
        Returns:
            原始 Issue 数据列表
        """
        return self.fetch_issues_from_api()
    
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