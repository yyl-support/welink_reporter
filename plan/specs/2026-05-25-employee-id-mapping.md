# Issue #4: 新增指派人员工号信息关联 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 issue_assign 映射中新增员工工号信息，使数据更完整

**Architecture:** 扩展 PersonInfo 数据结构添加 employee_id 字段；修改解析逻辑提取工号；变更 JSON 格式为嵌套结构；更新使用方适配新格式

**Tech Stack:** Python, dataclasses, JSON

---

## 文件结构

**修改文件:**
- `src/services/excel_reader.py` - PersonInfo 添加 employee_id 字段，修改解析逻辑
- `src/services/data_sync_service.py` - 修改 JSON 输出格式
- `src/services/welink_inform.py` - 适配新的 JSON 格式
- `tests/test_excel_reader.py` - 更新测试适配新数据结构
- `tests/test_data_sync_service.py` - 更新测试适配新 JSON 格式
- `tests/test_welink_inform.py` - 更新测试适配新格式读取

**数据文件 (自动生成):**
- `data/issue_assign.json` - 新格式 GitHub ID -> {name, employee_id} 映射

---

## Task 1: 扩展 PersonInfo 数据结构

**Files:**
- Modify: `src/services/excel_reader.py`

- [ ] **Step 1: 添加 employee_id 字段到 PersonInfo**

修改 `PersonInfo` dataclass:

```python
@dataclass
class PersonInfo:
    name: str
    github_id: str
    employee_id: Optional[str] = None
```

- [ ] **Step 2: 修改 extract_name_and_github_id 函数**

当前函数不支持工号，保持不变或标记为旧格式兼容。

- [ ] **Step 3: 验证修改**

Run: `python -c "from src.services.excel_reader import PersonInfo; p = PersonInfo('test', 'test-id', '12345'); print(p)"`

---

## Task 2: 修改 read_persons_from_column_d 解析逻辑

**Files:**
- Modify: `src/services/excel_reader.py`

- [ ] **Step 1: 修改不带括号模式的解析**

在 `read_persons_from_column_d` 方法中，修改 `pattern_without_parens` 的解析逻辑，保存工号:

```python
else:
    pattern_without_parens = r'^([^\d]+?)\s+(\d+)?\s*([a-zA-Z][a-zA-Z0-9_-]*)$'
    match = re.match(pattern_without_parens, value)
    if match:
        name = match.group(1).strip()
        name = name.replace('\n', ' ').strip()
        employee_id = match.group(2) if match.group(2) else None
        github_id = match.group(3)
        if name and github_id and github_id not in seen:
            persons.append(PersonInfo(
                name=name, 
                github_id=github_id, 
                employee_id=employee_id
            ))
            seen.add(github_id)
```

- [ ] **Step 2: 添加带括号模式的工号提取**

在带括号模式解析中，检查括号前是否有工号数字:

```python
if matches:
    name_pattern = r'^([^（(]+)'
    name_match = re.match(name_pattern, value)
    name = name_match.group(1).strip() if name_match else ""
    
    # 提取工号（括号前的数字）
    employee_id_pattern = r'(\d+)'
    employee_id_match = re.search(employee_id_pattern, name)
    employee_id = employee_id_match.group(1) if employee_id_match else None
    
    name = re.sub(r'\d+', '', name).strip()
    name = name.replace('\n', ' ').strip()
    
    for github_id in matches:
        if github_id and github_id not in seen:
            if name:
                persons.append(PersonInfo(
                    name=name, 
                    github_id=github_id, 
                    employee_id=employee_id
                ))
                seen.add(github_id)
```

- [ ] **Step 3: 检查其他列是否有工号**

根据 Google Sheets 结构，可能需要在其他列查找工号信息。添加方法检查指定列:

