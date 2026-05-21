"""
完整数据获取服务模块

负责获取 Issue 的完整数据，包括评论和事件时间线。
"""

import re
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from src.models.issue import IssueInfo
from src.utils.http import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FetchFullDataService:
    """
    完整数据获取服务
    
    获取 Issue 的完整数据，包括评论和事件时间线（labels、mentions、assignments）。
    
    Attributes:
        http_client: HTTP 客户端实例
        repo: GitHub 仓库名
        lookback_days: 回溯天数
    
    Example:
        service = FetchFullDataService(repo="owner/repo", lookback_days=2)
        full_data = service.fetch_full_data(issues)
    """
    
    def __init__(
        self,
        repo: str = "vllm-project/vllm-ascend",
        lookback_days: int = 2,
        http_client: HttpClient = None
    ):
        """
        初始化完整数据获取服务
        
        Args:
            repo: GitHub 仓库名
            lookback_days: 回溯天数
            http_client: HTTP 客户端
        """
        self.repo = repo
        self.lookback_days = lookback_days
        self.http_client = http_client or HttpClient()
        self.cutoff_time = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        
        logger.info(f"FetchFullDataService initialized: repo={repo}, lookback_days={lookback_days}")
    
    def extract_mentions(self, text: str) -> List[str]:
        """
        从文本中提取 @mention
        
        Args:
            text: 文本内容
        
        Returns:
            mention 用户名列表
        """
        if not text:
            return []
        return re.findall(r'@([a-zA-Z0-9_-]+)', text)
    
    def build_comments_url(self, issue_number: int) -> str:
        """构建评论 URL"""
        return f"https://api.github.com/repos/{self.repo}/issues/{issue_number}/comments"
    
    def build_timeline_url(self, issue_number: int) -> str:
        """构建时间线 URL"""
        return f"https://api.github.com/repos/{self.repo}/issues/{issue_number}/timeline"
    
    def fetch_comments(self, issue_number: int) -> List[Dict[str, Any]]:
        """
        获取 Issue 评论
        
        Args:
            issue_number: Issue 编号
        
        Returns:
            评论列表
        """
        url = self.build_comments_url(issue_number)
        logger.debug(f"Fetching comments: {url}")
        
        comments = self.http_client.get_with_delay(url)
        if comments is None:
            return []
        
        return comments
    
    def fetch_timeline(self, issue_number: int) -> List[Dict[str, Any]]:
        """
        获取 Issue 时间线
        
        Args:
            issue_number: Issue 编号
        
        Returns:
            时间线事件列表
        """
        url = self.build_timeline_url(issue_number)
        logger.debug(f"Fetching timeline: {url}")
        
        timeline = self.http_client.get_with_delay(url)
        if timeline is None:
            return []
        
        return timeline
    
    def parse_comments(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析评论数据
        
        Args:
            comments: 原始评论列表
        
        Returns:
            解析后的评论列表
        """
        parsed_comments = []
        
        for comment in comments:
            created_at_str = comment.get('created_at', '')
            if not created_at_str:
                continue
            
            try:
                comment_time = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                if comment_time < self.cutoff_time:
                    continue
            except ValueError:
                continue
            
            body = comment.get('body', '')
            mentions = self.extract_mentions(body)
            
            parsed_comments.append({
                'author': comment.get('user', {}).get('login', 'unknown'),
                'body': body,
                'mentions': mentions,
                'created_at': created_at_str,
                'html_url': comment.get('html_url', '')
            })
        
        return parsed_comments
    
    def parse_timeline(self, timeline: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        解析时间线数据
        
        Args:
            timeline: 原始时间线列表
        
        Returns:
            解析后的事件字典（label_events, mention_events, assign_events）
        """
        label_events = []
        mention_events = []
        assign_events = []
        
        for event in timeline:
            created_at_str = event.get('created_at', '')
            if not created_at_str:
                continue
            
            try:
                event_time = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                if event_time < self.cutoff_time:
                    continue
            except ValueError:
                continue
            
            event_type = event.get('event')
            actor = event.get('actor', {})
            actor_login = actor.get('login', 'unknown') if actor else 'unknown'
            
            if event_type == 'labeled':
                label_name = event.get('label', {}).get('name', 'unknown')
                label_events.append({
                    'event_type': 'labeled',
                    'label_name': label_name,
                    'actor': actor_login,
                    'created_at': created_at_str
                })
            elif event_type == 'unlabeled':
                label_name = event.get('label', {}).get('name', 'unknown')
                label_events.append({
                    'event_type': 'unlabeled',
                    'label_name': label_name,
                    'actor': actor_login,
                    'created_at': created_at_str
                })
            elif event_type == 'mentioned':
                mention_events.append({
                    'mentioned_user': actor_login,
                    'created_at': created_at_str
                })
            elif event_type == 'assigned':
                assignee = event.get('assignee', {})
                assignee_login = assignee.get('login', 'unknown') if assignee else 'unknown'
                assign_events.append({
                    'assignee': assignee_login,
                    'actor': actor_login,
                    'created_at': created_at_str
                })
            elif event_type == 'commented':
                body = event.get('body', '')
                mentions = self.extract_mentions(body)
                if mentions:
                    mention_events.append({
                        'mentioned_users': mentions,
                        'by_commenter': actor_login,
                        'created_at': created_at_str,
                        'comment_body': body
                    })
        
        return {
            'label_events': label_events,
            'mention_events': mention_events,
            'assign_events': assign_events
        }
    
    def fetch_issue_full_data(self, issue: IssueInfo) -> Dict[str, Any]:
        """
        获取单个 Issue 的完整数据
        
        Args:
            issue: IssueInfo 实例
        
        Returns:
            完整 Issue 数据字典
        """
        logger.info(f"Fetching full data for issue #{issue.number}")
        
        comments = self.fetch_comments(issue.number)
        timeline = self.fetch_timeline(issue.number)
        
        parsed_comments = self.parse_comments(comments)
        parsed_events = self.parse_timeline(timeline)
        
        return {
            'issue_number': issue.number,
            'issue_title': issue.title,
            'issue_url': issue.html_url,
            'created_at': issue.created_at,
            'state': issue.state,
            'labels': issue.labels,
            'comments': parsed_comments,
            'label_events': parsed_events['label_events'],
            'mention_events': parsed_events['mention_events'],
            'assign_events': parsed_events['assign_events']
        }
    
    def fetch_full_data(self, issues: List[IssueInfo]) -> Dict[str, Any]:
        """
        批量获取 Issue 完整数据
        
        Args:
            issues: IssueInfo 列表
        
        Returns:
            完整数据报告
        """
        logger.info(f"Fetching full data for {len(issues)} issues")
        
        full_report = []
        
        for issue in issues:
            issue_data = self.fetch_issue_full_data(issue)
            full_report.append(issue_data)
        
        report = {
            'fetch_time': datetime.now(timezone.utc).isoformat(),
            'total_issues': len(full_report),
            'issues': full_report
        }
        
        self._log_summary(full_report)
        
        return report
    
    def _log_summary(self, full_report: List[Dict[str, Any]]):
        """
        打印汇总信息
        
        Args:
            full_report: 完整数据报告
        """
        issues_with_mentions = [
            i for i in full_report 
            if i['mention_events'] or any(c['mentions'] for c in i['comments'])
        ]
        
        logger.info("=" * 50)
        logger.info("FULL DATA FETCH SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total issues processed: {len(full_report)}")
        logger.info(f"Issues with mentions: {len(issues_with_mentions)}")