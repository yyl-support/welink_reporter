# WeLink Issue Reporter

分析 GitHub 仓库中 triaged issue 的处理状态，识别分发后超过指定天数仍未处理的 issue，并生成 WeLink 通知文件。

## 功能

- 解析 triaged issue 数据
- 获取完整数据（comments + timeline）
- 分析分配链和负责人信息
- 从 Google Sheets 读取 GitHub ID 到人名的映射
- 生成 WeLink 通知文件

## 安装

```bash
pip install -r requirements.txt
```

## 配置

编辑 `config.yaml`:

```yaml
github:
  repo: "vllm-project/vllm-ascend"
  api_base: "https://api.github.com"

filters:
  triaged_label: "triaged"
  resolution_labels:
    - "invalid"
    - "wontfix"
    - "duplicated"
    - "wait-feedback"
    - "resolved"
  overdue_days: 7
  lookback_days: 2

excel:
  url: https://docs.google.com/spreadsheets/d/xxx/edit
  gid: 0
```

## 运行

```bash
python main.py
```

## 输出

生成 `data/welink_inform.txt`，格式如下：

```
请@人名，看下(issue链接列表)

请@所有人 查看下：未分配的issue链接列表
```

## 测试

```bash
python -m pytest tests/ -v
```

## 项目结构

```
welink-reporter/
├── main.py
├── config.yaml
├── src/
│   ├── pipeline.py
│   ├── config/
│   ├── models/
│   ├── services/
│   └── utils/
├── tests/
└── data/
``