import schedule
import time
import datetime
from threading import Thread
from DB import DB
from model import predict_day, predict_hour


scheduler_started = False  # To avoid running it more than once


def predict(hourly=False):
    data = DB.get_data()
    if not data:
        return
    last_vals = DB.get_closest_predictions()
    now = datetime.datetime.now()
    result = None
    
    # For hourly predictions
    if hourly:
        # Use the previous hourly prediction if available, otherwise use daily or a default value
        previous_demand = last_vals.get('hourly') or last_vals.get('daily') or 100  # Default value if no previous predictions
        user_input = [previous_demand, data['temperature'],
                      data['humidity'], now.hour, now.day, now.month, now.year]
        result = predict_hour(user_input)
    # For daily predictions
    else:
        # Use the previous daily prediction if available, otherwise use hourly or a default value
        previous_demand = last_vals.get('daily') or last_vals.get('hourly') or 100  # Default value if no previous predictions
        user_input = [previous_demand, data['temperature'],
                      data['humidity'], now.day, now.month, now.year]
        result = predict_day(user_input)
        
    if result:
        DB.insert_data('predictions', {
            'type': 'hourly' if hourly else 'daily',
            'prediction': result,
        })


def give_hourly_prompt():
    print("[SCHEDULED] Hourly prediction triggered.")
    predict(hourly=True)


def give_daily_prompt():
    print("[SCHEDULED] Daily prediction triggered.")
    predict(hourly=False)


def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)


def start_auto_input():
    global scheduler_started
    if scheduler_started:
        return
    # Schedule the jobs only once
    schedule.every(1).hours.do(give_hourly_prompt)
    schedule.every(1).hours.do(give_daily_prompt)

    scheduler_thread = Thread(target=run_schedule)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    scheduler_started = True
