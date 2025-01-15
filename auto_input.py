import schedule
import time
import datetime
from threading import Thread
from DB import DB
from model import predict_day, predict_hour

def predict(hourly = False):
    data = DB.get_data()
    if not data:
        return
    last_vals = DB.get_closest_predictions()
    now = datetime.now()
    if hourly and last_vals['hourly']:
        user_input = [last_vals['hourly'], data['temperature'], data['humidity'], now.hour, now.day, now.month, now.year]
        result = predict_hour(user_input)
    elif not hourly and last_vals['daily']:
        user_input = [last_vals['daily'], data['temperature'], data['humidity'], now.day, now.month, now.year]
        result = predict_day([0, 0, 0, now.day, now.month, now.year])
    if result:
        DB.insert_data('predictions', {
            'type': 'hourly' if hourly else 'daily',
            'prediction': result,
        })

def give_hourly_prompt():
    predict(hourly = True)
    
def give_daily_prompt():
    predict(hourly = False)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

schedule.every(1).hours.do(give_hourly_prompt)
schedule.every(1).days.do(give_daily_prompt)

def start_auto_input():
    scheduler_thread = Thread(target=run_schedule)
    scheduler_thread.daemon = True  
    scheduler_thread.start()
