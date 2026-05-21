"""
WeLink Issue Reporter

分析 GitHub 仓库中 triaged issue 的处理状态，
识别分发后超过指定天数仍未处理的 issue。

架构分层：
- config/     : 配置加载与管理
- models/     : 数据模型定义
- services/   : 业务逻辑实现
- utils/      : 工具函数
- pipeline.py : 流程编排
"""

from src.pipeline import Pipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_all():
    """
    运行完整的 Issue 分析流程
    
    流程步骤：
    1. 解析 triaged issue
    2. 获取标签变更事件
    3. 提取最终负责人
    4. 检查超期状态
    5. 生成最终报告
    """
    pipeline = Pipeline()
    pipeline.run()


if __name__ == '__main__':
    run_all()