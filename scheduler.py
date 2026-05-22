"""
定时调度器模块

每周一、周五早上9:30执行主流程
"""

import schedule
import time
import threading
from datetime import datetime
from src.pipeline import Pipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_pipeline():
    """执行主流程"""
    logger.info("=" * 60)
    logger.info(f"Scheduled pipeline started at {datetime.now()}")
    logger.info("=" * 60)
    try:
        pipeline = Pipeline()
        pipeline.run()
        logger.info("=" * 60)
        logger.info(f"Scheduled pipeline completed at {datetime.now()}")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")


def job_wrapper():
    """包装任务运行在独立线程中"""
    thread = threading.Thread(target=run_pipeline, daemon=True)
    thread.start()


def setup_schedule():
    """设置调度任务"""
    schedule.every().monday.at("09:28").do(job_wrapper)
    schedule.every().friday.at("09:28").do(job_wrapper)
    logger.info("Schedule configured: Monday and Friday at 09:28")


def run_scheduler():
    """运行调度器"""
    setup_schedule()
    logger.info("Scheduler started, waiting for scheduled tasks...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == '__main__':
    run_scheduler()
