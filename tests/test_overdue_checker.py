"""
超期检查器测试

测试 OverdueChecker 的各项功能。
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from datetime import datetime, timedelta, timezone
from models.issue import Issue
from services.checker import OverdueChecker


class TestOverdueChecker:
    """OverdueChecker 测试类"""
    
    def test_is_processed_closed_with_resolution_label(self):
        """测试：关闭且带处理标签的 Issue 应被判定为已处理"""
        issue = Issue(
            number=1,
            state="closed",
            labels=["triaged", "invalid"],
            triaged_at="2026-05-01T00:00:00Z",
            assignee="user1"
        )
        checker = OverdueChecker()
        assert checker.is_processed(issue) == True
    
    def test_is_processed_closed_without_resolution_label(self):
        """测试：关闭但无处理标签的 Issue 不应判定为已处理"""
        issue = Issue(
            number=2,
            state="closed",
            labels=["triaged", "bug"],
            triaged_at="2026-05-01T00:00:00Z",
            assignee="user1"
        )
        checker = OverdueChecker()
        assert checker.is_processed(issue) == False
    
    def test_is_processed_open_issue(self):
        """测试：开放的 Issue 不应判定为已处理"""
        issue = Issue(
            number=3,
            state="open",
            labels=["triaged", "bug"],
            triaged_at="2026-05-01T00:00:00Z",
            assignee="user1"
        )
        checker = OverdueChecker()
        assert checker.is_processed(issue) == False
    
    def test_is_overdue_within_7_days(self):
        """测试：7天内标记的 Issue 不应判定为超期"""
        now = datetime.now(timezone.utc)
        triaged_at = (now - timedelta(days=5)).isoformat()
        issue = Issue(
            number=4,
            state="open",
            labels=["triaged", "bug"],
            triaged_at=triaged_at,
            assignee="user1"
        )
        checker = OverdueChecker()
        assert checker.is_overdue(issue) == False
    
    def test_is_overdue_exceed_7_days(self):
        """测试：超过7天的 Issue 应判定为超期"""
        now = datetime.now(timezone.utc)
        triaged_at = (now - timedelta(days=10)).isoformat()
        issue = Issue(
            number=5,
            state="open",
            labels=["triaged", "bug"],
            triaged_at=triaged_at,
            assignee="user1"
        )
        checker = OverdueChecker()
        assert checker.is_overdue(issue) == True
    
    def test_find_overdue_issues(self):
        """测试：查找所有已分配、超期且未处理的 Issue"""
        now = datetime.now(timezone.utc)
        issues = [
            Issue(number=1, state="open", labels=["triaged"], 
                  triaged_at=(now - timedelta(days=10)).isoformat(), assignee="user1"),
            Issue(number=2, state="open", labels=["triaged"],
                  triaged_at=(now - timedelta(days=3)).isoformat(), assignee="user2"),
            Issue(number=3, state="closed", labels=["triaged", "invalid"],
                  triaged_at=(now - timedelta(days=15)).isoformat(), assignee="user3"),
            Issue(number=4, state="open", labels=["triaged"],
                  triaged_at=(now - timedelta(days=10)).isoformat(), assignee=None),
        ]
        checker = OverdueChecker()
        overdue = checker.find_overdue_issues(issues)
        assert len(overdue) == 1
        assert overdue[0].number == 1
    
    def test_all_resolution_labels(self):
        """测试：所有处理标签都能正确判定 Issue 为已处理"""
        resolution_labels = ["invalid", "wontfix", "duplicated", "wait-feedback"]
        checker = OverdueChecker()
        
        for label in resolution_labels:
            issue = Issue(
                number=100,
                state="closed",
                labels=["triaged", label],
                triaged_at="2026-05-01T00:00:00Z",
                assignee="user1"
            )
            assert checker.is_processed(issue) == True, f"Label {label} should be processed"
    
    def test_custom_resolution_labels(self):
        """测试：支持通过配置自定义处理标签"""
        issue = Issue(
            number=10,
            state="closed",
            labels=["triaged", "custom-done"],
            triaged_at="2026-05-01T00:00:00Z",
            assignee="user1"
        )
        checker = OverdueChecker(resolution_labels=['custom-done', 'another'])
        assert checker.is_processed(issue) == True
    
    def test_custom_overdue_days(self):
        """测试：支持通过配置自定义超期天数"""
        now = datetime.now(timezone.utc)
        issue = Issue(
            number=11,
            state="open",
            labels=["triaged"],
            triaged_at=(now - timedelta(days=5)).isoformat(),
            assignee="user1"
        )
        checker = OverdueChecker(overdue_days=3)
        assert checker.is_overdue(issue) == True