"""
事件服务模块

负责获取 Issue 的标签变更事件并提取 triaged 时间。
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from src.models.issue import IssueInfo
from src.utils.http import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EventService:
    """
    事件服务类
    
    获取 Issue 的标签变更事件，提取 triaged 标签添加时间。
    
    Attributes:
        http_client: HTTP 客户端实例
        lookback_days: 回溯天数
    
    Example:
        service = EventService(lookback_days=2)
        label_changes = service.fetch_events(issues)
        triaged_time = service.get_triaged_time(issue_number, label_changes)
    """
    
    def __init__(
        self,
        lookback_days: int = 2,
        http_client: HttpClient = None
    ):
        """
        初始化事件服务
        
        Args:
            lookback_days: 回溯天数
            http_client: HTTP 客户端，如果不提供则自动创建
        """
        self.lookback_days = lookback_days
        self.http_client = http_client or HttpClient()
        
        logger.info(f"EventService initialized: lookback_days={lookback_days}")
    
    def fetch_issue_events(self, events_url: str) -> List[Dict[str, Any]]:
        """
        获取单个 Issue 的所有事件
        
        Args:
            events_url: Issue 事件 API URL
        
        Returns:
            事件列表
        """
        logger.debug(f"Fetching events from: {events_url}")
        events = self.http_client.get(events_url)
        
        if events is None:
            logger.warning(f"Failed to fetch events from {events_url}")
            return []
        
        return events
    
    def parse_label_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析标签事件
        
        Args:
            event: 事件数据
        
        Returns:
            解析后的标签事件字典
        """
        label_name = event.get('label', {}).get('name', 'unknown')
        actor = event.get('actor', {}).get('login', 'unknown')
        
        return {
            'event_type': event.get('event'),
            'label_name': label_name,
            'actor': actor,
            'created_at': event.get('created_at')
        }
    
    def filter_recent_label_events(
        self,
        events: List[Dict[str, Any]],
        cutoff_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        筛选最近的标签变更事件
        
        Args:
            events: 事件列表
            cutoff_time: 截止时间
        
        Returns:
            筛选后的标签事件列表
        """
        label_events = []
        
        for event in events:
            event_type = event.get('event')
            if event_type not in ['labeled', 'unlabeled']:
                continue
            
            event_time_str = event.get('created_at', '')
            if not event_time_str:
                continue
            
            try:
                event_time = datetime.fromisoformat(
                    event_time_str.replace('Z', '+00:00')
                )
                
                if event_time >= cutoff_time:
                    label_events.append(self.parse_label_event(event))
            except ValueError as e:
                logger.warning(f"Invalid event time format: {e}")
        
        return label_events
    
    def fetch_events(self, issues: List[IssueInfo]) -> List[Dict[str, Any]]:
        """
        批量获取 Issue 的标签变更事件
        
        Args:
            issues: IssueInfo 列表
        
        Returns:
            标签变更报告列表，每个报告包含 Issue 信息和标签事件
        """
        logger.info(f"Fetching events for {len(issues)} issues")
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)
        label_changes = []
        
        for issue in issues:
            logger.info(f"Fetching events for issue #{issue.number}")
            
            events = self.fetch_issue_events(issue.events_url)
            recent_events = self.filter_recent_label_events(events, cutoff_time)
            
            if recent_events:
                label_changes.append({
                    'issue_number': issue.number,
                    'issue_title': issue.title,
                    'issue_url': issue.html_url,
                    'created_at': issue.created_at,
                    'label_events': recent_events
                })
        
        logger.info(
            f"Summary: {len(issues)} total issues, "
            f"{len(label_changes)} with label changes"
        )
        
        return label_changes
    
    def get_triaged_time(
        self,
        issue_number: int,
        label_changes: List[Dict[str, Any]]
    ) -> str:
        """
        从标签变更中获取 triaged 时间
        
        查找 triaged 标签的 labeled 事件，返回其时间。
        
        Args:
            issue_number: Issue 编号
            label_changes: 标签变更列表
        
        Returns:
            triaged 时间字符串，如果未找到则返回 None
        """
        for item in label_changes:
            if item['issue_number'] != issue_number:
                continue
            
            for event in item.get('label_events', []):
                if event['label_name'] == 'triaged' and event['event_type'] == 'labeled':
                    logger.debug(
                        f"Found triaged time for issue #{issue_number}: "
                        f"{event['created_at']}"
                    )
                    return event['created_at']
        
        logger.warning(f"No triaged time found for issue #{issue_number}")
        return None