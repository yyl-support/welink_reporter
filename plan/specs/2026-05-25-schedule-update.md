# Issue #3: 定时任务调度更新 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修改定时任务调度配置，Pipeline 执行改为每天三次（8:00, 14:00, 19:00），数据同步改为每周一 7:00，取消 Pipeline 中 step5/step6 注释

**Architecture:** 配置驱动调度，通过 config.yaml 配置调度时间，scheduler.py 动态读取配置创建调度任务，pipeline.py 取消注释恢复完整流程

**Tech Stack:** Python, schedule library, YAML config

---

## 文件结构

**修改文件:**
- `config.yaml` - 新增 pipeline.schedule 配置，修改 data_sync.schedule
- `src/config/loader.py` - 新增 get_pipeline_schedule() 方法
- `scheduler.py` - 修改 setup_schedule() 支持多时间点调度
- `src/pipeline.py` - 取消 step5/step6 注释

**新增文件:**
- `tests/test_schedule_config.py` - 调度配置测试

---

## Task 1: 更新 config.yaml 添加 pipeline.schedule 配置

**Files:**
- Modify: `config.yaml`

- [ ] **Step 1: 添加 pipeline.schedule 配置**

在 `config.yaml` 中添加：

```yaml
pipeline:
  schedule:
    times:
      - "08:00"
      - "14:00"
      - "19:00"
```

- [ ] **Step 2: 修改 data_sync.schedule 配置**

将 `config.yaml` 中：

```yaml
data_sync:
  enabled: true
  schedule:
    day: "wednesday"
    time: "20:00"
```

修改为：

```yaml
data_sync:
  enabled: true
  schedule:
    day: "monday"
    time: "07:00"
```

---

## Task 2: 更新 ConfigLoader 添加 pipeline schedule 读取方法

**Files:**
- Modify: `src/config/loader.py`

- [ ] **Step 1: 添加 get_pipeline_schedule 方法**

在 `ConfigLoader` 类中添加：

```python
def get_pipeline_schedule(self, config: Dict[str, Any]) -> List[str]:
    """
    获取 Pipeline 调度时间列表
    
    Args:
        config: 配置字典
    
    Returns:
        调度时间列表，如 ["08:00", "14:00", "19:00"]
    """
    default_times = ["08:00", "14:00", "19:00"]
    pipeline_config = config.get('pipeline', {})
    schedule_config = pipeline_config.get('schedule', {})
    times = schedule_config.get('times', default_times)
    
    logger.debug(f"Pipeline schedule times: {times}")
    return times
```

- [ ] **Step 2: 更新 DEFAULT_CONFIG**

在 `loader.py` 的 `DEFAULT_CONFIG` 中添加：

```python
DEFAULT_CONFIG: Dict[str, Any] = {
    # ... 现有配置 ...
    'pipeline': {
        'schedule': {
            'times': ["08:00", "14:00", "19:00"]
        }
    },
    'data_sync': {
        'enabled': True,
        'schedule': {
            'day': 'monday',
            'time': '07:00'
        }
    }
}
```

---

## Task 3: 修改 scheduler.py 支持多时间点调度

**Files:**
- Modify: `scheduler.py`

- [ ] **Step 1: 修改 setup_schedule 函数**

修改 `setup_schedule` 函数：

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
    
    # Pipeline 调度：每天多次执行
    pipeline_times = loader.get_pipeline_schedule(config)
    for time_str in pipeline_times:
        schedule.every().day.at(time_str).do(job_wrapper)
        logger.info(f"Pipeline scheduled: every day at {time_str}")
    
    # 数据同步调度
    sync_config = loader.get_data_sync_config(config)
    
    if sync_config.get('enabled', True):
        sync_day = sync_config.get('schedule', {}).get('day', 'monday')
        sync_time = sync_config.get('schedule', {}).get('time', '07:00')
        
        scheduler = getattr(schedule.every(), sync_day.lower(), None)
        if scheduler:
            scheduler.at(sync_time).do(data_sync_wrapper)
            logger.info(f"Data sync scheduled: {sync_day} at {sync_time}")
        else:
            logger.warning(f"Invalid sync day: {sync_day}")
    else:
        logger.info("Data sync is disabled in config")
```

- [ ] **Step 2: 删除旧的硬编码调度**

删除以下两行：

```python
schedule.every().monday.at("09:28").do(job_wrapper)
schedule.every().friday.at("09:28").do(job_wrapper)
logger.info("Schedule configured: Monday and Friday at 09:28")
```

---

## Task 4: 取消 Pipeline 中 step5/step6 注释

**Files:**
- Modify: `src/pipeline.py`

- [ ] **Step 1: 取消 step5 和 step6 的注释**

将 `src/pipeline.py` 第 258-259 行：

```python
# self.step5_generate_welink_inform()
# self.step6_send_welink_message()
```

修改为：

```python
self.step5_generate_welink_inform()
self.step6_send_welink_message()
```

- [ ] **Step 2: 验证 Pipeline run 方法完整性**

确认 `run()` 方法完整执行 1-6 步骤：

```python
def run(self) -> List[Dict[str, Any]]:
    """运行完整流程"""
    logger.info("=" * 60)
    logger.info("STARTING ISSUE ASSIGNMENT ANALYSIS PIPELINE")
    logger.info("=" * 60)
    
    self.load_config()
    
    issues = self.step1_parse_issues()
    
    if not issues:
        logger.warning("No triaged issues found, pipeline terminated")
        return []
    
    full_report = self.step2_fetch_full_data(issues)
    results = self.step3_analyze_assignment(full_report)
    report = self.step4_generate_report(results)
    self.step5_generate_welink_inform()
    self.step6_send_welink_message()
    
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)
    
    return report
