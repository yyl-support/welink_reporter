"""
数据同步服务模块

负责从 Google Sheets 同步数据到本地 JSON 文件。
"""

import json
import os
from typing import Dict, Any
from src.utils.logger import get_logger
from src.services.excel_reader import GoogleSheetsReader

logger = get_logger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')


class DataSyncService:
    """
    数据同步服务
    
    从 Google Sheets 读取数据并保存到本地 JSON 文件。
    
    Example:
        service = DataSyncService(excel_url, excel_gid)
        service.sync()
    """
    
    def __init__(self, excel_url: str, excel_gid: str = '0'):
        """
        初始化数据同步服务
        
        Args:
            excel_url: Google Sheets URL
            excel_gid: Google Sheets GID
        """
        self.excel_url = excel_url
        self.excel_gid = excel_gid
        logger.info("DataSyncService initialized")
    
    def sync(self) -> Dict[str, Any]:
        """
        执行数据同步
        
        从 Google Sheets 读取数据，保存到本地 JSON 文件。
        
        Returns:
            同步结果统计:
            - assign_count: GitHub ID 映射数量
            - label_count: Label 映射数量
        """
        logger.info("=" * 60)
        logger.info("Starting Data Sync from Google Sheets")
        logger.info("=" * 60)
        
        if not self.excel_url:
            logger.error("No Excel URL provided, sync aborted")
            return {'assign_count': 0, 'label_count': 0}
        
        reader = GoogleSheetsReader(self.excel_url, self.excel_gid)
        
        github_id_to_name, label_to_name = reader.build_all_mappings()
        reader.close()
        
        assign_file = os.path.join(DATA_DIR, 'issue_assign.json')
        label_file = os.path.join(DATA_DIR, 'issue_label.json')
        
        with open(assign_file, 'w', encoding='utf-8') as f:
            json.dump(github_id_to_name, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(github_id_to_name)} GitHub ID mappings to {assign_file}")
        
        with open(label_file, 'w', encoding='utf-8') as f:
            json.dump(label_to_name, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(label_to_name)} Label mappings to {label_file}")
        
        logger.info("=" * 60)
        logger.info("Data Sync Completed")
        logger.info("=" * 60)
        
        return {
            'assign_count': len(github_id_to_name),
            'label_count': len(label_to_name)
        }


def sync_data_from_google_sheets(excel_url: str, excel_gid: str = '0') -> Dict[str, Any]:
    """
    便捷函数：从 Google Sheets 同步数据
    
    Args:
        excel_url: Google Sheets URL
        excel_gid: Google Sheets GID
    
    Returns:
        同步结果统计
    """
    service = DataSyncService(excel_url, excel_gid)
    return service.sync()