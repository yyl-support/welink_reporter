"""
WeLink 通知服务测试

测试 WeLinkInformService 的各项功能。
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.services.welink_inform import WeLinkInformService


class TestWeLinkInformService:
    """WeLinkInformService 测试类"""
    
    def test_init_with_config(self):
        """测试带配置初始化"""
        service = WeLinkInformService(
            excel_url="https://docs.google.com/spreadsheets/d/abc123/edit",
            excel_gid="gid123"
        )
        assert service.excel_url == "https://docs.google.com/spreadsheets/d/abc123/edit"
        assert service.excel_gid == "gid123"
    
    def test_init_without_config(self):
        """测试不带配置初始化"""
        service = WeLinkInformService()
        assert service.excel_url is None
        assert service.excel_gid == '0'
    
    def test_load_assignment_analysis(self):
        """测试加载分配分析数据"""
        test_data = [
            {"issue_number": 1, "issue_url": "url1", "final_assignee": "user1"},
            {"issue_number": 2, "issue_url": "url2", "final_assignee": "user2"}
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, 'assignment_analysis.json')
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f)
            
            service = WeLinkInformService()
            
            with patch.object(WeLinkInformService, '__module__', 'src.services.welink_inform'):
                with patch('src.services.welink_inform.DATA_DIR', tmpdir):
                    data = service.load_assignment_analysis()
            
            assert len(data) == 2
            assert data[0]['issue_number'] == 1
    
    def test_generate_issue_assignee_pairs(self):
        """测试生成 issue-assignee 映射"""
        analysis_data = [
            {"issue_number": 1, "issue_url": "url1", "final_assignee": "user1"},
            {"issue_number": 2, "issue_url": "url2", "final_assignee": None}
        ]
        
        service = WeLinkInformService()
        pairs = service.generate_issue_assignee_pairs(analysis_data)
        
        assert len(pairs) == 2
        assert pairs[0]['assignee'] == "user1"
        assert pairs[1]['assignee'] == "url2"
    
    def test_merge_by_assignee(self):
        """测试按 assignee 合并"""
        pairs = [
            {"assignee": "user1", "issue": "#1"},
            {"assignee": "user1", "issue": "#2"},
            {"assignee": "user2", "issue": "#3"}
        ]
        
        service = WeLinkInformService()
        merged = service.merge_by_assignee(pairs)
        
        assert len(merged) == 2
        assert merged['user1'] == ['#1', '#2']
        assert merged['user2'] == ['#3']
    
    def test_generate_inform_content_with_assignees(self):
        """测试生成通知内容（有负责人）"""
        assignee_issues = {
            "user1": ["url1", "url2"],
            "user2": ["url3"]
        }
        name_mapping = {
            "user1": "user1",
            "user2": "user2"
        }
        
        service = WeLinkInformService()
        content = service.generate_inform_content(assignee_issues, name_mapping)
        
        assert "请@user1，看下(url1, url2)" in content
        assert "请@user2，看下(url3)" in content
    
    def test_generate_inform_content_with_unassigned(self):
        """测试生成通知内容（有未分配）"""
        assignee_issues = {
            "http://issue1": ["#1"],
            "http://issue2": ["#2"]
        }
        name_mapping = {}
        
        service = WeLinkInformService()
        content = service.generate_inform_content(assignee_issues, name_mapping)
        
        assert "请@所有人 查看下：" in content
    
    def test_generate_inform_content_no_mapping(self):
        """测试生成通知内容（无映射）"""
        assignee_issues = {
            "unknown_user": ["url1"]
        }
        name_mapping = {}
        
        service = WeLinkInformService()
        content = service.generate_inform_content(assignee_issues, name_mapping)
        
        assert "请@unknown_user，看下(url1)" in content
    
    def test_load_name_mapping_without_url(self):
        """测试无 URL 时加载映射"""
        service = WeLinkInformService()
        mapping = service.load_name_mapping_from_google_sheets()
        
        assert mapping == {}