```

---

## Task 5: 编写调度配置测试

**Files:**
- Create: `tests/test_schedule_config.py`

- [ ] **Step 1: 创建调度配置测试文件**

创建文件 `tests/test_schedule_config.py`：

```python
"""
调度配置测试
"""

import pytest
from src.config.loader import ConfigLoader


class TestPipelineScheduleConfig:
    """Pipeline 调度配置测试"""
    
    def test_get_pipeline_schedule_default(self):
        """测试默认 Pipeline 调度时间"""
        loader = ConfigLoader()
        config = {}
        
        times = loader.get_pipeline_schedule(config)
        
        assert times == ["08:00", "14:00", "19:00"]
    
    def test_get_pipeline_schedule_from_config(self):
        """测试从配置读取 Pipeline 调度时间"""
        loader = ConfigLoader()
        config = {
            'pipeline': {
                'schedule': {
                    'times': ["09:00", "15:00", "21:00"]
                }
            }
        }
        
        times = loader.get_pipeline_schedule(config)
        
        assert times == ["09:00", "15:00", "21:00"]
    
    def test_get_pipeline_schedule_partial_config(self):
        """测试部分配置"""
        loader = ConfigLoader()
        config = {
            'pipeline': {}
        }
        
        times = loader.get_pipeline_schedule(config)
        
        assert times == ["08:00", "14:00", "19:00"]


class TestDataSyncScheduleConfig:
    """数据同步调度配置测试"""
    
    def test_get_data_sync_config_default(self):
        """测试默认数据同步配置"""
        loader = ConfigLoader()
        config = {}
        
        sync_config = loader.get_data_sync_config(config)
        
        assert sync_config['enabled'] == True
        assert sync_config['schedule']['day'] == 'monday'
        assert sync_config['schedule']['time'] == '07:00'
    
    def test_get_data_sync_config_from_yaml(self):
        """测试从 YAML 配置读取"""
        loader = ConfigLoader()
        config = {
            'data_sync': {
                'enabled': False,
                'schedule': {
                    'day': 'tuesday',
                    'time': '10:00'
                }
            }
        }
        
        sync_config = loader.get_data_sync_config(config)
        
        assert sync_config['enabled'] == False
        assert sync_config['schedule']['day'] == 'tuesday'
        assert sync_config['schedule']['time'] == '10:00'
```

- [ ] **Step 2: 运行测试**

Run: `python -m pytest tests/test_schedule_config.py -v`
Expected: 所有测试通过

---

## Task 6: 验证和文档更新

**Files:**
- None (手动验证)

- [ ] **Step 1: 验证配置加载**

```bash
python -c "
from src.config.loader import ConfigLoader
loader = ConfigLoader()
config = loader.load('config.yaml')

pipeline_times = loader.get_pipeline_schedule(config)
print(f'Pipeline times: {pipeline_times}')

sync_config = loader.get_data_sync_config(config)
print(f'Data sync: {sync_config}')
"
```

Expected: 
- Pipeline times: ['08:00', '14:00', '19:00']
- Data sync: {'enabled': True, 'schedule': {'day': 'monday', 'time': '07:00'}}

- [ ] **Step 2: 验证调度器配置**

```bash
python -c "
from scheduler import setup_schedule
import schedule
setup_schedule()
for job in schedule.get_jobs():
    print(f'Job: {job}')
"
```

Expected: 显示 3 个 Pipeline 任务和 1 个数据同步任务

- [ ] **Step 3: 验证 Pipeline 步骤**

```bash
python -c "
from src.pipeline import Pipeline
p = Pipeline()
# 检查 run 方法是否包含 step5 和 step6
import inspect
source = inspect.getsource(p.run)
print('step5_generate_welink_inform' in source)
print('step6_send_welink_message' in source)
"
```

Expected: 输出两个 True

---

## 自检清单

- [ ] 检查 spec 覆盖:
  - Pipeline 每天 8:00, 14:00, 19:00 执行: ✓ Task 3
  - 数据同步周一 7:00 执行: ✓ Task 1, Task 2
  - 取消 step5/step6 注释: ✓ Task 4
  - 配置驱动调度: ✓ Task 1, Task 2, Task 3

- [ ] 检查类型一致性:
  - `get_pipeline_schedule` 返回 `List[str]`
  - `get_data_sync_config` 返回 `Dict[str, Any]`
  - `pipeline_times` 配置项为时间字符串列表

- [ ] 检查无占位符:
  - 所有代码块完整
  - 无 "TODO" 或 "TBD"

- [ ] 检查依赖:
  - 需确保 Issue #1 和 Issue #2 已完成
  - `issue_assign.json` 和 `issue_label.json` 文件存在
  - WeLink 四级匹配优先级已实现

---

## 执行顺序

1. Task 1: 更新 config.yaml
2. Task 2: 更新 ConfigLoader
3. Task 3: 修改 scheduler.py
4. Task 4: 取消 Pipeline 注释
5. Task 5: 编写测试
6. Task 6: 验证

---

## 完成标准

1. 所有测试通过
2. 配置正确加载
3. 调度器设置正确
4. Pipeline 执行包含 step5 和 step6
5. 文档更新（如有）