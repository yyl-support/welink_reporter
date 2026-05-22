"""
生成 WeLink 通知文件服务模块

从 assignment_analysis.json 生成 welink_inform.txt。
"""

import json
import os
from typing import Dict, List, Any, Optional
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
    
    def __init__(self, excel_url: str = None, excel_gid: str = None, use_local: bool = True):
        """
        初始化服务
        
        Args:
            excel_url: Google Sheets URL
            excel_gid: Google Sheets GID
            use_local: 是否使用本地数据（默认 True）
        """
        self.excel_url = excel_url
        self.excel_gid = excel_gid or '0'
        self.use_local = use_local
        logger.info(f"WeLinkInformService initialized (use_local={use_local})")
    
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

    def load_name_mapping_from_local(self) -> Dict[str, str]:
        """
        从本地 JSON 文件加载 GitHub ID -> 人名映射
        
        Returns:
            GitHub ID -> 人名 的字典
        """
        file_path = os.path.join(DATA_DIR, 'issue_assign.json')
        
        if not os.path.exists(file_path):
            logger.warning(f"Local mapping file not found: {file_path}")
            return {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        logger.info(f"Loaded {len(mapping)} person mappings from local file")
        return mapping

    def load_label_mapping_from_local(self) -> Dict[str, str]:
        """
        从本地 JSON 文件加载 Label -> 负责人映射
        
        Returns:
            Label -> 负责人姓名 的字典
        """
        file_path = os.path.join(DATA_DIR, 'issue_label.json')
        
        if not os.path.exists(file_path):
            logger.warning(f"Local label mapping file not found: {file_path}")
            return {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        logger.info(f"Loaded {len(mapping)} label mappings from local file")
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
        if issue_data.get('has_special_label') and issue_data.get('special_label_assignee'):
            special_assignee = issue_data['special_label_assignee']
            logger.debug(f"Issue #{issue_data['issue_number']}: Special label assignee -> {special_assignee}")
            return special_assignee
        
        assignee_chain = issue_data.get('assignee_chain', [])
        if assignee_chain:
            for github_id in assignee_chain:
                if github_id in github_id_to_name:
                    name = github_id_to_name[github_id]
                    logger.debug(f"Issue #{issue_data['issue_number']}: Timeline assignee {github_id} -> {name}")
                    return name
        
        issue_labels = issue_data.get('labels', [])
        if issue_labels:
            for label in issue_labels:
                if label in label_to_name:
                    name = label_to_name[label]
                    logger.debug(f"Issue #{issue_data['issue_number']}: Label {label} -> {name}")
                    return name
        
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
                    'assignee': assignee_name
                })
            else:
                pairs.append({
                    'issue': f"#{issue_number}",
                    'issue_url': issue_url,
                    'assignee': issue_url
                })
        
        return pairs
    
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
        
        if self.use_local:
            github_id_to_name = self.load_name_mapping_from_local()
            label_to_name = self.load_label_mapping_from_local()
        else:
            github_id_to_name = self.load_name_mapping_from_google_sheets()
            label_to_name = {}
        
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
        
        content = self.generate_inform_content_v2(assignee_issues)
        
        file_path = self.save_inform_file(content)
        
        logger.info("=" * 60)
        logger.info("WeLink Inform Generation Completed")
        logger.info("=" * 60)
        
        return file_path