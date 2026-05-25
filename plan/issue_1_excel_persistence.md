# Issue #1: [feature]:在线excel表格信息持久化

**状态**: open  
**创建时间**: 2026-05-22T09:03:20Z  
**链接**: https://github.com/yyl-support/welink_reporter/issues/1

---

## 需求描述

当前获取issue接口人的方法是直接获取在线表格，然后解析对应列信息，这样的方法可能会收到网络波动和编码影响，导致信息不稳定，我现在需要进行如下三处优化

### 需求点

1. **定时读取本地化**
   - 每周三晚上八点去线上读取最新的表格信息
   - 将有用信息规整并保留在本地 `/data` 中的 `issue_assign.json`
   - 支持本地手动修改
   - 后续直接读取本地信息

2. **label和负责人关联信息**
   - 查看 Google Sheets 中的 B 列
   - 括号中的英文信息即为 label 信息
   - 对应的 D 列负责人就是负责该类 label 的 issue 的接口人
   - 将这部分信息本地化保留在 `/data` 中的 `issue_label.json`

---

## 参考链接

- Google Sheets: https://docs.google.com/spreadsheets/d/1VF__45_AA51HGr1hqi-oTlT0-gCciBnMJfBOBwbrvgA/edit?gid=2110807604#gid=2110807604

---

## 技术方案

### 1. 新增定时任务
- 在 scheduler.py 中添加每周三晚上八点的定时任务
- 任务内容：从 Google Sheets 读取数据并保存到本地

### 2. 数据结构设计

**issue_assign.json** (GitHub ID -> 人名映射):
```json
{
  "yiz-liu": "刘逸舟",
  "lilinsiman": "李林斯曼",
  ...
}
```

**issue_label.json** (Label -> 负责人映射):
```json
{
  "gqa-model": "接口人姓名",
  "310P": "接口人姓名",
  ...
}
```

### 3. 修改读取逻辑
- WeLinkInformService 默认读取本地文件
- 支持通过参数切换为在线读取