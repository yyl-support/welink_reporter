# Issue #2: WeLink消息通知负责人规则修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正 WeLink 通知负责人分配规则，支持特殊 label 直接分配、保留完整时间线负责人链路、以及多级匹配优先级

**Architecture:** 修改 analyze_assignment.py 保留完整分配链而非仅最后一人；新增特殊 label 检测逻辑；修改 welink_inform.py 实现四级匹配优先级：特殊 label -> 时间线负责人 -> label 映射 -> @所有人

**Tech Stack:** Python, JSON

---

## 文件结构

**修改文件:**
- `src/services/analyze_assignment.py` - 修改为保留完整时间线负责人链路，新增特殊 label 检测
- `src/services/welink_inform.py` - 实现新的匹配优先级逻辑
- `src/models/issue.py` - 更新数据结构支持多负责人
- `config.yaml` - 添加特殊 label 配置
- `src/config/loader.py` - 添加特殊 label 配置读取

**依赖:**
- Issue #1 的 `data/issue_label.json` 文件（Label -> 负责人映射）

---

## Task 1: 更新配置文件添加特殊 Label

**Files:**
- Modify: `config.yaml`
- Modify: `src/config/loader.py`

- [ ] **Step 1: 更新 config.yaml 添加特殊 label 配置**

在 `config.yaml` 中添加：

```yaml
assignee_rules:
  special_labels:
    - "gqa-model"
    - "310P"
```

- [ ] **Step 2: 更新 config/loader.py 添加特殊 label 读取方法**

在 `ConfigLoader` 类中添加：

```python
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
```

- [ ] **Step 3: 更新 DEFAULT_CONFIG**

在 `loader.py` 的 `DEFAULT_CONFIG` 中添加：

```python
DEFAULT_CONFIG: Dict[str, Any] = {
    # ... 现有配置 ...
    'assignee_rules': {
        'special_labels': ['gqa-model', '310P']
    }
}
```

---

## Task 2: 更新数据模型支持多负责人

**Files:**
- Modify: `src/models/issue.py`

- [ ] **Step 1: 更新 AssigneeInfo 数据结构**

修改 `src/models/issue.py` 中的 `AssigneeInfo` dataclass：

```python
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
    assignee_chain: List[str] = field(default_factory=list)  # 新增：所有负责人
    final_assignee: Optional[str] = None
    has_special_label: bool = False  # 新增
    special_label_assignee: Optional[str] = None  # 新增
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
            'assignee_chain': self.assignee_chain,  # 新增
            'final_assignee': self.final_assignee,
            'has_special_label': self.has_special_label,  # 新增
            'special_label_assignee': self.special_label_assignee,  # 新增
            'has_formal_assignment': self.has_formal_assignment,
            'flow_diagram': self.flow_diagram
        }
```

---

## Task 3: 修改 analyze_assignment.py 保留完整负责人链路

**Files:**
- Modify: `src/services/analyze_assignment.py`

- [ ] **Step 1: 修改 analyze_task_assignment 方法**

修改 `analyze_task_assignment` 方法，保留完整负责人链路：

