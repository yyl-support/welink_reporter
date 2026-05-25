# Issue #1: 在线excel表格信息持久化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将在线 Google Sheets 数据定时本地化，避免网络波动和编码问题，提升系统稳定性

**Architecture:** 新增定时数据同步服务，每周三晚8点从 Google Sheets 拉取数据并保存为本地 JSON 文件；修改 WeLinkInformService 默认从本地读取数据，支持手动修改和在线模式切换

**Tech Stack:** Python, schedule, requests, JSON

---

## 文件结构

**新增文件:**
- `src/services/data_sync_service.py` - 数据同步服务，负责从 Google Sheets 拉取数据并保存到本地

**修改文件:**
- `scheduler.py` - 添加周三晚8点的数据同步定时任务
- `src/services/welink_inform.py` - 支持从本地 JSON 文件读取数据
- `src/services/excel_reader.py` - 新增读取 B 列解析 label 信息的方法
- `config.yaml` - 添加数据同步相关配置
- `src/config/loader.py` - 添加数据同步配置读取方法

**数据文件 (自动生成):**
- `data/issue_assign.json` - GitHub ID -> 人名映射
- `data/issue_label.json` - Label -> 负责人映射

---

## Task 1: 扩展 excel_reader.py 支持读取 Label 信息

**Files:**
- Modify: `src/services/excel_reader.py`

- [ ] **Step 1: 在 excel_reader.py 中添加读取 B 列的方法**

在 `GoogleSheetsReader` 类中添加 `read_labels_from_column_b` 方法：

```python
def read_labels_from_column_b(self) -> dict[str, str]:
    """
    从 B 列读取 label -> 负责人映射
    
    B 列格式: "人名(label)"
    例如: "刘逸舟(gqa-model)" -> {"gqa-model": "刘逸舟"}
    
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
        
        pattern = r'^(.+?)[（(]([^()（）]+)[）)]$'
        match = re.match(pattern, b_value)
        
        if match:
            name = match.group(1).strip()
            label = match.group(2).strip()
            if name and label:
                label_mapping[label] = name
    
    return label_mapping
```

- [ ] **Step 2: 添加构建两个映射的方法**

在 `GoogleSheetsReader` 类中添加：

```python
def build_all_mappings(self) -> tuple[dict[str, str], dict[str, str]]:
    """
    构建所有映射
    
    Returns:
        (github_id_to_name, label_to_name) 元组
    """
    github_id_to_name = self.build_github_id_to_name_map()
    label_to_name = self.read_labels_from_column_b()
    
    return github_id_to_name, label_to_name
```

- [ ] **Step 3: 运行测试验证**

Run: `python -m pytest tests/test_excel_reader.py -v`
Expected: 现有测试通过

---

## Task 2: 创建数据同步服务

**Files:**
- Create: `src/services/data_sync_service.py`

- [ ] **Step 1: 创建 DataSyncService 类**

创建文件 `src/services/data_sync_service.py`：

```python
"""
数据同步服务模块

负责从 Google Sheets 同步数据到本地 JSON 文件。
"""

import json
import os
from typing import Dict, Any, Optional
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
```

- [ ] **Step 2: 验证文件创建**

Run: `python -c "from src.services.data_sync_service import DataSyncService; print('OK')"`
Expected: 输出 "OK"

---

## Task 3: 添加本地数据读取功能

**Files:**
- Modify: `src/services/welink_inform.py`

- [ ] **Step 1: 添加本地数据加载方法**

在 `WeLinkInformService` 类中添加以下方法：

```python
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
```

- [ ] **Step 2: 修改 __init__ 方法支持本地/在线模式切换**

修改 `WeLinkInformService.__init__` 方法：

```python
def __init__(
    self,
    excel_url: str = None,
    excel_gid: str = None,
    use_local: bool = True
):
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
```

- [ ] **Step 3: 修改 generate 方法支持本地模式**

修改 `WeLinkInformService.generate` 方法中的映射加载逻辑：

```python
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
    
    pairs = self.generate_issue_assignee_pairs(analysis_data)
    logger.info(f"Generated {len(pairs)} issue-assignee pairs")
    
    assignee_issues = self.merge_by_assignee(pairs)
    logger.info(f"Merged into {len(assignee_issues)} assignee groups")
    
    if self.use_local:
        name_mapping = self.load_name_mapping_from_local()
    else:
        name_mapping = self.load_name_mapping_from_google_sheets()
    
    content = self.generate_inform_content(assignee_issues, name_mapping)
    
    file_path = self.save_inform_file(content)
    
    logger.info("=" * 60)
    logger.info("WeLink Inform Generation Completed")
    logger.info("=" * 60)
    
    return file_path
```

- [ ] **Step 4: 运行测试验证**

Run: `python -m pytest tests/test_welink_inform.py -v`
Expected: 现有测试通过

---

## Task 4: 更新配置文件和加载器

**Files:**
- Modify: `config.yaml`
- Modify: `src/config/loader.py`

- [ ] **Step 1: 更新 config.yaml 添加数据同步配置**

在 `config.yaml` 中添加：

```yaml
data_sync:
  enabled: true
  schedule:
    day: "wednesday"
    time: "20:00"
```

- [ ] **Step 2: 更新 config/loader.py 添加配置读取方法**

在 `ConfigLoader` 类中添加：

```python
def get_data_sync_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    获取数据同步配置
    
    Args:
        config: 配置字典
    
    Returns:
        数据同步配置字典
    """
    default_config = {
        'enabled': True,
        'schedule': {
            'day': 'wednesday',
            'time': '20:00'
        }
    }
    
    sync_config = config.get('data_sync', default_config)
    return sync_config
```

