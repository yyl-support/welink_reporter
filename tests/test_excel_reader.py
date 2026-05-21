"""
Google Sheets 读取器测试

测试 ExcelReader 的各项功能。
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from services.excel_reader import GoogleSheetsReader, PersonInfo, extract_name_and_github_id


class TestPersonInfo:
    """PersonInfo 数据类测试"""
    
    def test_person_info_creation(self):
        """测试 PersonInfo 创建"""
        person = PersonInfo(name="zhangsan", github_id="zhangsan")
        assert person.name == "zhangsan"
        assert person.github_id == "zhangsan"


class TestExtractNameAndGithubId:
    """extract_name_and_github_id 函数测试"""
    
    def test_extract_with_chinese_paren(self):
        """测试中文括号格式"""
        result = extract_name_and_github_id("zhangsan(zhangsan)")
        assert result is not None
        assert result.name == "zhangsan"
        assert result.github_id == "zhangsan"
    
    def test_extract_with_english_paren(self):
        """测试英文括号格式"""
        result = extract_name_and_github_id("lisi(lisi)")
        assert result is not None
        assert result.name == "lisi"
        assert result.github_id == "lisi"
    
    def test_extract_empty_text(self):
        """测试空文本"""
        result = extract_name_and_github_id("")
        assert result is None
    
    def test_extract_none_text(self):
        """测试 None"""
        result = extract_name_and_github_id(None)
        assert result is None
    
    def test_extract_invalid_format(self):
        """测试无效格式"""
        result = extract_name_and_github_id("wangwu")
        assert result is None


class TestGoogleSheetsReader:
    """GoogleSheetsReader 测试类"""
    
    def test_build_csv_url(self):
        """测试构建 CSV URL"""
        reader = GoogleSheetsReader(
            "https://docs.google.com/spreadsheets/d/abc123/edit",
            "gid123"
        )
        expected_url = "https://docs.google.com/spreadsheets/d/abc123/export?format=csv&gid=gid123"
        assert reader._csv_url == expected_url
    
    def test_invalid_url_raises_error(self):
        """测试无效 URL 抛出异常"""
        with pytest.raises(ValueError):
            GoogleSheetsReader("https://invalid-url.com", "gid123")
    
    @patch('services.excel_reader.requests.get')
    def test_fetch_csv(self, mock_get):
        """测试获取 CSV 数据"""
        mock_response = Mock()
        mock_response.content = b"name,github_id\nuser1,zhangsan\nuser2,lisi"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        reader = GoogleSheetsReader(
            "https://docs.google.com/spreadsheets/d/abc123/edit",
            "gid123"
        )
        rows = reader._fetch_csv()
        
        assert len(rows) == 3
        assert rows[0] == ['name', 'github_id']
        assert rows[1] == ['user1', 'zhangsan']
    
    @patch('services.excel_reader.requests.get')
    def test_read_persons_from_column_d(self, mock_get):
        """测试从 D 列读取人员信息"""
        csv_content = "col1,col2,col3,assignee\n".encode('utf-8')
        csv_content += "data1,data2,data3,user1(zhangsan)\n".encode('utf-8')
        csv_content += "data4,data5,data6,user2(lisi)\n".encode('utf-8')
        csv_content += "data7,data8,data9,user3(wangwu)".encode('utf-8')
        
        mock_response = Mock()
        mock_response.content = csv_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        reader = GoogleSheetsReader(
            "https://docs.google.com/spreadsheets/d/abc123/edit",
            "gid123"
        )
        persons = reader.read_persons_from_column_d()
        
        assert len(persons) == 3
        assert persons[0].github_id == "zhangsan"
        assert persons[1].github_id == "lisi"
    
    @patch('services.excel_reader.requests.get')
    def test_build_github_id_to_name_map(self, mock_get):
        """测试构建 GitHub ID 到人名的映射"""
        csv_content = "col1,col2,col3,assignee\n".encode('utf-8')
        csv_content += "data1,data2,data3,user1(zhangsan)\n".encode('utf-8')
        csv_content += "data4,data5,data6,user2(lisi)".encode('utf-8')
        
        mock_response = Mock()
        mock_response.content = csv_content
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        reader = GoogleSheetsReader(
            "https://docs.google.com/spreadsheets/d/abc123/edit",
            "gid123"
        )
        mapping = reader.build_github_id_to_name_map()
        
        assert 'zhangsan' in mapping
        assert 'lisi' in mapping
    
    def test_close(self):
        """测试关闭方法"""
        reader = GoogleSheetsReader(
            "https://docs.google.com/spreadsheets/d/abc123/edit",
            "gid123"
        )
        reader.close()