```python
def analyze_task_assignment(
    self,
    issue_data: Dict[str, Any],
    special_labels: List[str] = None
) -> Dict[str, Any]:
    """
    分析 Issue 的任务分配流程
    
    Args:
        issue_data: Issue 完整数据（包含 comments, label_events, mention_events, assign_events）
        special_labels: 特殊 label 列表（包含这些 label 的 issue 直接分配）
    
    Returns:
        分析结果：
        - assignment_chain: 分配链列表
        - assignee_chain: 时间线上所有负责人 GitHub ID 列表
        - final_assignee: 最终负责人
        - has_formal_assignment: 是否有正式分配
        - has_special_label: 是否包含特殊 label
        - special_labels_found: 发现的特殊 label 列表
    """
    if special_labels is None:
        special_labels = ['gqa-model', '310P']
    
    assignment_chain = []
    formal_assignees = []
    all_assignees = set()  # 收集所有负责人
    
    comments = issue_data.get('comments', [])
    assign_events = issue_data.get('assign_events', [])
    mention_events = issue_data.get('mention_events', [])
    issue_labels = issue_data.get('labels', [])
    
    # 检查特殊 label
    special_labels_found = [label for label in issue_labels if label in special_labels]
    has_special_label = len(special_labels_found) > 0
    
    for event in assign_events:
        assignee = event.get('assignee')
        formal_assignees.append({
            'assignee': assignee,
            'actor': event.get('actor'),
            'time': event.get('created_at')
        })
        assignment_chain.append({
            'from': event.get('actor'),
            'to': assignee,
            'method': 'formal_assignment',
            'time': event.get('created_at'),
            'comment': None
        })
        if assignee:
            all_assignees.add(assignee)
    
    comment_mentions = []
    for comment in comments:
        mentions = comment.get('mentions', [])
        if mentions:
            for mentioned_user in mentions:
                comment_mentions.append({
                    'from': comment.get('author'),
                    'to': mentioned_user,
                    'method': 'mention',
                    'time': comment.get('created_at'),
                    'comment': comment.get('body', '')
                })
                all_assignees.add(mentioned_user)
    
    for event in mention_events:
        if 'by_commenter' in event and 'mentioned_users' in event:
            for user in event['mentioned_users']:
                exists = any(
                    m['from'] == event['by_commenter'] and m['to'] == user
                    for m in comment_mentions
                )
                if not exists:
                    comment_mentions.append({
                        'from': event['by_commenter'],
                        'to': user,
                        'method': 'mention',
                        'time': event.get('created_at'),
                        'comment': event.get('comment_body', '')
                    })
                    all_assignees.add(user)
    
    all_assignments = assignment_chain + comment_mentions
    all_assignments.sort(key=lambda x: x.get('time', ''))
    
    final_assignee = None
    if formal_assignees:
        latest = max(formal_assignees, key=lambda x: x['time'])
        final_assignee = latest['assignee']
    elif comment_mentions:
        latest = max(comment_mentions, key=lambda x: x['time'])
        final_assignee = latest['to']
    
    return {
        'assignment_chain': all_assignments,
        'assignee_chain': list(all_assignees),  # 所有负责人列表
        'final_assignee': final_assignee,
        'has_formal_assignment': len(formal_assignees) > 0,
        'has_special_label': has_special_label,
        'special_labels_found': special_labels_found
    }
```

- [ ] **Step 2: 修改 analyze_issue 方法**

修改 `analyze_issue` 方法：

```python
def analyze_issue(
    self,
    issue_data: Dict[str, Any],
    special_labels: List[str] = None,
    label_mapping: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    分析单个 Issue 的分配情况
    
    Args:
        issue_data: Issue 完整数据
        special_labels: 特殊 label 列表
        label_mapping: Label -> 负责人姓名映射
    
    Returns:
        分配分析结果
    """
    if special_labels is None:
        special_labels = ['gqa-model', '310P']
    if label_mapping is None:
        label_mapping = {}
    
    analysis = self.analyze_task_assignment(issue_data, special_labels)
    flow_diagram = self.generate_flow_diagram(analysis['assignment_chain'])
    
    # 处理特殊 label 的负责人
    special_label_assignee = None
    if analysis['has_special_label'] and analysis['special_labels_found']:
        # 取第一个匹配的特殊 label 对应的负责人
        for label in analysis['special_labels_found']:
            if label in label_mapping:
                special_label_assignee = label_mapping[label]
                break
    
    return {
        'issue_number': issue_data['issue_number'],
        'issue_title': issue_data['issue_title'],
        'issue_url': issue_data['issue_url'],
        'state': issue_data['state'],
        'labels': issue_data.get('labels', []),
        'assignment_chain': analysis['assignment_chain'],
        'assignee_chain': analysis['assignee_chain'],  # 新增
        'final_assignee': analysis['final_assignee'],
        'has_special_label': analysis['has_special_label'],  # 新增
        'special_label_assignee': special_label_assignee,  # 新增
        'has_formal_assignment': analysis['has_formal_assignment'],
        'flow_diagram': flow_diagram
    }
```

