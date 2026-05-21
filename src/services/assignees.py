"""
负责人服务模块

负责从 Issue 评论中提取完整的分配链和最终负责人。
"""

import re
from typing import List, Dict, Any, Optional
from src.models.issue import IssueInfo, AssigneeInfo, AssignmentChainItem
from src.utils.http import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AssigneeService:
    """
    负责人服务类
    
    通过分析 Issue 评论中的 @mention 来构建完整的分配链，
    确定最终负责人和分配流程图。
    
    Attributes:
        http_client: HTTP 客户端实例
        repo: GitHub 仓库名
    
    Example:
        service = AssigneeService(repo="owner/repo")
        assignees = service.get_assignees(issues)
    """
    
    def __init__(
        self,
        repo: str = "vllm-project/vllm-ascend",
        http_client: HttpClient = None
    ):
        """
        初始化负责人服务
        
        Args:
            repo: GitHub 仓库名（格式：owner/repo）
            http_client: HTTP 客户端，如果不提供则自动创建
        """
        self.repo = repo
        self.http_client = http_client or HttpClient()
        
        logger.info(f"AssigneeService initialized: repo={repo}")
    
    def extract_mentions(self, text: str) -> List[str]:
        """
        从文本中提取所有 @mention
        
        Args:
            text: 评论文本
        
        Returns:
            mention 用户名列表
        """
        if not text:
            return []
        
        mentions = re.findall(r'@([a-zA-Z0-9_-]+)', text)
        logger.debug(f"Found {len(mentions)} mentions in text")
        
        return mentions
    
    def build_comments_url(self, issue_number: int) -> str:
        """
        构建 Issue 评论 API URL
        
        Args:
            issue_number: Issue 编号
        
        Returns:
            评论 API URL
        """
        url = f"https://api.github.com/repos/{self.repo}/issues/{issue_number}/comments"
        return url
    
    def fetch_comments(self, issue_number: int) -> List[Dict[str, Any]]:
        """
        获取 Issue 评论
        
        Args:
            issue_number: Issue 编号
        
        Returns:
            评论列表
        """
        url = self.build_comments_url(issue_number)
        logger.debug(f"Fetching comments from: {url}")
        
        comments = self.http_client.get_with_delay(url)
        
        if comments is None:
            logger.warning(f"Failed to fetch comments for issue #{issue_number}")
            return []
        
        return comments
    
    def analyze_comment_mentions(
        self,
        comments: List[Dict[str, Any]]
    ) -> List[AssignmentChainItem]:
        """
        分析评论中的 @mention 构建分配链
        
        Args:
            comments: 评论列表
        
        Returns:
            分配链项列表
        """
        chain = []
        
        for comment in comments:
            body = comment.get('body', '')
            mentions = self.extract_mentions(body)
            
            if mentions:
                author = comment.get('user', {}).get('login', 'unknown')
                created_at = comment.get('created_at', '')
                
                for mentioned_user in mentions:
                    chain_item = AssignmentChainItem(
                        from_user=author,
                        to_user=mentioned_user,
                        method='mention',
                        time=created_at,
                        comment=body
                    )
                    chain.append(chain_item)
        
        return chain
    
    def determine_final_assignee(
        self,
        chain: List[AssignmentChainItem]
    ) -> Optional[str]:
        """
        确定最终负责人
        
        从分配链中选择最新的一个作为最终负责人。
        
        Args:
            chain: 分配链
        
        Returns:
            最终负责人用户名，如果没有则返回 None
        """
        if not chain:
            return None
        
        latest = max(chain, key=lambda x: x.time)
        assignee = latest.to_user
        
        logger.debug(f"Determined final assignee: {assignee}")
        
        return assignee
    
    def generate_flow_diagram(self, chain: List[AssignmentChainItem]) -> str:
        """
        生成流程图描述
        
        Args:
            chain: 分配链
        
        Returns:
            流程图文本描述
        """
        if not chain:
            return "No assignment flow found."
        
        lines = []
        for item in chain:
            safe_comment = ''.join(c if ord(c) < 65536 else '?' for c in item.comment)
            comment_preview = safe_comment[:50].replace('\n', ' ') if safe_comment else ''
            
            if item.method == 'mention':
                lines.append(
                    f"{item.from_user} -> {item.to_user} "
                    f"(via @{item.to_user}: \"{comment_preview}...\")"
                )
            else:
                lines.append(
                    f"{item.from_user} -> {item.to_user} (formal assignment)"
                )
        
        return '\n'.join(lines)
    
    def get_assignees(self, issues: List[IssueInfo]) -> List[AssigneeInfo]:
        """
        批量获取 Issue 分配链和负责人
        
        Args:
            issues: IssueInfo 列表
        
        Returns:
            AssigneeInfo 列表
        """
        logger.info(f"Processing {len(issues)} issues for assignees")
        
        results = []
        
        for i, issue in enumerate(issues):
            logger.info(f"Processing {i+1}/{len(issues)}: #{issue.number}")
            
            comments = self.fetch_comments(issue.number)
            chain = self.analyze_comment_mentions(comments)
            final_assignee = self.determine_final_assignee(chain)
            flow_diagram = self.generate_flow_diagram(chain)
            
            assignee_info = AssigneeInfo(
                issue_number=issue.number,
                issue_title=issue.title,
                issue_url=issue.html_url,
                state=issue.state,
                labels=issue.labels,
                assignment_chain=chain,
                final_assignee=final_assignee,
                has_formal_assignment=False,
                flow_diagram=flow_diagram
            )
            
            results.append(assignee_info)
        
        self._log_assignee_summary(results)
        
        return results
    
    def _log_assignee_summary(self, results: List[AssigneeInfo]):
        """
        打印负责人汇总
        
        Args:
            results: AssigneeInfo 列表
        """
        logger.info("=" * 50)
        logger.info("ASSIGNEE SUMMARY")
        logger.info("=" * 50)
        
        for result in results:
            assignee = result.final_assignee if result.final_assignee else "NOT ASSIGNED"
            logger.info(f"#{result.issue_number} -> {assignee}")
    
    def get_assignee_for_issue(
        self,
        issue_number: int,
        assignees: List[AssigneeInfo]
    ) -> Optional[str]:
        """
        从负责人列表中查找指定 Issue 的负责人
        
        Args:
            issue_number: Issue 编号
            assignees: AssigneeInfo 列表
        
        Returns:
            负责人用户名，如果没有则返回 None
        """
        for item in assignees:
            if item.issue_number == issue_number:
                return item.final_assignee
        
        return None