- [ ] **Step 3: 更新 DEFAULT_CONFIG**

在 `loader.py` 的 `DEFAULT_CONFIG` 中添加：

```python
DEFAULT_CONFIG: Dict[str, Any] = {
    # ... 现有配置 ...
    'data_sync': {
        'enabled': True,
        'schedule': {
            'day': 'wednesday',
            'time': '20:00'
        }
    }
}
```

---

## Task 5: 更新调度器添加数据同步任务

**Files:**
- Modify: `scheduler.py`

- [ ] **Step 1: 添加数据同步任务函数**

在 `scheduler.py` 中添加：

```python
def run_data_sync():
    """执行数据同步"""
    logger.info("=" * 60)
    logger.info(f"Scheduled data sync started at {datetime.now()}")
    logger.info("=" * 60)
    try:
        from src.config.loader import ConfigLoader
        from src.services.data_sync_service import sync_data_from_google_sheets
        
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'config.yaml'
        )
        loader = ConfigLoader()
        config = loader.load(config_path)
        
        excel_url = loader.get_excel_url(config)
        excel_gid = loader.get_excel_gid(config)
        
        result = sync_data_from_google_sheets(excel_url, excel_gid)
        
        logger.info(f"Data sync completed: {result}")
        logger.info("=" * 60)
        logger.info(f"Scheduled data sync finished at {datetime.now()}")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Data sync failed: {e}")
```

- [ ] **Step 2: 添加数据同步包装函数**

```python
def data_sync_wrapper():
    """包装数据同步任务运行在独立线程中"""
    thread = threading.Thread(target=run_data_sync, daemon=True)
    thread.start()
```

- [ ] **Step 3: 修改 setup_schedule 函数**

```python
def setup_schedule():
    """设置调度任务"""
    from src.config.loader import ConfigLoader
    
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'config.yaml'
    )
    loader = ConfigLoader()
    config = loader.load(config_path)
    
    sync_config = loader.get_data_sync_config(config)
    
    # 主流程：周一和周五早9:28
    schedule.every().monday.at("09:28").do(job_wrapper)
    schedule.every().friday.at("09:28").do(job_wrapper)
    logger.info("Schedule configured: Monday and Friday at 09:28")
    
    # 数据同步：周三晚8点
    if sync_config.get('enabled', True):
        sync_day = sync_config.get('schedule', {}).get('day', 'wednesday')
        sync_time = sync_config.get('schedule', {}).get('time', '20:00')
        
        scheduler = getattr(schedule.every(), sync_day.lower(), None)
        if scheduler:
            scheduler.at(sync_time).do(data_sync_wrapper)
            logger.info(f"Data sync scheduled: {sync_day} at {sync_time}")
        else:
            logger.warning(f"Invalid sync day: {sync_day}")
    else:
        logger.info("Data sync is disabled in config")
```

- [ ] **Step 4: 添加必要的 import**

在 `scheduler.py` 开头添加：

```python
import os
```

---

## Task 6: 更新 Pipeline 支持本地数据

**Files:**
- Modify: `src/pipeline.py`

- [ ] **Step 1: 修改 step5_generate_welink_inform 支持本地模式**

修改 `Pipeline.step5_generate_welink_inform` 方法：

```python
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
```

---

## Task 7: 编写测试

**Files:**
- Create: `tests/test_data_sync_service.py`

- [ ] **Step 1: 创建数据同步服务测试**

创建文件 `tests/test_data_sync_service.py`：

```python
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
            {"user1": "用户1", "user2": "用户2"},
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
                assert assign_data == {"user1": "用户1", "user2": "用户2"}
                
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
```

- [ ] **Step 2: 运行测试**

Run: `python -m pytest tests/test_data_sync_service.py -v`
Expected: 所有测试通过

---

## Task 8: 集成测试和验证

**Files:**
- None (手动测试)

- [ ] **Step 1: 验证本地数据文件格式**

手动创建测试数据文件验证格式：

```bash
# 创建测试数据
echo '{"user1": "用户1", "user2": "用户2"}' > data/issue_assign.json
echo '{"label1": "负责人1", "label2": "负责人2"}' > data/issue_label.json
```

- [ ] **Step 2: 验证本地模式加载**

```bash
python -c "
from src.services.welink_inform import WeLinkInformService
service = WeLinkInformService(use_local=True)
mapping = service.load_name_mapping_from_local()
print(f'Loaded {len(mapping)} mappings')
label_mapping = service.load_label_mapping_from_local()
print(f'Loaded {len(label_mapping)} label mappings')
"
```
Expected: 成功加载本地数据

- [ ] **Step 3: 验证调度器配置**

```bash
python -c "
from scheduler import setup_schedule
import schedule
setup_schedule()
for job in schedule.get_jobs():
    print(f'Job: {job}')
"
```
Expected: 显示周一/周五任务和周三数据同步任务

---

## 自检清单

- [ ] 检查 spec 覆盖:
  - 定时读取本地化: ✓ Task 5
  - 本地 JSON 文件保存: ✓ Task 2, Task 3
  - 支持本地手动修改: ✓ (JSON 文件可直接编辑)
  - 默认读取本地信息: ✓ Task 3
  - Label 和负责人关联信息: ✓ Task 1

- [ ] 检查类型一致性:
  - `use_local` 参数在 `__init__` 和 `generate` 中都是 `bool`
  - 返回值类型注解正确

- [ ] 检查无占位符:
  - 所有代码块完整
  - 无 "TODO" 或 "TBD"