- [ ] **Step 3: 修改 generate_analysis_report 方法**

修改 `generate_analysis_report` 方法：

```python
def generate_analysis_report(
    self,
    full_report: Dict[str, Any],
    special_labels: List[str] = None,
    label_mapping: Dict[str, str] = None
) -> List[Dict[str, Any]]:
    """
    批量分析 Issue 分配情况
    
    Args:
        full_report: 完整数据报告
        special_labels: 特殊 label 列表
        label_mapping: Label -> 负责人姓名映射
    
    Returns:
        分配分析报告列表
    """
    if special_labels is None:
        special_labels = ['gqa-model', '310P']
    if label_mapping is None:
        label_mapping = {}
    
    issues = full_report.get('issues', [])
    
    logger.info(f"Analyzing assignment for {len(issues)} issues")
    logger.info(f"Special labels: {special_labels}")
    
    results = []
    for issue in issues:
        result = self.analyze_issue(issue, special_labels, label_mapping)
        results.append(result)
    
    self._log_analysis_summary(results)
    
    return results
```

- [ ] **Step 4: 更新 _log_analysis_summary 方法**

修改 `_log_analysis_summary` 方法：

```python
def _log_analysis_summary(self, results: List[Dict[str, Any]]):
    """
    打印分析汇总
    
    Args:
        results: 分析结果列表
    """
    assigned_issues = [r for r in results if r['final_assignee']]
    unassigned_issues = [r for r in results if not r['final_assignee']]
    special_label_issues = [r for r in results if r['has_special_label']]
    
    logger.info("=" * 60)
    logger.info("ISSUE ASSIGNMENT ANALYSIS REPORT")
    logger.info("=" * 60)
    logger.info(f"Total issues analyzed: {len(results)}")
    logger.info(f"Issues with assignment: {len(assigned_issues)}")
    logger.info(f"Issues without assignment: {len(unassigned_issues)}")
    logger.info(f"Issues with special labels: {len(special_label_issues)}")
    
    if special_label_issues:
        logger.info("-" * 60)
        logger.info("SPECIAL LABEL ISSUES")
        logger.info("-" * 60)
        for r in special_label_issues:
            title_preview = r['issue_title'][:50] if r['issue_title'] else ''
            logger.info(f"#{r['issue_number']}: {title_preview}...")
            logger.info(f"  Special labels: {r.get('special_labels_found', [])}")
            logger.info(f"  Special label assignee: {r.get('special_label_assignee')}")
            logger.info(f"  Assignee chain: {r['assignee_chain']}")
    
    if assigned_issues:
        logger.info("-" * 60)
        logger.info("ASSIGNED ISSUES")
        logger.info("-" * 60)
        for r in assigned_issues:
            title_preview = r['issue_title'][:50] if r['issue_title'] else ''
            logger.info(f"#{r['issue_number']}: {title_preview}...")
            logger.info(f"  State: {r['state']}")
            logger.info(f"  Formal Assignment: {r['has_formal_assignment']}")
            logger.info(f"  Final Assignee: {r['final_assignee']}")
            logger.info(f"  Assignee Chain: {r['assignee_chain']}")
    
    if unassigned_issues:
        logger.info("-" * 60)
        logger.info("UNASSIGNED ISSUES")
        logger.info("-" * 60)
        for r in unassigned_issues:
            title_preview = r['issue_title'][:50] if r['issue_title'] else ''
            logger.info(f"#{r['issue_number']}: {title_preview}...")
            logger.info(f"  State: {r['state']}")
            logger.info("  No assignment found (triaged but not assigned to anyone)")
```

---

## Task 4: 修改 welink_inform.py 实现四级匹配优先级

**Files:**
- Modify: `src/services/welink_inform.py`

- [ ] **Step 1: 添加匹配优先级方法**

在 `WeLinkInformService` 类中添加：

