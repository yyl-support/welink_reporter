# Issue #2: [feature]:welink消息通知负责人规则修正

**状态**: open  
**创建时间**: 2026-05-22T09:05:28Z  
**链接**: https://github.com/yyl-support/welink_reporter/issues/2

---

## 需求描述

对于当前的最终接口人方案进行修正：

### 需求点

0. **特殊 label 直接分配**
   - 先拿到时间线和 issue 相关 label（原过滤规则不变）
   - label 为 `gqa-model` 和 `310P` 的直接分给接口人
   - 不看时间线

1. **保留时间线链路全部负责人**
   - 先按照时间线去对
   - 保留整个时间线链路上的全部负责人（githubid）

2. **Excel 表格匹配失败时使用 label**
   - 如果最终确定的接口人，没法在 excel 表格中读取到人名或工号
   - 就去读取 label 对应的信息

3. **最终关联流程**
   - 先按照委派的时间线
   - 如果没有 -> 按照 label 对应
   - 如果全都没有 -> 划归为所有人

---

## 技术方案

### 1. 修改 analyze_assignment.py

**当前逻辑**:
- 只取时间线最后一个负责人作为最终接口人

**新逻辑**:
- 保留整个时间线链路上的所有负责人
- 检查特殊 label (`gqa-model`, `310P`) 直接分配

### 2. 新增 label -> 负责人映射

需要从 Google Sheets B 列解析：
- B 列格式：`人名(label)`
- 提取 label 和对应负责人

### 3. 修改 welink_inform.py

**匹配优先级**:
```
1. 特殊 label (gqa-model, 310P) -> 直接分配对应接口人
2. 时间线负责人 -> 匹配 Excel 人名
3. 时间线负责人匹配失败 -> 使用 label 映射
4. 全都失败 -> @所有人
```

### 4. 数据结构

**时间线负责人列表**:
```python
{
  "issue_number": 123,
  "assignee_chain": ["user1", "user2", "user3"],  # 全部负责人
  "labels": ["triaged", "gqa-model"],
  "final_assignee": "接口人姓名"  # 最终确定的接口人
}
```

---

## 特殊 Label 配置

需要在 config.yaml 中配置特殊 label：
```yaml
special_labels:
  - "gqa-model"
  - "310P"
```