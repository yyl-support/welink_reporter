import csv
import io
import re
from dataclasses import dataclass
from typing import Optional, List

import requests


@dataclass
class PersonInfo:
    name: str
    github_id: str
    employee_id: Optional[str] = None


def extract_name_and_github_id(text: str) -> Optional[PersonInfo]:
    if not text:
        return None
    
    text = str(text).strip()
    pattern = r'^(.+?)[（(]([^()（）]+)[）)]$'
    match = re.match(pattern, text)
    if match:
        name = match.group(1).strip()
        github_id = match.group(2).strip()
        if name and github_id:
            return PersonInfo(name=name, github_id=github_id)
    return None


class GoogleSheetsReader:
    def __init__(self, sheet_url: str, gid: str):
        self.sheet_url = sheet_url
        self.gid = gid
        self._csv_url = self._build_csv_url()
        self._rows = None

    def _build_csv_url(self) -> str:
        pattern = r'/d/([a-zA-Z0-9_-]+)/'
        match = re.search(pattern, self.sheet_url)
        if not match:
            raise ValueError(f"Invalid Google Sheets URL: {self.sheet_url}")
        sheet_id = match.group(1)
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={self.gid}"

    def _fetch_csv(self) -> list[list[str]]:
        response = requests.get(self._csv_url, timeout=30, verify=False)
        response.raise_for_status()
        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        return list(reader)

    def read_persons_from_column_d(self) -> List[PersonInfo]:
        if self._rows is None:
            self._rows = self._fetch_csv()
        
        persons = []
        seen = set()
        for row in self._rows[1:]:
            if len(row) < 4:
                continue
            value = row[3]
            if not value or not value.strip():
                continue
            
            value = value.strip()
            
            person = self._parse_person_value(value)
            if person and person.github_id not in seen:
                persons.append(person)
                seen.add(person.github_id)
        
        return persons
    
    def _parse_person_value(self, value: str) -> Optional[PersonInfo]:
        pattern_with_parens = r'[（(]([a-zA-Z0-9_-]+)[）)]'
        matches = re.findall(pattern_with_parens, value)
        
        if matches:
            name_pattern = r'^([^（(]+)'
            name_match = re.match(name_pattern, value)
            name_part = name_match.group(1).strip() if name_match else ""
            
            employee_id_match = re.search(r'(\d{6,8})', name_part)
            employee_id = employee_id_match.group(1) if employee_id_match else None
            
            name = re.sub(r'\d+', '', name_part).strip()
            name = name.replace('\n', ' ').strip()
            
            for github_id in matches:
                if github_id and name:
                    return PersonInfo(name=name, github_id=github_id, employee_id=employee_id)
        
        pattern_without_parens = r'^([^\d]+?)\s+(\d+)?\s*([a-zA-Z][a-zA-Z0-9_-]*)$'
        match = re.match(pattern_without_parens, value)
        if match:
            name = match.group(1).strip()
            name = name.replace('\n', ' ').strip()
            employee_id = match.group(2) if match.group(2) else None
            github_id = match.group(3)
            if name and github_id:
                return PersonInfo(name=name, github_id=github_id, employee_id=employee_id)
        
        return None

    def build_github_id_to_name_map(self) -> dict[str, str]:
        return {p.github_id: p.name for p in self.read_persons_from_column_d()}
    
    def build_github_id_to_full_info_map(self) -> dict[str, dict]:
        """
        构建 GitHub ID -> {name, employee_id} 映射
        
        Returns:
            GitHub ID -> 完整信息字典
        """
        persons = self.read_persons_from_column_d()
        return {
            p.github_id: {
                'name': p.name,
                'employee_id': p.employee_id
            }
            for p in persons
        }

    def read_labels_from_column_b(self) -> dict[str, str]:
        """
        从 B 列读取 label -> 负责人映射
        
        B 列包含 label，D 列包含对应的负责人姓名。
        B 列格式: "特性名称\n(label)" 
        D 列格式: "人名\n(github-id)"
        
        label 中的下划线转换为连字符，如 core_features -> core-features
        
        Returns:
            Label -> 负责人姓名 的字典
        """
        if self._rows is None:
            self._rows = self._fetch_csv()
        
        label_mapping = {}
        for row in self._rows[1:]:
            if len(row) < 4:
                continue
            
            b_value = row[1].strip() if len(row) > 1 else ""
            d_value = row[3].strip() if len(row) > 3 else ""
            
            if not b_value or not d_value:
                continue
            
            b_normalized = b_value.replace('\n', ' ').strip()
            d_normalized = d_value.replace('\n', ' ').strip()
            
            # 从 B 列提取 label
            label_pattern = r'[（(]([a-zA-Z0-9_-]+)[）)]'
            label_match = re.search(label_pattern, b_normalized)
            
            if label_match:
                label = label_match.group(1).strip().replace('_', '-')
                
                # 从 D 列提取人名（括号前的部分）
                name_pattern = r'^([^（(]+)'
                name_match = re.match(name_pattern, d_normalized)
                if name_match:
                    name = name_match.group(1).strip()
                    name = re.sub(r'\d+', '', name).strip()
                    if name and label:
                        label_mapping[label] = name
            
        return label_mapping

    def build_all_mappings(self) -> tuple[dict[str, dict], dict[str, str]]:
        """
        构建所有映射
        
        Returns:
            (github_id_to_full_info, label_to_name) 元组
            github_id_to_full_info: {"github_id": {"name": "人名", "employee_id": "工号"}}
            label_to_name: {"label": "负责人姓名"}
        """
        github_id_to_full_info = self.build_github_id_to_full_info_map()
        label_to_name = self.read_labels_from_column_b()
        
        return github_id_to_full_info, label_to_name

    def close(self):
        pass