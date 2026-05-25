"""
主流程编排模块

协调各服务模块完成完整的 Issue 分配分析流程。
"""

import json
import os
from typing import List, Dict, Any

from src.config.loader import ConfigLoader
from src.models.issue import IssueInfo
from src.services.parser import IssueParser
from src.services.fetch_full_data import FetchFullDataService
from src.services.analyze_assignment import AnalyzeAssignmentService
from src.services.welink_inform import WeLinkInformService
from src.services.send_msg import send_msg
from src.utils.logger import get_logger, log_step

logger = get_logger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')


class Pipeline:
    """
    分析流程编排器
    
    协调各个服务模块完成完整的 Issue 分配分析流程：
    1. 解析 Issue 数据
    2. 获取完整数据（comments + timeline）
    3. 分析分配链和负责人信息
    4. 生成最终报告 (assignment_analysis.json)
    5. 生成 WeLink 通知文件 (welink_inform.txt)
    
    Example:
        pipeline = Pipeline(config_path="config.yaml")
        pipeline.run()
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化流程编排器
        
        Args:
            config_path: 配置文件路径，如果不提供则使用默认配置
        """
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..',
            'config.yaml'
        )
        self.config: Dict[str, Any] = None
        
        logger.info("Pipeline initialized")
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置
        
        Returns:
            配置字典
        """
        log_step(logger, "Loading Configuration")
        
        loader = ConfigLoader()
        
        if os.path.exists(self.config_path):
            self.config = loader.load(self.config_path)
        else:
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            self.config = {
                'filters': {
                    'lookback_days': 2
                },
                'github': {
                    'repo': 'vllm-project/vllm-ascend'
                },
                'excel': {
                    'url': None,
                    'gid': '0'
                }
            }
        
        return self.config
    
    def step1_parse_issues(self) -> List[IssueInfo]:
        """
        步骤1：解析 Issue 数据
        
        Returns:
            筛选后的 IssueInfo 列表
        """
        log_step(logger, "Step 1", "Parse triaged issues")
        
        repo = self.config.get('github', {}).get('repo', 'vllm-project/vllm-ascend')
        lookback_days = self.config.get('filters', {}).get('lookback_days', 2)
        
        parser = IssueParser(repo=repo, lookback_days=lookback_days)
        issues = parser.parse()
        
        logger.info(f"Found {len(issues)} triaged issues")
        
        return issues
    
    def step2_fetch_full_data(self, issues: List[IssueInfo]) -> Dict[str, Any]:
        """
        步骤2：获取完整数据
        
        Args:
            issues: IssueInfo 列表
        
        Returns:
            完整数据报告（包含 comments, label_events, mention_events, assign_events）
        """
        log_step(logger, "Step 2", "Fetch full data (comments + timeline)")
        
        repo = self.config.get('github', {}).get('repo', 'vllm-project/vllm-ascend')
        lookback_days = self.config.get('filters', {}).get('lookback_days', 2)
        
        fetch_service = FetchFullDataService(repo=repo, lookback_days=lookback_days)
        full_report = fetch_service.fetch_full_data(issues)
        
        output_path = os.path.join(DATA_DIR, 'full_issue_report.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Full data saved to: {output_path}")
        
        return full_report
    
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
    
    def step4_generate_report(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        步骤4：生成最终报告
        
        输出 assignment_analysis.json，包含分配链、最终负责人、流程图等信息。
        
        Args:
            results: 分配分析结果列表
        
        Returns:
            最终报告数据
        """
        log_step(logger, "Step 4", "Generate assignment analysis report")
        
        output_path = os.path.join(DATA_DIR, 'assignment_analysis.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Report saved to: {output_path}")
        
        return results
    
    def step5_generate_welink_inform(self, use_local: bool = True) -> str:
        """
        步骤5：生成 WeLink 通知文件
        
        Args:
            use_local: 是否使用本地数据（默认 True）
        
        Returns:
            生成的文件路径
        """
        log_step(logger, "Step 5", "Generate WeLink inform file")
        
        loader = ConfigLoader()
        excel_url = loader.get_excel_url(self.config)
        excel_gid = loader.get_excel_gid(self.config)
        
        welink_service = WeLinkInformService(
            excel_url=excel_url,
            excel_gid=excel_gid,
            use_local=use_local
        )
        output_path = welink_service.generate()
        
        logger.info(f"WeLink inform file saved to: {output_path}")
        
        return output_path
    
    def step6_send_welink_message(self) -> None:
        """
        步骤6：发送 WeLink 消息
        
        读取 welink_inform.txt 并发送消息
        """
        log_step(logger, "Step 6", "Send WeLink message")
        
        inform_path = os.path.join(DATA_DIR, 'welink_inform.txt')
        with open(inform_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        auth = self.config.get('welink', {}).get('auth', '')
        receiver_uid = self.config.get('welink', {}).get('receiver_uid', '')
        
        if not auth or not receiver_uid:
            logger.warning("WeLink auth or receiver_uid not configured, skipping message sending")
            return
        
        send_msg(content, receiver_uid, auth)
        logger.info("WeLink message sent successfully")
    
    def run(self) -> List[Dict[str, Any]]:
        """
        运行完整流程
        
        Returns:
            最终报告数据
        """
        logger.info("=" * 60)
        logger.info("STARTING ISSUE ASSIGNMENT ANALYSIS PIPELINE")
        logger.info("=" * 60)
        
        self.load_config()
        
        issues = self.step1_parse_issues()
        
        if not issues:
            logger.warning("No triaged issues found, pipeline terminated")
            return []
        
        full_report = self.step2_fetch_full_data(issues)
        results = self.step3_analyze_assignment(full_report)
        report = self.step4_generate_report(results)
        self.step5_generate_welink_inform()
        self.step6_send_welink_message()
        
        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
        return report