```python
def read_persons_with_employee_id(self) -> list[PersonInfo]:
    """
    从 D 列读取人员信息，包括工号
    
    工号可能在:
    1. D 列人名前的数字（如：刘逸舟30063492(yiz-liu)）
    2. 其他列（需要确认列位置）
    
    Returns:
        包含工号的 PersonInfo 列表
    """
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
        
        # 尝试多种格式解析
        person = self._parse_person_value(value)
        if person and person.github_id not in seen:
            persons.append(person)
            seen.add(person.github_id)
    
    return persons

def _parse_person_value(self, value: str) -> Optional[PersonInfo]:
    """
    解析单个单元格值，提取人名、GitHub ID 和工号
    
    支持格式:
    - 人名(github-id)
    - 人名工号(github-id)
    - 人名 工号 github-id
    
    Args:
        value: 单元格文本
    
    Returns:
        PersonInfo 或 None
    """
    # 格式1: 人名工号(github-id) 或 人名(github-id)
    pattern_with_parens = r'^(.+?)[（(]([a-zA-Z0-9_-]+)[）)]$'
    match = re.match(pattern_with_parens, value)
    if match:
        name_part = match.group(1).strip()
        github_id = match.group(2).strip()
        
        # 从 name_part 提取工号
        employee_id_match = re.search(r'(\d{6,8})', name_part)
        employee_id = employee_id_match.group(1) if employee_id_match else None
        
        name = re.sub(r'\d+', '', name_part).strip()
        name = name.replace('\n', ' ').strip()
        
        if name and github_id:
            return PersonInfo(name=name, github_id=github_id, employee_id=employee_id)
    
    # 格式2: 人名 工号 github-id
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
```

- [ ] **Step 4: 运行测试验证**

Run: `python -m pytest tests/test_excel_reader.py -v`

---

## Task 3: 修改 build_github_id_to_name_map 返回完整信息

**Files:**
- Modify: `src/services/excel_reader.py`

- [ ] **Step 1: 新增方法返回完整映射**

添加新方法返回包含工号的完整映射:

```python
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
```

- [ ] **Step 2: 修改 build_all_mappings 返回完整信息**

修改 `build_all_mappings` 方法:

```python
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
```

- [ ] **Step 3: 保留旧方法兼容性**

保持 `build_github_id_to_name_map` 方法不变，用于兼容:

```python
def build_github_id_to_name_map(self) -> dict[str, str]:
    """
    构建 GitHub ID -> 人名映射（仅人名，不含工号）
    
    兼容旧版本使用
    
    Returns:
        GitHub ID -> 人名 的字典
    """
    return {p.github_id: p.name for p in self.read_persons_from_column_d()}
```

---

## Task 4: 修改数据同步服务

**Files:**
- Modify: `src/services/data_sync_service.py`

- [ ] **Step 1: 修改 sync 方法保存新格式**

修改 `sync` 方法保存新的 JSON 格式:

```python
def sync(self) -> Dict[str, Any]:
    """
    执行数据同步
    
    Returns:
        同步结果统计
    """
    logger.info("=" * 60)
    logger.info("Starting Data Sync from Google Sheets")
    logger.info("=" * 60)
    
    if not self.excel_url:
        logger.error("No Excel URL provided, sync aborted")
        return {'assign_count': 0, 'label_count': 0}
    
    reader = GoogleSheetsReader(self.excel_url, self.excel_gid)
    
    github_id_to_full_info, label_to_name = reader.build_all_mappings()
    reader.close()
    
    assign_file = os.path.join(DATA_DIR, 'issue_assign.json')
    label_file = os.path.join(DATA_DIR, 'issue_label.json')
    
    with open(assign_file, 'w', encoding='utf-8') as f:
        json.dump(github_id_to_full_info, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(github_id_to_full_info)} GitHub ID mappings to {assign_file}")
    
    with open(label_file, 'w', encoding='utf-8') as f:
        json.dump(label_to_name, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(label_to_name)} Label mappings to {label_file}")
    
    logger.info("=" * 60)
    logger.info("Data Sync Completed")
    logger.info("=" * 60)
    
    return {
        'assign_count': len(github_id_to_full_info),
        'label_count': len(label_to_name)
    }
```

- [ ] **Step 2: 运行测试验证**

Run: `python -m pytest tests/test_data_sync_service.py -v`

---

## Task 5: 修改 WeLinkInformService 适配新格式

**Files:**
- Modify: `src/services/welink_inform.py`

- [ ] **Step 1: 修改 load_name_mapping_from_local 返回兼容格式**

修改方法，使返回值仍为 `github_id -> name` 字典（兼容现有逻辑）:

```python
def load_name_mapping_from_local(self) -> Dict[str, str]:
    """
    从本地 JSON 文件加载 GitHub ID -> 人名映射
    
    支持新格式 JSON（嵌套结构）和旧格式（简单字符串）
    
    Returns:
        GitHub ID -> 人名 的字典
    """
    file_path = os.path.join(DATA_DIR, 'issue_assign.json')
    
    if not os.path.exists(file_path):
        logger.warning(f"Local mapping file not found: {file_path}")
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    # 处理新格式（嵌套结构）
    result = {}
    for github_id, value in mapping.items():
        if isinstance(value, dict):
            result[github_id] = value.get('name', '')
        else:
            # 兼容旧格式（简单字符串）
            result[github_id] = value
    
    logger.info(f"Loaded {len(result)} person mappings from local file")
    return result
```

