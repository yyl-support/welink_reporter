"""
分配分析服务模块

负责从完整 Issue 数据中分析任务分配链。
"""

from typing import List, Dict, Any, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AnalyzeAssignmentService:
    """
    分配分析服务
    
    从完整 Issue 数据中分析任务分配流程，提取分配链和最终负责人。
    
    Example:
        service = AnalyzeAssignmentService()
        analysis = service.analyze_assignment(issue_data)
        result = service.generate_analysis_report(full_report)
    """
    
    def __init__(self):
        """初始化分配分析服务"""
        logger.info("AnalyzeAssignmentService initialized")
    
    def analyze_task_assignment(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析 Issue 的任务分配流程
        
        Args:
            issue_data: Issue 完整数据（包含 comments, label_events, mention_events, assign_events）
        
        Returns:
            分析结果：
            - assignment_chain: 分配链列表
            - final_assignee: 最终负责人
            - has_formal_assignment: 是否有正式分配
        """
        assignment_chain = []
        formal_assignees = []
        
        comments = issue_data.get('comments', [])
        assign_events = issue_data.get('assign_events', [])
        mention_events = issue_data.get('mention_events', [])
        
        for event in assign_events:
            formal_assignees.append({
                'assignee': event.get('assignee'),
                'actor': event.get('actor'),
                'time': event.get('created_at')
            })
            assignment_chain.append({
                'from': event.get('actor'),
                'to': event.get('assignee'),
                'method': 'formal_assignment',
                'time': event.get('created_at'),
                'comment': None
            })
        
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
            'final_assignee': final_assignee,
            'has_formal_assignment': len(formal_assignees) > 0
        }
    
    def generate_flow_diagram(self, chain: List[Dict[str, Any]]) -> str:
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
            method = item['method']
            from_user = item['from']
            to_user = item['to']
            comment = item.get('comment', '')
            
            if method == 'mention':
                safe_comment = ''.join(c if ord(c) < 65536 else '?' for c in str(comment))
                comment_preview = safe_comment[:50].replace('\n', ' ') if safe_comment else ''
                lines.append(f"{from_user} -> {to_user} (via @{to_user}: \"{comment_preview}...\")")
            else:
                lines.append(f"{from_user} -> {to_user} (formal assignment)")
        
        return '\n'.join(lines)
    
    def analyze_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析单个 Issue 的分配情况
        
        Args:
            issue_data: Issue 完整数据
        
        Returns:
            分配分析结果
        """
        analysis = self.analyze_task_assignment(issue_data)
        flow_diagram = self.generate_flow_diagram(analysis['assignment_chain'])
        
        return {
            'issue_number': issue_data['issue_number'],
            'issue_title': issue_data['issue_title'],
            'issue_url': issue_data['issue_url'],
            'state': issue_data['state'],
            'assignment_chain': analysis['assignment_chain'],
            'final_assignee': analysis['final_assignee'],
            'has_formal_assignment': analysis['has_formal_assignment'],
            'flow_diagram': flow_diagram
        }
    
    def generate_analysis_report(self, full_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        批量分析 Issue 分配情况
        
        Args:
            full_report: 完整数据报告
        
        Returns:
            分配分析报告列表
        """
        issues = full_report.get('issues', [])
        
        logger.info(f"Analyzing assignment for {len(issues)} issues")
        
        results = []
        for issue in issues:
            result = self.analyze_issue(issue)
            results.append(result)
        
        self._log_analysis_summary(results)
        
        return results
    
    def _log_analysis_summary(self, results: List[Dict[str, Any]]):
        """
        打印分析汇总
        
        Args:
            results: 分析结果列表
        """
        assigned_issues = [r for r in results if r['final_assignee']]
        unassigned_issues = [r for r in results if not r['final_assignee']]
        
        logger.info("=" * 60)
        logger.info("ISSUE ASSIGNMENT ANALYSIS REPORT")
        logger.info("=" * 60)
        logger.info(f"Total issues analyzed: {len(results)}")
        logger.info(f"Issues with assignment: {len(assigned_issues)}")
        logger.info(f"Issues without assignment: {len(unassigned_issues)}")
        
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
        
        if unassigned_issues:
            logger.info("-" * 60)
            logger.info("UNASSIGNED ISSUES")
            logger.info("-" * 60)
            for r in unassigned_issues:
                title_preview = r['issue_title'][:50] if r['issue_title'] else ''
                logger.info(f"#{r['issue_number']}: {title_preview}...")
                logger.info(f"  State: {r['state']}")
                logger.info("  No assignment found (triaged but not assigned to anyone)")