```python
import json
import os
from typing import Dict, List, Any, Optional
from collections import defaultdict
from ..utils.logger import get_logger

logger = get_logger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')


class WeLinkInformService:
    # ... 现有代码 ...
    
    def find_best_assignee(
        self,
        issue_data: Dict[str, Any],
        github_id_to_name: Dict[str, str],
        label_to_name: Dict[str, str]
    ) -> Optional[str]:
        """
        按优先级查找最佳负责人
        
        匹配优先级:
        1. 特殊 label (gqa-model, 310P) -> 直接返回对应负责人姓名
        2. 时间线负责人 -> 匹配 GitHub ID 映射找到人名
        3. 时间线负责人匹配失败 -> 使用 issue 的 label 映射
        4. 全都失败 -> 返回 None (将使用 URL 作为 @所有人)
        
        Args:
            issue_data: Issue 分析数据
            github_id_to_name: GitHub ID -> 人名映射
            label_to_name: Label -> 负责人姓名映射
        
        Returns:
            最佳负责人姓名，如果找不到返回 None
        """
        # 优先级 1: 特殊 label
        if issue_data.get('has_special_label') and issue_data.get('special_label_assignee'):
            special_assignee = issue_data['special_label_assignee']
            logger.debug(f"Issue #{issue_data['issue_number']}: Special label assignee -> {special_assignee}")
            return special_assignee
        
        # 优先级 2: 时间线负责人
        assignee_chain = issue_data.get('assignee_chain', [])
        if assignee_chain:
            for github_id in assignee_chain:
                if github_id in github_id_to_name:
                    name = github_id_to_name[github_id]
                    logger.debug(f"Issue #{issue_data['issue_number']}: Timeline assignee {github_id} -> {name}")
                    return name
        
        # 优先级 3: Issue 的 label 映射
        issue_labels = issue_data.get('labels', [])
        if issue_labels:
            for label in issue_labels:
                if label in label_to_name:
                    name = label_to_name[label]
                    logger.debug(f"Issue #{issue_data['issue_number']}: Label {label} -> {name}")
                    return name
        
        # 优先级 4: 找不到 -> 返回 None
        logger.debug(f"Issue #{issue_data['issue_number']}: No assignee found, will use @所有人")
        return None
    
    def generate_issue_assignee_pairs_v2(
        self,
        analysis_data: List[Dict[str, Any]],
        github_id_to_name: Dict[str, str],
        label_to_name: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        生成 issue - assignee 映射 (新版本，使用四级优先级)
        
        Args:
            analysis_data: 分配分析结果
            github_id_to_name: GitHub ID -> 人名映射
            label_to_name: Label -> 负责人姓名映射
        
        Returns:
            issue-assignee 映射列表
        """
        pairs = []
        
        for issue in analysis_data:
            issue_number = issue['issue_number']
            issue_url = issue['issue_url']
            
            assignee_name = self.find_best_assignee(
                issue,
                github_id_to_name,
                label_to_name
            )
            
            if assignee_name:
                pairs.append({
                    'issue': f"#{issue_number}",
                    'issue_url': issue_url,
                    'assignee': assignee_name  # 直接使用人名，不再使用 GitHub ID
                })
            else:
                pairs.append({
                    'issue': f"#{issue_number}",
                    'issue_url': issue_url,
                    'assignee': issue_url  # 无负责人时使用 URL
                })
        
        return pairs
```

- [ ] **Step 2: 修改 generate 方法使用新逻辑**

修改 `WeLinkInformService.generate` 方法：