- [ ] **Step 2: 新增方法加载完整信息**

添加方法返回包含工号的完整信息:

```python
def load_full_info_from_local(self) -> Dict[str, Dict[str, str]]:
    """
    从本地 JSON 文件加载完整人员信息
    
    Returns:
        GitHub ID -> {name, employee_id} 的字典
    """
    file_path = os.path.join(DATA_DIR, 'issue_assign.json')
    
    if not os.path.exists(file_path):
        logger.warning(f"Local mapping file not found: {file_path}")
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    result = {}
    for github_id, value in mapping.items():
        if isinstance(value, dict):
            result[github_id] = value
        else:
            # 兼容旧格式
            result[github_id] = {'name': value, 'employee_id': None}
    
    logger.info(f"Loaded {len(result)} person full info from local file")
    return result
```

- [ ] **Step 3: 运行测试验证**

Run: `python -m pytest tests/test_welink_inform.py -v`

---

## Task 6: 更新测试文件

**Files:**
- Modify: `tests/test_excel_reader.py`
- Modify: `tests/test_data_sync_service.py`

- [ ] **Step 1: 更新 test_excel_reader.py**

修改 PersonInfo 测试适配新字段:

```python
class TestPersonInfo:
    """PersonInfo 数据类测试"""
    
    def test_person_info_creation(self):
        """测试 PersonInfo 创建"""
        person = PersonInfo(name="zhangsan", github_id="zhangsan")
        assert person.name == "zhangsan"
        assert person.github_id == "zhangsan"
        assert person.employee_id is None
    
    def test_person_info_with_employee_id(self):
        """测试 PersonInfo 带工号创建"""
        person = PersonInfo(name="刘逸舟", github_id="yiz-liu", employee_id="30063492")
        assert person.name == "刘逸舟"
        assert person.github_id == "yiz-liu"
        assert person.employee_id == "30063492"
```

- [ ] **Step 2: 更新 test_data_sync_service.py**

修改测试适配新 JSON 格式:

```python
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
            
            with open(assign_file, 'r', encoding='utf-8') as f:
                assign_data = json.load(f)
            
            assert assign_data["user1"]["name"] == "用户1"
            assert assign_data["user1"]["employee_id"] == "12345"
        finally:
            sync_module.DATA_DIR = original_data_dir
```

- [ ] **Step 3: 运行全部测试**

Run: `python -m pytest tests/ -v`

---

## Task 7: 验证新格式数据

**Files:**
- None (手动测试)

- [ ] **Step 1: 手动触发数据同步**

```bash
python -c "
from src.services.data_sync_service import sync_data_from_google_sheets
from src.config.loader import ConfigLoader
import os

config_path = 'config.yaml'
loader = ConfigLoader()
config = loader.load(config_path)

excel_url = loader.get_excel_url(config)
excel_gid = loader.get_excel_gid(config)

result = sync_data_from_google_sheets(excel_url, excel_gid)
print(f'Sync result: {result}')
"
```

- [ ] **Step 2: 检查生成的 JSON 格式**

```bash
cat data/issue_assign.json
```

Expected output similar to:
```json
{
  "yiz-liu": {
    "name": "刘逸舟",
    "employee_id": "30063492"
  },
  "earthmanylf": {
    "name": "余林峰",
    "employee_id": "00879304"
  }
}
```

- [ ] **Step 3: 验证 WeLink 服务读取**

```bash
python -c "
from src.services.welink_inform import WeLinkInformService

service = WeLinkInformService(use_local=True)
mapping = service.load_name_mapping_from_local()
full_info = service.load_full_info_from_local()

print('Name mapping:', mapping)
print('Full info:', full_info)
"
```

---

## 自检清单

- [ ] 检查 spec 覆盖:
  - PersonInfo 添加 employee_id 字段: ✓ Task 1
  - 解析逻辑提取工号: ✓ Task 2
  - JSON 格式变更: ✓ Task 4
  - 使用方适配新格式: ✓ Task 5
  - 测试更新: ✓ Task 6

- [ ] 检查类型一致性:
  - employee_id 类型为 Optional[str]
  - 新 JSON 格式为 dict[str, dict]
  - load_name_mapping_from_local 返回 dict[str, str]（兼容）
  - load_full_info_from_local 返回 dict[str, dict[str, str]]

- [ ] 检查无占位符:
  - 所有代码块完整
  - 无 "TODO" 或 "TBD"

- [ ] 检查兼容性:
  - 旧格式 JSON 仍可读取
  - build_github_id_to_name_map 方法保留