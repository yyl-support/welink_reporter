"""
定时调度器模块

每周一、周五早上9:30执行主流程
"""

import os
import schedule
import time
import threading
from datetime import datetime
from src.pipeline import Pipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_data_sync():
    """执行数据同步"""
    logger.info("=" * 60)
    logger.info(f"Scheduled data sync started at {datetime.now()}")
    logger.info("=" * 60)
    try:
        from src.config.loader import ConfigLoader
        from src.services.data_sync_service import sync_data_from_google_sheets
        
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'config.yaml'
        )
        loader = ConfigLoader()
        config = loader.load(config_path)
        
        excel_url = loader.get_excel_url(config)
        excel_gid = loader.get_excel_gid(config)
        
        result = sync_data_from_google_sheets(excel_url, excel_gid)
        
        logger.info(f"Data sync completed: {result}")
        logger.info("=" * 60)
        logger.info(f"Scheduled data sync finished at {datetime.now()}")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Data sync failed: {e}")


def data_sync_wrapper():
    """包装数据同步任务运行在独立线程中"""
    thread = threading.Thread(target=run_data_sync, daemon=True)
    thread.start()


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
    from src.config.loader import ConfigLoader
    
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'config.yaml'
    )
    loader = ConfigLoader()
    config = loader.load(config_path)
    
    sync_config = loader.get_data_sync_config(config)
    
    schedule.every().monday.at("09:28").do(job_wrapper)
    schedule.every().friday.at("09:28").do(job_wrapper)
    logger.info("Schedule configured: Monday and Friday at 09:28")
    
    if sync_config.get('enabled', True):
        sync_day = sync_config.get('schedule', {}).get('day', 'wednesday')
        sync_time = sync_config.get('schedule', {}).get('time', '20:00')
        
        scheduler = getattr(schedule.every(), sync_day.lower(), None)
        if scheduler:
            scheduler.at(sync_time).do(data_sync_wrapper)
            logger.info(f"Data sync scheduled: {sync_day} at {sync_time}")
        else:
            logger.warning(f"Invalid sync day: {sync_day}")
    else:
        logger.info("Data sync is disabled in config")


def run_scheduler():
    """运行调度器"""
    setup_schedule()
    logger.info("Scheduler started, waiting for scheduled tasks...")
    
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == '__main__':
    run_scheduler()
