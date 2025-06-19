import schedule
import time
import datetime
import logging
from threading import Thread
from DB import DB
from model import predict_day, predict_hour

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('auto_input')


def predict(hourly=False):
    """Make a prediction based on current data"""
    logger.info(f"Auto-input predict called with hourly={hourly}")

    # Get current sensor data
    try:
        data = DB.get_data()
        if not data:
            logger.warning("No data returned from DB.get_data()")
            return

        if data['temperature'] is None or data['humidity'] is None:
            logger.warning(f"Missing temperature or humidity data: {data}")
            return

        logger.info(
            f"Current sensor data: temperature={data['temperature']}, humidity={data['humidity']}")
    except Exception as e:
        logger.error(f"Error getting sensor data: {str(e)}")
        return

    # Get previous predictions
    try:
        last_vals = DB.get_closest_predictions() or {}
        logger.info(f"Last prediction values: {last_vals}")
    except Exception as e:
        logger.error(f"Error getting previous predictions: {str(e)}")
        last_vals = {}

    now = datetime.datetime.now()
    logger.info(f"Current time: {now}")

    try:
        # For hourly predictions
        if hourly:
            # Use a default value if no previous prediction is available
            previous_demand = last_vals.get(
                'hourly') or last_vals.get('daily') or 100

            user_input = [
                float(previous_demand),
                float(data['temperature']),
                float(data['humidity']),
                float(now.hour),
                float(now.day),
                float(now.month),
                float(now.year)
            ]
            logger.info(f"Hourly prediction input: {user_input}")
            result = predict_hour(user_input)
        # For daily predictions
        else:
            # Use a default value if no previous prediction is available
            previous_demand = last_vals.get(
                'daily') or last_vals.get('hourly') or 100

            user_input = [
                float(previous_demand),
                float(data['temperature']),
                float(data['humidity']),
                float(now.day),
                float(now.month),
                float(now.year)
            ]
            logger.info(f"Daily prediction input: {user_input}")
            result = predict_day(user_input)

        if result is not None:
            logger.info(
                f"Prediction result: {result} ({'hourly' if hourly else 'daily'})")

            # Insert into database
            try:
                inserted_id = DB.insert_data('predictions', {
                    'type': 'hourly' if hourly else 'daily',
                    'prediction': float(result),
                })
                logger.info(
                    f"Inserted prediction into database with ID: {inserted_id}")
            except Exception as e:
                logger.error(
                    f"Error inserting prediction into database: {str(e)}")
        else:
            logger.warning("Prediction returned None")
    except Exception as e:
        logger.error(f"Error in auto_input prediction: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


def give_hourly_prompt():
    """Wrapper function for hourly predictions"""
    try:
        logger.info("Running scheduled hourly prediction")
        predict(hourly=True)
    except Exception as e:
        logger.error(f"Error in hourly prediction scheduler: {str(e)}")


def give_daily_prompt():
    """Wrapper function for daily predictions"""
    try:
        logger.info("Running scheduled daily prediction")
        predict(hourly=False)
    except Exception as e:
        logger.error(f"Error in daily prediction scheduler: {str(e)}")


def run_schedule():
    """Run the scheduler loop"""
    logger.info("Scheduler thread started")

    # Clear any existing jobs
    schedule.clear()

    # Schedule jobs
    schedule.every(1).hour.at(":33").do(give_hourly_prompt)  # Run hourly predictions every hour
    schedule.every().day.at("00:00").do(give_daily_prompt)   # Run daily predictions at midnight

    logger.info("Jobs scheduled: hourly predictions every hour and daily predictions every day")

    # Remove these lines to prevent immediate predictions on startup
    # logger.info("Running initial predictions")
    # give_hourly_prompt()
    # give_daily_prompt()

    # Main scheduler loop
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in scheduler loop: {str(e)}")
            # Don't exit the loop on error, just continue


def start_auto_input():
    """Start the auto-input scheduler in a separate thread"""
    try:
        logger.info("Starting auto-input scheduler")
        scheduler_thread = Thread(target=run_schedule)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        logger.info(f"Scheduler thread started: {scheduler_thread.name}")
        return scheduler_thread
    except Exception as e:
        logger.error(f"Failed to start scheduler thread: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
