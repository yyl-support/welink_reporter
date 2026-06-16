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

import argparse

from src.pipeline import Pipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_all(welink_auth: str = None, receiver_uid: str = None):
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
    pipeline.run(welink_auth=welink_auth, receiver_uid=receiver_uid)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='WeLink Issue Reporter')
    parser.add_argument('--welink-auth', type=str, required=True,
                        help='WeLink auth token (从小鲁班获取)')
    parser.add_argument('--receiver-uid', type=str, required=True,
                        help='Receiver UID (格式: 首字母+工号, 如 a00123456)')
    args = parser.parse_args()
    run_all(welink_auth=args.welink_auth, receiver_uid=args.receiver_uid)