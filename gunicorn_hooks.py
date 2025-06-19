"""
Gunicorn hooks for starting the scheduler
"""
import threading
from auto_input import start_auto_input
import logging
from DB import DB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gunicorn_hooks')

# Global variable to track if scheduler is running
scheduler_running = False
scheduler_lock = threading.Lock()

def on_starting(server):
    """Called just before the master process is initialized"""
    logger.info("Gunicorn starting")
    
    # Initialize database
    logger.info("Initializing database...")
    DB.init()

def when_ready(server):
    """Called just after the server is started"""
    global scheduler_running
    
    with scheduler_lock:
        if not scheduler_running:
            logger.info("Starting auto-prediction scheduler from Gunicorn hook")
            try:
                # Use non-daemon thread in production
                scheduler_thread = start_auto_input(daemon=False)
                scheduler_running = True
                logger.info(f"Auto-prediction scheduler started: {scheduler_thread.name}")
            except Exception as e:
                logger.error(f"Error starting scheduler: {e}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.info("Scheduler already running, skipping initialization")

