from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for, g
from functools import wraps
import os
from datetime import datetime
from threading import Thread
import pytz
import pandas as pd
from io import BytesIO
from DB import DB
from auto_input import start_auto_input
from model import predict_day, predict_hour

app = Flask(__name__)

# Secret key for session management
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_testing')

# Admin credentials
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '@dmin')

# Login decorator


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def is_admin():
    return 'user' in session and session['user'] == ADMIN_USERNAME


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    next_url = request.args.get('next', '/')
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['user'] = username
            return redirect(next_url)
        else:
            error = 'Invalid credentials'
    return render_template('login.html', error=error, next_url=next_url)


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))


# Initialize the database
DB.init()
TIMEZONE = pytz.timezone('Asia/Dhaka')


@app.route("/")
def home():
    now = datetime.now(TIMEZONE)
    data = DB.get_data()
    last_p = DB.get_closest_predictions()
    all_predictions = DB.get_predictions() or []

    hourly_predictions = [
        p for p in all_predictions if p['type'] == 'hourly'][:25]
    daily_predictions = [
        p for p in all_predictions if p['type'] == 'daily'][:25]
    default_value = 100

    return render_template(
        "index.html",
        year=now.year,
        month=now.month,
        day=now.day,
        hour=now.hour,
        humidity=data['humidity'],
        temperature=data['temperature'],
        history_hourly=hourly_predictions,
        history_daily=daily_predictions,
        last_hour=last_p.get('hourly') or default_value,
        last_day=last_p.get('daily') or default_value,
        is_admin=is_admin()
    )


@app.route("/check")
def check_scheduler():
    return jsonify({"status": "Scheduler running (if you see this, app loaded successfully)"}), 200


@app.route('/insert', methods=['POST'])
def insert_data():
    try:
        humidity = request.form.get('humidity')
        temperature = request.form.get('temperature')
        device_id = request.form.get('device_id')

        if not humidity or not temperature or not device_id:
            return jsonify({"error": "humidity, temperature, and device_id are required"}), 400

        inserted_id = DB.insert_data('readings', {
            'temperature': temperature,
            'humidity': humidity,
            'device_id': device_id,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        if inserted_id:
            return jsonify({"message": "Data inserted successfully", "id": inserted_id}), 201
        else:
            return jsonify({"error": "Failed to insert data"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/predict', methods=['POST'])
def predict():
    hour = request.form.get('hour')
    day = request.form.get('day')
    month = request.form.get('month')
    year = request.form.get('year')
    nldc_demand = request.form.get('demand')
    temperature = request.form.get('temperature')
    humidity = request.form.get('humidity')

    try:
        if hour:
            user_input = [
                float(nldc_demand),
                float(temperature),
                float(humidity),
                float(hour),
                float(day),
                float(month),
                float(year)
            ]
            prediction = predict_hour(user_input)
        else:
            user_input = [
                float(nldc_demand),
                float(temperature),
                float(humidity),
                float(day),
                float(month),
                float(year)
            ]
            prediction = predict_day(user_input)

        inserted_id = DB.insert_data('predictions', {
            'type': 'hourly' if hour else 'daily',
            'prediction': float(prediction),
        })

        return jsonify({
            "prediction": float(prediction),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/readings', methods=['GET'])
def get_readings():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        sort_by = request.args.get('sort_by', 'timestamp')
        order = request.args.get('order', 'desc')
        device_id = request.args.get('device_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        filters = {}
        if device_id:
            filters['device_id'] = device_id
        if start_date:
            filters['timestamp__gte'] = start_date + " 00:00:00"
        if end_date:
            filters['timestamp__lte'] = end_date + " 23:59:59"

        readings = DB.get_paginated_data(
            table='readings',
            filters=filters,
            sort_by=sort_by,
            order=order,
            page=page,
            limit=limit
        )

        return jsonify({"page": page, "limit": limit, "data": readings}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def format_datetime(value, format="%Y-%m-%d %H:%M"):
    if not isinstance(value, datetime):
        value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    value = value.replace(tzinfo=pytz.utc).astimezone(TIMEZONE)
    return value.strftime(format)


app.jinja_env.filters['strftime'] = format_datetime


@app.route('/export-predictions', methods=['POST'])
@login_required
def export_predictions():
    try:
        prediction_type = request.form.get('type')
        if prediction_type not in ['hourly', 'daily']:
            return jsonify({"error": "Invalid prediction type"}), 400

        all_predictions = DB.get_predictions()
        filtered_predictions = [
            p for p in all_predictions if p['type'] == prediction_type]

        if not filtered_predictions:
            return jsonify({"error": "No predictions found for the selected type"}), 404

        df = pd.DataFrame(filtered_predictions)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        timestamps = [p['timestamp'] for p in filtered_predictions]
        readings_data = DB.get_readings_for_timestamps(timestamps)

        temperature_values = []
        humidity_values = []

        for timestamp in timestamps:
            reading = readings_data.get(
                timestamp, {'temperature': None, 'humidity': None})
            temperature_values.append(reading['temperature'])
            humidity_values.append(reading['humidity'])

        df['temperature'] = temperature_values
        df['humidity'] = humidity_values
        df['formatted_date'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
        df['prediction'] = df['prediction'].round(2)

        df = df[['formatted_date', 'type',
                 'humidity', 'temperature', 'prediction']]
        df.columns = ['Date', 'Type', 'Humidity', 'Temperature', 'Prediction']

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False,
                        sheet_name=f'{prediction_type.capitalize()} Predictions')
            worksheet = writer.sheets[f'{prediction_type.capitalize()} Predictions']
            for idx, cell in enumerate(worksheet['E'][1:], 2):
                cell.number_format = '0.00'

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'{prediction_type}_predictions.xlsx'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Start scheduler always
start_auto_input()

# Start Flask server only if running directly
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=3000)
