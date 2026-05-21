"""
集成测试

使用模拟数据测试完整流程。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from datetime import datetime, timezone, timedelta
from models.issue import Issue
from services.checker import OverdueChecker


def test_with_mock_data():
    """
    使用模拟数据测试完整场景
    
    模拟场景：7个 Issue，其中：
    - Issue 101: 开放，超期10天，有负责人 -> 应判定为超期
    - Issue 102: 关闭，带 invalid 标签 -> 已处理
    - Issue 103: 开放，超期8天，有负责人 -> 应判定为超期
    - Issue 104: 开放，未超期 -> 正常
    - Issue 105: 关闭，带 wait-feedback 标签 -> 已处理
    - Issue 106: 开放，超期，无负责人 -> 应跳过
    - Issue 107: 关闭，带 wontfix 标签 -> 已处理
    
    预期结果：Issue 101 和 103 应被标记为超期未处理
    """
    now = datetime.now(timezone.utc)
    
    mock_issues = [
        Issue(101, "open", ["triaged", "bug"], 
              (now - timedelta(days=10)).isoformat(), "developer1"),
        Issue(102, "closed", ["triaged", "invalid"],
              (now - timedelta(days=15)).isoformat(), "developer2"),
        Issue(103, "open", ["triaged"],
              (now - timedelta(days=8)).isoformat(), "developer3"),
        Issue(104, "open", ["triaged"],
              (now - timedelta(days=5)).isoformat(), "developer4"),
        Issue(105, "closed", ["triaged", "wait-feedback"],
              (now - timedelta(days=20)).isoformat(), "developer5"),
        Issue(106, "open", ["triaged"],
              (now - timedelta(days=12)).isoformat(), None),
        Issue(107, "closed", ["triaged", "wontfix"],
              (now - timedelta(days=30)).isoformat(), "developer7"),
    ]
    
    checker = OverdueChecker()
    overdue = checker.find_overdue_issues(mock_issues)
    
    print("=" * 60)
    print("MOCK DATA TEST - Expected: Issues 101 and 103")
    print("=" * 60)
    
    for issue in overdue:
        triaged_time = datetime.fromisoformat(issue.triaged_at.replace("Z", "+00:00"))
        days_passed = (now - triaged_time).days
        print(f"#{issue.number} | {days_passed} days overdue | Assignee: {issue.assignee}")
    
    assert len(overdue) == 2, f"Expected 2 overdue issues, got {len(overdue)}"
    assert overdue[0].number == 101
    assert overdue[1].number == 103
    print("\nTest passed!")


if __name__ == '__main__':
    test_with_mock_data()