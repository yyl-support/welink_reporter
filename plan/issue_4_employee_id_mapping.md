# Issue #4: [feature]:新增指派人员工号信息关联

**状态**: open  
**创建时间**: 2026-05-25  
**链接**: https://github.com/yyl-support/welink_reporter/issues/4

---

## 需求描述

在 issue_assign 里面，之前关联了人员的 GitHub ID 和人名，现在还需要关联其对应的工号，也在同样的表格 sheet 页中。

### 需求点

1. **工号信息关联**
   - 从 Google Sheets 同一页面读取员工工号信息
   - 将工号与 GitHub ID、人名一并保存到本地 JSON 文件
   
2. **数据格式变更**
   - 当前格式：`{"github_id": "人名"}`
   - 新格式：包含工号信息的完整映射

### 示例数据

| 人名 | GitHub ID | 工号 |
|------|-----------|------|
| 刘逸舟 | yiz-liu | 30063492 |
| 余林峰 | earthmanylf | 00879304 |

---

## 当前代码分析

### 涉及文件

| 文件 | 当前功能 | 需要修改 |
|------|----------|----------|
| `src/services/excel_reader.py` | 从 D 列解析人名和 GitHub ID | 需要新增工号解析 |
| `src/services/data_sync_service.py` | 同步数据到 JSON 文件 | 需要修改 JSON 格式 |
| `data/issue_assign.json` | 存储 GitHub ID -> 人名映射 | 需要变更数据结构 |

### 当前数据结构

**PersonInfo dataclass** (excel_reader.py:10-13):
```python
@dataclass
class PersonInfo:
    name: str
    github_id: str
```

**issue_assign.json 当前格式**:
```json
{
  "yiz-liu": "刘逸舟",
  "earthmanylf": "余林峰",
  ...
}
```

### 当前解析逻辑分析

在 `read_persons_from_column_d` 方法中，存在两种解析模式：

1. **带括号模式**: `r'[（(]([a-zA-Z0-9_-]+)[）)]'`
   - 格式：`人名(github-id)`
   - 提取括号中的 github_id

2. **不带括号模式**: `r'^([^\d]+?)\s+(\d+)?\s*([a-zA-Z][a-zA-Z0-9_-]*)$'`
   - 格式：`人名 工号 github-id`
   - 已有 `\d+` 模式匹配工号，但当前未保存

**关键发现**: `pattern_without_parens` 中的 `\d+` 已经匹配了数字，但当前代码未将其保存到 PersonInfo 中。

---

## 技术方案

### 1. 数据结构变更

**PersonInfo 新结构**:
```python
@dataclass
class PersonInfo:
    name: str
    github_id: str
    employee_id: Optional[str] = None  # 新增工号字段
```

**issue_assign.json 新格式**:
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

### 2. 解析逻辑修改

在 `read_persons_from_column_d` 方法中：
- 修改不带括号的解析模式，保存匹配到的工号
- 检查其他列是否有工号信息

### 3. 同步服务修改

在 `data_sync_service.py` 中：
- 修改 JSON 输出格式为嵌套结构

### 4. 使用方修改

在 `welink_inform.py` 中：
- 修改读取逻辑适配新的 JSON 格式
- 确保 `github_id_to_name` 映射仍然可用

---

## 参考链接

- Google Sheets: https://docs.google.com/spreadsheets/d/1VF__45_AA51HGr1hqi-oTlT0-gCciBnMJfBOBwbrvgA/edit?gid=2110807604#gid=2110807604