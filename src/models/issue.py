"""
数据模型模块

定义 Issue 数据模型和相关的数据结构。
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Issue:
    """
    Issue 数据模型
    
    表示 GitHub Issue 的核心属性，用于超期检查和负责人分析。
    
    Attributes:
        number: Issue 编号
        state: Issue 状态（open/closed）
        labels: Issue 标签列表
        triaged_at: 被标记为 triaged 的时间
        assignee: 最终负责人
    
    Example:
        issue = Issue(
            number=123,
            state="open",
            labels=["bug", "triaged"],
            triaged_at="2026-05-01T00:00:00Z",
            assignee="developer1"
        )
    """
    number: int
    state: str
    labels: List[str] = field(default_factory=list)
    triaged_at: Optional[str] = None
    assignee: Optional[str] = None
    
    def has_label(self, label_name: str) -> bool:
        """
        检查是否包含指定标签
        
        Args:
            label_name: 标签名称
        
        Returns:
            是否包含该标签
        """
        return label_name in self.labels
    
    def is_closed(self) -> bool:
        """
        检查 Issue 是否已关闭
        
        Returns:
            是否已关闭
        """
        return self.state == "closed"


@dataclass
class IssueInfo:
    """
    Issue 信息数据结构
    
    用于存储从 API 解析的完整 Issue 信息。
    
    Attributes:
        number: Issue 编号
        title: Issue 标题
        html_url: Issue 页面 URL
        events_url: Issue 事件 API URL
        created_at: 创建时间
        updated_at: 更新时间
        state: Issue 状态
        labels: 标签列表
    """
    number: int
    title: str = ""
    html_url: str = ""
    events_url: str = ""
    created_at: str = ""
    updated_at: str = ""
    state: str = "open"
    labels: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """
        转换为字典格式
        
        Returns:
            字典形式的 Issue 信息
        """
        return {
            'number': self.number,
            'title': self.title,
            'html_url': self.html_url,
            'events_url': self.events_url,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'state': self.state,
            'labels': self.labels
        }


@dataclass
class AssignmentChainItem:
    """
    分配链单项数据结构
    
    表示一次分配行为（mention 或 formal assignment）。
    
    Attributes:
        from_user: 分配发起人
        to_user: 分配接收人
        method: 分配方式（mention/formal_assignment）
        time: 分配时间
        comment: 评论内容（如果是 mention）
    """
    from_user: str
    to_user: str
    method: str = "mention"
    time: str = ""
    comment: str = ""
    
    def to_dict(self) -> dict:
        """
        转换为字典格式
        
        Returns:
            字典形式的分配链单项
        """
        return {
            'from': self.from_user,
            'to': self.to_user,
            'method': self.method,
            'time': self.time,
            'comment': self.comment
        }


@dataclass
class AssigneeInfo:
    """
    负责人信息数据结构
    
    用于存储 Issue 的负责人信息和相关状态。
    
    Attributes:
        issue_number: Issue 编号
        issue_title: Issue 标题
        issue_url: Issue 页面 URL
        state: Issue 状态
        labels: 标签列表
        assignment_chain: 分配链列表
        assignee_chain: 时间线上所有负责人 GitHub ID 列表（新增）
        final_assignee: 最终负责人 GitHub ID
        has_special_label: 是否包含特殊 label（新增）
        special_label_assignee: 特殊 label 对应的负责人姓名（新增）
        has_formal_assignment: 是否有正式分配
        flow_diagram: 流程图描述
    """
    issue_number: int
    issue_title: str = ""
    issue_url: str = ""
    state: str = "open"
    labels: List[str] = field(default_factory=list)
    assignment_chain: List[AssignmentChainItem] = field(default_factory=list)
    assignee_chain: List[str] = field(default_factory=list)
    final_assignee: Optional[str] = None
    has_special_label: bool = False
    special_label_assignee: Optional[str] = None
    has_formal_assignment: bool = False
    flow_diagram: str = "No assignment flow found."
    
    def to_dict(self) -> dict:
        """
        转换为字典格式
        
        Returns:
            字典形式的负责人信息
        """
        return {
            'issue_number': self.issue_number,
            'issue_title': self.issue_title,
            'issue_url': self.issue_url,
            'state': self.state,
            'labels': self.labels,
            'assignment_chain': [item.to_dict() for item in self.assignment_chain],
            'assignee_chain': self.assignee_chain,
            'final_assignee': self.final_assignee,
            'has_special_label': self.has_special_label,
            'special_label_assignee': self.special_label_assignee,
            'has_formal_assignment': self.has_formal_assignment,
            'flow_diagram': self.flow_diagram
        }