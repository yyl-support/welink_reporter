import csv
import io
import re
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class PersonInfo:
    name: str
    github_id: str


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
        response = requests.get(self._csv_url, timeout=30)
        response.raise_for_status()
        content = response.content.decode('utf-8')
        reader = csv.reader(io.StringIO(content))
        return list(reader)

    def read_persons_from_column_d(self) -> list[PersonInfo]:
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
            
            pattern_with_parens = r'[（(]([a-zA-Z0-9_-]+)[）)]'
            matches = re.findall(pattern_with_parens, value)
            
            if matches:
                name_pattern = r'^([^（(]+)'
                name_match = re.match(name_pattern, value)
                name = name_match.group(1).strip() if name_match else ""
                name = re.sub(r'\d+', '', name).strip()
                name = name.replace('\n', ' ').strip()
                
                for github_id in matches:
                    if github_id and github_id not in seen:
                        if name:
                            persons.append(PersonInfo(name=name, github_id=github_id))
                            seen.add(github_id)
            else:
                pattern_without_parens = r'^([^\d]+?)\s+(\d+)?\s*([a-zA-Z][a-zA-Z0-9_-]*)$'
                match = re.match(pattern_without_parens, value)
                if match:
                    name = match.group(1).strip()
                    name = name.replace('\n', ' ').strip()
                    github_id = match.group(3)
                    if name and github_id and github_id not in seen:
                        persons.append(PersonInfo(name=name, github_id=github_id))
                        seen.add(github_id)
        return persons

    def build_github_id_to_name_map(self) -> dict[str, str]:
        return {p.github_id: p.name for p in self.read_persons_from_column_d()}

    def close(self):
        pass