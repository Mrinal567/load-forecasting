#!/usr/bin/env python
"""
Standalone scheduler process for auto predictions.
Run this separately from the web application.
"""
import time
import logging
from DB import DB
from auto_input import start_auto_input

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('scheduler')
    
    # Initialize database
    logger.info("Initializing database...")
    DB.init()
    
    # Start the scheduler
    logger.info("Starting auto-prediction scheduler...")
    scheduler_thread = start_auto_input()
    logger.info(f"Scheduler thread started: {scheduler_thread.name}")
    
    # Keep the process running
    try:
        while True:
            time.sleep(60)
            logger.info("Scheduler process still running...")
    except KeyboardInterrupt:
        logger.info("Scheduler process terminated by user")