```python
def generate(self) -> str:
    """
    执行完整流程
    
    Returns:
        生成的文件路径
    """
    logger.info("=" * 60)
    logger.info("Starting WeLink Inform Generation")
    logger.info("=" * 60)
    
    analysis_data = self.load_assignment_analysis()
    
    if not analysis_data:
        logger.error("No data to process")
        return None
    
    # 加载两个映射
    if self.use_local:
        github_id_to_name = self.load_name_mapping_from_local()
        label_to_name = self.load_label_mapping_from_local()
    else:
        github_id_to_name = self.load_name_mapping_from_google_sheets()
        label_to_name = {}  # 暂不支持在线读取 label 映射
    
    logger.info(f"GitHub ID mappings: {len(github_id_to_name)}")
    logger.info(f"Label mappings: {len(label_to_name)}")
    
    pairs = self.generate_issue_assignee_pairs_v2(
        analysis_data,
        github_id_to_name,
        label_to_name
    )
    logger.info(f"Generated {len(pairs)} issue-assignee pairs")
    
    assignee_issues = self.merge_by_assignee(pairs)
    logger.info(f"Merged into {len(assignee_issues)} assignee groups")
    
    # 不再需要传入 name_mapping，因为 pairs 已经包含了人名
    content = self.generate_inform_content_v2(assignee_issues)
    
    file_path = self.save_inform_file(content)
    
    logger.info("=" * 60)
    logger.info("WeLink Inform Generation Completed")
    logger.info("=" * 60)
    
    return file_path
```

- [ ] **Step 3: 添加 generate_inform_content_v2 方法**

```python
def generate_inform_content_v2(
    self,
    assignee_issues: Dict[str, List[str]]
) -> str:
    """
    生成通知内容 (新版本)
    
    Args:
        assignee_issues: assignee (人名或 URL) -> issues 映射
    
    Returns:
        通知文本内容
    """
    lines = []
    
    assigned_lines = []
    unassigned_urls = []
    
    sorted_assignees = sorted(assignee_issues.keys())
    
    for assignee in sorted_assignees:
        issues = assignee_issues[assignee]
        
        issues_str = ", ".join(issues)
        
        # assignee 已经是人名或 URL
        if assignee.startswith('http'):
            unassigned_urls.extend(issues)
        else:
            assigned_lines.append(f"请@{assignee}，看下({issues_str})")
    
    lines.extend(assigned_lines)
    
    if unassigned_urls:
        lines.append("")
        urls_str = " ".join(unassigned_urls)
        lines.append(f"请@所有人 查看下：{urls_str}")
    
    return '\n'.join(lines)
```

---

## Task 5: 更新 Pipeline 传递 label 映射

**Files:**
- Modify: `src/pipeline.py`

- [ ] **Step 1: 修改 step3_analyze_assignment 方法**

修改 `Pipeline.step3_analyze_assignment` 方法：

```python
def step3_analyze_assignment(self, full_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    步骤3：分析分配链
    
    Args:
        full_report: 完整数据报告
    
    Returns:
        分配分析结果列表
    """
    log_step(logger, "Step 3", "Analyze assignment chain")
    
    loader = ConfigLoader()
    special_labels = loader.get_special_labels(self.config)
    
    # 加载 label 映射
    label_mapping_file = os.path.join(DATA_DIR, 'issue_label.json')
    label_mapping = {}
    if os.path.exists(label_mapping_file):
        with open(label_mapping_file, 'r', encoding='utf-8') as f:
            label_mapping = json.load(f)
        logger.info(f"Loaded {len(label_mapping)} label mappings")
    
    analyze_service = AnalyzeAssignmentService()
    results = analyze_service.generate_analysis_report(
        full_report,
        special_labels=special_labels,
        label_mapping=label_mapping
    )
    
    logger.info(f"Analyzed {len(results)} issues")
    
    return results
```

- [ ] **Step 2: 在文件开头添加必要的 import**

确保 `src/pipeline.py` 有：

```python
import json
import os
from typing import List, Dict, Any
```

---

## Task 6: 编写测试

**Files:**
- Create: `tests/test_assignee_rules.py`

- [ ] **Step 1: 创建负责人规则测试**

创建文件 `tests/test_assignee_rules.py`：

