"""
日志工具模块

提供统一的日志配置和获取接口，支持不同级别的日志输出。
"""

import logging
import sys

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    获取配置好的 Logger 实例
    
    Args:
        name: 日志器名称，通常使用模块名
        level: 日志级别，默认为 INFO
    
    Returns:
        logging.Logger: 配置好的日志器实例
    
    Example:
        logger = get_logger(__name__)
        logger.info("开始处理任务")
        logger.warning("发现异常数据")
        logger.error("请求失败")
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(handler)
    
    logger.setLevel(level)
    return logger


def log_step(logger: logging.Logger, step_name: str, message: str = ""):
    """
    打印流程步骤日志
    
    Args:
        logger: 日志器实例
        step_name: 步骤名称
        message: 附加消息
    """
    border = "=" * 60
    logger.info(border)
    logger.info(f"[STEP] {step_name}")
    if message:
        logger.info(message)
    logger.info(border)


def log_summary(logger: logging.Logger, title: str, items: list):
    """
    打印汇总日志
    
    Args:
        logger: 日志器实例
        title: 汇总标题
        items: 汇总项列表
    """
    border = "-" * 50
    logger.info(border)
    logger.info(f"[SUMMARY] {title}")
    logger.info(border)
    for item in items:
        logger.info(item)