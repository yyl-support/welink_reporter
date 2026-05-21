"""
超期检查器服务模块

负责判断 Issue 是否已处理和是否超期的核心逻辑。
"""

from datetime import datetime, timezone, timedelta
from typing import List
from src.models.issue import Issue
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OverdueChecker:
    """
    超期检查器类
    
    判断 Issue 的处理状态和超期状态，筛选出需要关注的超期未处理 Issue。
    
    Attributes:
        resolution_labels: 标记为已处理的标签列表
        overdue_days: 超期天数阈值
    
    Example:
        checker = OverdueChecker(
            resolution_labels=['invalid', 'wontfix'],
            overdue_days=7
        )
        overdue_issues = checker.find_overdue_issues(issues)
    """
    
    def __init__(
        self,
        resolution_labels: List[str] = None,
        overdue_days: int = 7
    ):
        """
        初始化超期检查器
        
        Args:
            resolution_labels: 已处理标签列表，默认使用常见标签
            overdue_days: 超期天数，默认为 7 天
        """
        self.resolution_labels = resolution_labels or [
            'invalid', 'wontfix', 'duplicated', 'wait-feedback', 'resolved'
        ]
        self.overdue_days = overdue_days
        
        logger.info(
            f"OverdueChecker initialized: "
            f"overdue_days={overdue_days}, "
            f"resolution_labels={resolution_labels}"
        )
    
    def is_processed(self, issue: Issue) -> bool:
        """
        判断 Issue 是否已被处理
        
        处理条件：Issue 已关闭且包含任意一个已处理标签。
        
        Args:
            issue: Issue 实例
        
        Returns:
            是否已处理
        
        Note:
            已处理的定义：state == "closed" AND labels 包含 resolution_labels 之一
        """
        if not issue.is_closed():
            return False
        
        for label in issue.labels:
            if label in self.resolution_labels:
                logger.debug(
                    f"Issue #{issue.number} is processed: "
                    f"closed with label '{label}'"
                )
                return True
        
        return False
    
    def is_overdue(self, issue: Issue) -> bool:
        """
        判断 Issue 是否已超期
        
        超期条件：从 triaged 时间至今已超过 overdue_days 天。
        
        Args:
            issue: Issue 实例
        
        Returns:
            是否已超期
        
        Raises:
            ValueError: triaged_at 格式无效
        """
        if issue.triaged_at is None:
            logger.warning(f"Issue #{issue.number} has no triaged_at time")
            return False
        
        try:
            triaged_time = datetime.fromisoformat(
                issue.triaged_at.replace("Z", "+00:00")
            )
        except ValueError as e:
            logger.error(f"Invalid triaged_at format for issue #{issue.number}: {e}")
            return False
        
        now = datetime.now(timezone.utc)
        days_passed = (now - triaged_time).days
        is_overdue = days_passed > self.overdue_days
        
        if is_overdue:
            logger.debug(
                f"Issue #{issue.number} is overdue: "
                f"{days_passed} days passed (threshold: {self.overdue_days})"
            )
        
        return is_overdue
    
    def find_overdue_issues(self, issues: List[Issue]) -> List[Issue]:
        """
        查找所有超期未处理的 Issue
        
        筛选条件：
        1. 有负责人（assignee 不为空）
        2. 未被处理（is_processed == False）
        3. 已超期（is_overdue == True）
        
        Args:
            issues: Issue 列表
        
        Returns:
            超期未处理的 Issue 列表
        
        Note:
            输出条件：is_assigned AND is_overdue AND NOT is_processed
        """
        logger.info(f"Checking {len(issues)} issues for overdue status")
        
        overdue_list = []
        
        for issue in issues:
            if issue.assignee is None:
                logger.debug(f"Issue #{issue.number} skipped: no assignee")
                continue
            
            if self.is_processed(issue):
                logger.debug(f"Issue #{issue.number} skipped: already processed")
                continue
            
            if self.is_overdue(issue):
                overdue_list.append(issue)
                logger.info(
                    f"Issue #{issue.number} is overdue and unprocessed "
                    f"(assignee: {issue.assignee})"
                )
        
        logger.info(f"Found {len(overdue_list)} overdue unprocessed issues")
        
        return overdue_list
    
    def calculate_days_overdue(self, issue: Issue) -> int:
        """
        计算 Issue 超期天数
        
        Args:
            issue: Issue 实例
        
        Returns:
            超期天数，如果无法计算则返回 -1
        """
        if issue.triaged_at is None:
            return -1
        
        try:
            triaged_time = datetime.fromisoformat(
                issue.triaged_at.replace("Z", "+00:00")
            )
            now = datetime.now(timezone.utc)
            return (now - triaged_time).days
        except ValueError:
            return -1