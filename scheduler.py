#!/usr/bin/env python
"""
Standalone scheduler process for auto predictions.
Run this separately from the web application.
"""
import time
import logging
import os
import pytz
from datetime import datetime
from DB import DB
from auto_input import start_auto_input, predict

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler('/tmp/scheduler.log')  # Log to file
    ]
)
logger = logging.getLogger('scheduler')

if __name__ == "__main__":
    # Print environment info
    logger.info(f"Starting scheduler process, PID: {os.getpid()}")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"Current time: {datetime.now()}")
    
    # Initialize database
    logger.info("Initializing database...")
    try:
        DB.init()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Test database connection
    try:
        data = DB.get_data()
        logger.info(f"Database test query result: {data}")
    except Exception as e:
        logger.error(f"Database test query failed: {str(e)}")
    
    # Start the scheduler
    logger.info("Starting auto-prediction scheduler...")
    try:
        # Non-daemon thread to prevent premature termination
        scheduler_thread = start_auto_input(daemon=False)
        logger.info(f"Scheduler thread started: {scheduler_thread.name}")
        
        # Run a test prediction to verify everything works
        logger.info("Running test predictions...")
        try:
            predict(hourly=True)
            predict(hourly=False)
            logger.info("Test predictions completed successfully")
        except Exception as e:
            logger.error(f"Test prediction failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Keep the process running
        while True:
            time.sleep(60)
            logger.info(f"Scheduler process still running... Time: {datetime.now()}")
            logger.info(f"Scheduler thread alive: {scheduler_thread.is_alive()}")
    except Exception as e:
        logger.error(f"Error in scheduler main loop: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

