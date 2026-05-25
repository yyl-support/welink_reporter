# Issue #3: 定时任务调度更新

## Issue 来源

GitHub Issue: https://github.com/yyl-support/welink_reporter/issues/3

## 需求概述

修改项目的定时任务调度配置：

| 任务 | 当前调度 | 目标调度 |
|------|----------|----------|
| Pipeline 执行（welink_inform.txt 更新） | 周一/周五 9:28 | 每天 8:00, 14:00, 19:00 |
| 数据同步（Google Sheets → 本地） | 周三 20:00 | 周一 7:00 |
| Pipeline step5/step6 | 已注释，不执行 | 取消注释，随 Pipeline 执行 |

## 需求详细分析

### 1. Pipeline 执行频率变更

**当前实现：**
- `scheduler.py` 第 87-88 行硬编码 `schedule.every().monday.at("09:28")` 和 `schedule.every().friday.at("09:28")`
- Pipeline 执行步骤 1-4（解析、获取数据、分析分配、生成报告）
- step5（生成 WeLink 通知）和 step6（发送消息）被注释

**需求变更：**
- 执行频率改为每天三次：8:00, 14:00, 19:00
- 取消 step5 和 step6 的注释，使其随 Pipeline 执行
- 通知生成和消息发送将每天执行三次

### 2. 数据同步调度变更

**当前实现：**
- `config.yaml` 中 `data_sync.schedule.day: wednesday, time: 20:00`
- `scheduler.py` 第 92-98 行读取配置动态设置调度

**需求变更：**
- 时间改为周一早上 7:00
- 数据同步在 Pipeline 执行前完成，确保周一 8:00 Pipeline 有最新数据

### 3. 被注释代码的处理

**当前状态：**
- `pipeline.py` 第 258-259 行：
  ```python
  # self.step5_generate_welink_inform()
  # self.step6_send_welink_message()
  ```

**需求变更：**
- 取消注释，step5 和 step6 作为 Pipeline 流程的一部分执行
- WeLink 通知文件和消息发送将每天执行三次

## 设计方案

采用**配置驱动调度**方案：

### 架构设计

```
config.yaml
├── pipeline.schedule: ["08:00", "14:00", "19:00"]  (新增)
├── data_sync.schedule.day: "monday"  (修改)
├── data_sync.schedule.time: "07:00"  (修改)

scheduler.py
├── setup_schedule() 读取 pipeline.schedule 配置
├── 为每个时间点创建调度任务
├── 数据同步按 data_sync.schedule 配置

pipeline.py
├── run() 取消 step5/step6 注释
├── 完整执行步骤 1-6
```

### 数据流

```
周一 7:00: 数据同步（Google Sheets → issue_assign.json, issue_label.json）

每天 8:00/14:00/19:00:
  Step 1: 解析 triaged issues
  Step 2: 获取完整数据（comments + timeline）
  Step 3: 分析分配链
  Step 4: 生成 assignment_analysis.json
  Step 5: 生成 welink_inform.txt ← 取消注释
  Step 6: 发送 WeLink 消息 ← 取消注释
```

### 配置优先级优势

1. **灵活性**：修改调度时间无需改代码，只改配置
2. **一致性**：符合现有 `data_sync` 配置模式
3. **可维护性**：配置集中管理，易于理解

## 影响范围

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `config.yaml` | 新增 `pipeline.schedule`，修改 `data_sync.schedule` |
| `src/config/loader.py` | 新增 `get_pipeline_schedule()` 方法 |
| `scheduler.py` | 修改 `setup_schedule()` 支持多时间点调度 |
| `src/pipeline.py` | 取消 step5/step6 注释 |

### 不涉及变更

- `main.py` - 无变更
- `src/services/*.py` - 无变更
- 测试文件 - 需新增调度配置测试

## 验收标准

1. Pipeline 每天在 8:00, 14:00, 19:00 执行
2. 数据同步在每周一 7:00 执行
3. Pipeline 执行包含 step5 和 step6
4. 配置文件可调整调度时间
5. 现有测试通过
6. 新增调度配置测试通过

## 依赖关系

- 无外部依赖
- 依赖 Issue #1 的 `issue_assign.json` 和 `issue_label.json` 文件存在
- 依赖 Issue #2 的 WeLink 通知四级匹配优先级已实现

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| WeLink API 调用频率增加 | 每天 3 次调用，可能触发限流 | 监控调用状态，必要时调整频率 |
| Pipeline 执行时间过长 | 高频执行可能重叠 | 使用独立线程执行，设置超时 |
| 数据同步失败 | Pipeline 使用旧数据 | 数据同步失败日志告警 |

## 时间估算

- 配置修改：15 分钟
- Scheduler 修改：30 分钟
- Pipeline 注释取消：5 分钟
- ConfigLoader 新增方法：15 分钟
- 测试编写：30 分钟
- 验证：15 分钟

**总计：约 2 小时**