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
        
        assert result is None