```python
"""
负责人规则修正测试
"""

import pytest
from unittest.mock import MagicMock, patch

from src.services.analyze_assignment import AnalyzeAssignmentService
from src.services.welink_inform import WeLinkInformService


class TestSpecialLabelDetection:
    """特殊 label 检测测试"""
    
    def test_special_label_detection(self):
        """测试检测特殊 label"""
        service = AnalyzeAssignmentService()
        
        issue_data = {
            'issue_number': 123,
            'issue_title': 'Test issue',
            'issue_url': 'https://github.com/test/test/issues/123',
            'state': 'open',
            'labels': ['triaged', 'gqa-model'],
            'comments': [],
            'assign_events': [],
            'mention_events': []
        }
        
        result = service.analyze_issue(
            issue_data,
            special_labels=['gqa-model', '310P'],
            label_mapping={'gqa-model': '负责人A'}
        )
        
        assert result['has_special_label'] == True
        assert result['special_label_assignee'] == '负责人A'
    
    def test_no_special_label(self):
        """测试无特殊 label"""
        service = AnalyzeAssignmentService()
        
        issue_data = {
            'issue_number': 124,
            'issue_title': 'Test issue 2',
            'issue_url': 'https://github.com/test/test/issues/124',
            'state': 'open',
            'labels': ['triaged', 'bug'],
            'comments': [],
            'assign_events': [],
            'mention_events': []
        }
        
        result = service.analyze_issue(
            issue_data,
            special_labels=['gqa-model', '310P'],
            label_mapping={'gqa-model': '负责人A'}
        )
        
        assert result['has_special_label'] == False
        assert result['special_label_assignee'] is None
    
    def test_multiple_special_labels(self):
        """测试多个特殊 label"""
        service = AnalyzeAssignmentService()
        
        issue_data = {
            'issue_number': 125,
            'issue_title': 'Test issue 3',
            'issue_url': 'https://github.com/test/test/issues/125',
            'state': 'open',
            'labels': ['triaged', 'gqa-model', '310P'],
            'comments': [],
            'assign_events': [],
            'mention_events': []
        }
        
        result = service.analyze_issue(
            issue_data,
            special_labels=['gqa-model', '310P'],
            label_mapping={'gqa-model': '负责人A', '310P': '负责人B'}
        )
        
        assert result['has_special_label'] == True
        # 应取第一个匹配的
        assert result['special_label_assignee'] == '负责人A'


class TestAssigneeChainPreservation:
    """负责人链路保留测试"""
    
    def test_assignee_chain_preservation(self):
        """测试保留完整负责人链路"""
        service = AnalyzeAssignmentService()
        
        issue_data = {
            'issue_number': 126,
            'issue_title': 'Test issue',
            'issue_url': 'https://github.com/test/test/issues/126',
            'state': 'open',
            'labels': ['triaged'],
            'comments': [
                {'author': 'user1', 'mentions': ['user2'], 'created_at': '2026-01-01T00:00:00Z', 'body': 'test'}
            ],
            'assign_events': [
                {'actor': 'user3', 'assignee': 'user4', 'created_at': '2026-01-02T00:00:00Z'}
            ],
            'mention_events': [
                {'by_commenter': 'user5', 'mentioned_users': ['user6'], 'created_at': '2026-01-03T00:00:00Z'}
            ]
        }
        
        result = service.analyze_issue(issue_data)
        
        # 应包含所有负责人
        assert 'user2' in result['assignee_chain']
        assert 'user4' in result['assignee_chain']
        assert 'user6' in result['assignee_chain']


class TestAssigneeMatchingPriority:
    """负责人匹配优先级测试"""
    
    def test_priority_1_special_label(self):
        """测试优先级 1: 特殊 label"""
        service = WeLinkInformService(use_local=True)
        
        issue_data = {
            'issue_number': 127,
            'has_special_label': True,
            'special_label_assignee': '负责人A',
            'assignee_chain': ['user1', 'user2'],
            'labels': ['triaged', 'gqa-model']
        }
        
        github_id_to_name = {'user1': '用户1', 'user2': '用户2'}
        label_to_name = {'gqa-model': '负责人A'}
        
        result = service.find_best_assignee(issue_data, github_id_to_name, label_to_name)
        
        # 应返回特殊 label 的负责人
        assert result == '负责人A'
    
    def test_priority_2_timeline_assignee(self):
        """测试优先级 2: 时间线负责人"""
        service = WeLinkInformService(use_local=True)
        
        issue_data = {
            'issue_number': 128,
            'has_special_label': False,
            'special_label_assignee': None,
            'assignee_chain': ['user1', 'user2'],
            'labels': ['triaged', 'bug']
        }
        
        github_id_to_name = {'user1': '用户1', 'user2': '用户2'}
        label_to_name = {}
        
        result = service.find_best_assignee(issue_data, github_id_to_name, label_to_name)
        
        # 应返回第一个能匹配的
        assert result == '用户1'
    
    def test_priority_3_label_mapping(self):
        """测试优先级 3: Label 映射"""
        service = WeLinkInformService(use_local=True)
        
        issue_data = {
            'issue_number': 129,
            'has_special_label': False,
            'special_label_assignee': None,
            'assignee_chain': ['unknown_user'],
            'labels': ['triaged', 'custom-label']
        }
        
        github_id_to_name = {}
        label_to_name = {'custom-label': '负责人B'}
        
        result = service.find_best_assignee(issue_data, github_id_to_name, label_to_name)
        
        # 应返回 label 映射的负责人
        assert result == '负责人B'
    
    def test_priority_4_no_match(self):
        """测试优先级 4: 无匹配"""
        service = WeLinkInformService(use_local=True)
        
        issue_data = {
            'issue_number': 130,
            'has_special_label': False,
            'special_label_assignee': None,
            'assignee_chain': ['unknown_user'],
            'labels': ['triaged', 'unknown-label']
        }
        
        github_id_to_name = {}
        label_to_name = {}
        
        result = service.find_best_assignee(issue_data, github_id_to_name, label_to_name)
        
        # 应返回 None
        assert result is None
```

