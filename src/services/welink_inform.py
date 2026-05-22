"""
生成 WeLink 通知文件服务模块

从 assignment_analysis.json 生成 welink_inform.txt。
"""

import json
import os
from typing import Dict, List, Any
from collections import defaultdict
from ..utils.logger import get_logger
from .excel_reader import GoogleSheetsReader

logger = get_logger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')


class WeLinkInformService:
    """
    WeLink 通知生成服务
    
    从 assignment_analysis.json 生成 welink_inform.txt 文件。
    
    流程：
    1. 生成 issue - final_assignee 映射
    2. 合并相同 assignee 的 issues
    3. 从 Google Sheets 查找 GitHub ID 对应的人名
    4. 输出 welink_inform.txt
    
    Example:
        service = WeLinkInformService(excel_url, excel_gid)
        service.generate()
    """
    
    def __init__(self, excel_url: str = None, excel_gid: str = None):
        """
        初始化服务
        
        Args:
            excel_url: Google Sheets URL
            excel_gid: Google Sheets GID
        """
        self.excel_url = excel_url
        self.excel_gid = excel_gid or '0'
        logger.info("WeLinkInformService initialized")
    
    def load_name_mapping_from_google_sheets(self) -> Dict[str, str]:
        """
        从 Google Sheets 加载 GitHub ID -> 人名映射
        
        Returns:
            GitHub ID -> 人名 的字典
        """
        if not self.excel_url:
            logger.warning("No Excel URL provided, using empty mapping")
            return {}
        
        logger.info(f"Reading Google Sheets: {self.excel_url}")
        reader = GoogleSheetsReader(self.excel_url, self.excel_gid)
        mapping = reader.build_github_id_to_name_map()
        reader.close()
        logger.info(f"Loaded {len(mapping)} person mappings from Google Sheets")
        
        return mapping
    
    def load_assignment_analysis(self) -> List[Dict[str, Any]]:
        """
        加载 assignment_analysis.json
        
        Returns:
            分配分析结果列表
        """
        file_path = os.path.join(DATA_DIR, 'assignment_analysis.json')
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} issues from assignment_analysis.json")
        
        return data
    
    def generate_issue_assignee_pairs(
        self,
        analysis_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        生成 issue - final_assignee 映射
        
        Args:
            analysis_data: 分配分析结果
        
        Returns:
            issue-assignee 映射列表
        """
        pairs = []
        
        for issue in analysis_data:
            issue_number = issue['issue_number']
            issue_url = issue['issue_url']
            final_assignee = issue['final_assignee']
            
            if final_assignee:
                pairs.append({
                    'issue': f"#{issue_number}",
                    'issue_url': issue_url,
                    'assignee': final_assignee
                })
            else:
                pairs.append({
                    'issue': f"#{issue_number}",
                    'issue_url': issue_url,
                    'assignee': issue_url
                })
        
        return pairs
    
    def merge_by_assignee(
        self,
        pairs: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        按 assignee 合并 issues
        
        Args:
            pairs: issue-assignee 映射列表
        
        Returns:
            assignee -> issues 列表 的字典
        """
        assignee_issues = defaultdict(list)
        
        for pair in pairs:
            assignee = pair['assignee']
            issue_url = pair['issue_url']
            assignee_issues[assignee].append(issue_url)
        
        return assignee_issues
    
    def generate_inform_content(
        self,
        assignee_issues: Dict[str, List[str]],
        name_mapping: Dict[str, str]
    ) -> str:
        """
        生成通知内容
        
        Args:
            assignee_issues: assignee -> issues 映射
            name_mapping: GitHub ID -> 人名 映射
        
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
            
            display_name = name_mapping.get(assignee, assignee)
            
            if assignee.startswith('http'):
                unassigned_urls.extend(issues)
            else:
                assigned_lines.append(f"请@{display_name}，看下({issues_str})")
        
        lines.extend(assigned_lines)
        
        if unassigned_urls:
            lines.append("")
            urls_str = " ".join(unassigned_urls)
            lines.append(f"请@所有人 查看下：{urls_str}")
        
        return '\n'.join(lines)
    
    def save_inform_file(self, content: str) -> str:
        """
        保存通知文件
        
        Args:
            content: 通知内容
        
        Returns:
            文件路径
        """
        file_path = os.path.join(DATA_DIR, 'welink_inform.txt')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Saved inform file to: {file_path}")
        
        return file_path
    
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
        
        pairs = self.generate_issue_assignee_pairs(analysis_data)
        logger.info(f"Generated {len(pairs)} issue-assignee pairs")
        
        assignee_issues = self.merge_by_assignee(pairs)
        logger.info(f"Merged into {len(assignee_issues)} assignee groups")
        
        name_mapping = self.load_name_mapping_from_google_sheets()
        
        content = self.generate_inform_content(assignee_issues, name_mapping)
        
        file_path = self.save_inform_file(content)
        
        logger.info("=" * 60)
        logger.info("WeLink Inform Generation Completed")
        logger.info("=" * 60)
        
        return file_path