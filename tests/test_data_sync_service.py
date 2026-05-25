"""
数据同步服务测试
"""

import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from src.services.data_sync_service import DataSyncService, sync_data_from_google_sheets


class TestDataSyncService:
    """DataSyncService 测试类"""
    
    def test_init(self):
        """测试初始化"""
        service = DataSyncService(
            excel_url="https://docs.google.com/spreadsheets/d/test",
            excel_gid="123"
        )
        assert service.excel_url == "https://docs.google.com/spreadsheets/d/test"
        assert service.excel_gid == "123"
    
    def test_init_default_gid(self):
        """测试默认 GID"""
        service = DataSyncService(
            excel_url="https://docs.google.com/spreadsheets/d/test"
        )
        assert service.excel_gid == "0"
    
    @patch('src.services.data_sync_service.GoogleSheetsReader')
    def test_sync_success(self, mock_reader_class):
        """测试同步成功"""
        mock_reader = MagicMock()
        mock_reader.build_all_mappings.return_value = (
            {
                "user1": {"name": "用户1", "employee_id": "12345"},
                "user2": {"name": "用户2", "employee_id": "67890"}
            },
            {"label1": "负责人1", "label2": "负责人2"}
        )
        mock_reader_class.return_value = mock_reader
        
        with tempfile.TemporaryDirectory() as tmpdir:
            import src.services.data_sync_service as sync_module
            original_data_dir = sync_module.DATA_DIR
            sync_module.DATA_DIR = tmpdir
            
            try:
                service = DataSyncService(
                    excel_url="https://docs.google.com/spreadsheets/d/test",
                    excel_gid="123"
                )
                result = service.sync()
                
                assert result['assign_count'] == 2
                assert result['label_count'] == 2
                
                assign_file = os.path.join(tmpdir, 'issue_assign.json')
                label_file = os.path.join(tmpdir, 'issue_label.json')
                
                assert os.path.exists(assign_file)
                assert os.path.exists(label_file)
                
                with open(assign_file, 'r', encoding='utf-8') as f:
                    assign_data = json.load(f)
                assert assign_data["user1"]["name"] == "用户1"
                assert assign_data["user1"]["employee_id"] == "12345"
                assert assign_data["user2"]["name"] == "用户2"
                assert assign_data["user2"]["employee_id"] == "67890"
                
                with open(label_file, 'r', encoding='utf-8') as f:
                    label_data = json.load(f)
                assert label_data == {"label1": "负责人1", "label2": "负责人2"}
            finally:
                sync_module.DATA_DIR = original_data_dir
    
    def test_sync_no_url(self):
        """测试无 URL 时同步"""
        service = DataSyncService(excel_url=None)
        result = service.sync()
        
        assert result['assign_count'] == 0
        assert result['label_count'] == 0
    
    @patch('src.services.data_sync_service.DataSyncService')
    def test_sync_data_from_google_sheets(self, mock_service_class):
        """测试便捷函数"""
        mock_service = MagicMock()
        mock_service.sync.return_value = {'assign_count': 5, 'label_count': 3}
        mock_service_class.return_value = mock_service
        
        result = sync_data_from_google_sheets(
            excel_url="https://docs.google.com/spreadsheets/d/test",
            excel_gid="456"
        )
        
        mock_service_class.assert_called_once_with(
            "https://docs.google.com/spreadsheets/d/test",
            "456"
        )
        assert result == {'assign_count': 5, 'label_count': 3}