- [ ] **Step 2: 运行测试**

Run: `python -m pytest tests/test_assignee_rules.py -v`
Expected: 所有测试通过

---

## Task 7: 验证和文档更新

**Files:**
- None (手动验证)

- [ ] **Step 1: 验证特殊 label 配置加载**

```bash
python -c "
from src.config.loader import ConfigLoader
loader = ConfigLoader()
config = loader.load('config.yaml')
special_labels = loader.get_special_labels(config)
print(f'Special labels: {special_labels}')
"
```
Expected: 输出 `['gqa-model', '310P']`

- [ ] **Step 2: 验证四级优先级逻辑**

创建测试数据验证完整流程：

```bash
# 1. 确保 issue_label.json 存在
echo '{"gqa-model": "负责人A", "310P": "负责人B"}' > data/issue_label.json

# 2. 确保 issue_assign.json 存在
echo '{"user1": "用户1", "user2": "用户2"}' > data/issue_assign.json

# 3. 运行 pipeline
python main.py
```
Expected: 生成的 welink_inform.txt 按正确优先级分配负责人

- [ ] **Step 3: 检查生成的报告格式**

```bash
cat data/assignment_analysis.json | python -m json.tool | head -50
```
Expected: 包含 `assignee_chain`, `has_special_label`, `special_label_assignee` 字段

---

## 自检清单

- [ ] 检查 spec 覆盖:
  - 特殊 label 直接分配: ✓ Task 4 (优先级1)
  - 保留时间线全部负责人: ✓ Task 3
  - Excel 匹配失败使用 label: ✓ Task 4 (优先级3)
  - 最终关联流程: ✓ Task 4 (四级优先级)
  - 配置特殊 label: ✓ Task 1

- [ ] 检查类型一致性:
  - `special_labels` 在各方法中都是 `List[str]`
  - `label_mapping` 在各方法中都是 `Dict[str, str]`
  - `assignee_chain` 是 `List[str]`
  - `has_special_label` 是 `bool`
  - `special_label_assignee` 是 `Optional[str]`

- [ ] 检查无占位符:
  - 所有代码块完整
  - 无 "TODO" 或 "TBD"

- [ ] 检查依赖:
  - Issue #1 的 `issue_label.json` 文件
  - 如 Issue #1 未完成，需先手动创建该文件