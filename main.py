from flask import Flask, request, jsonify, render_template, send_file
from datetime import datetime
from DB import DB
from auto_input import start_auto_input
from model import predict_day, predict_hour
import pytz
import os
from threading import Thread
import pandas as pd
from io import BytesIO

app = Flask(__name__)

# Initialize the database connection
DB.init()

TIMEZONE = pytz.timezone('Asia/Dhaka')


@app.route("/")
def home():
    now = datetime.now(TIMEZONE)
    data = DB.get_data()
    last_p = DB.get_closest_predictions()
    all_predictions = DB.get_predictions()

    hourly_predictions = [
        p for p in all_predictions if p['type'] == 'hourly'][:25]
    daily_predictions = [
        p for p in all_predictions if p['type'] == 'daily'][:25]

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
        last_hour=last_p['hourly'],
        last_day=last_p['daily'],
    )


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
            user_input = [nldc_demand, temperature,
                          humidity, hour, day, month, year]
            prediction = predict_hour(user_input)
        else:
            user_input = [nldc_demand, temperature, humidity, day, month, year]
            prediction = predict_day(user_input)

        DB.insert_data('predictions', {
            'type': 'hourly' if hour else 'daily',
            'prediction': prediction,
        })
        return jsonify({"prediction": prediction, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}), 200
    except Exception as e:
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
def export_predictions():
    try:
        prediction_type = request.form.get('type')
        if prediction_type not in ['hourly', 'daily']:
            return jsonify({"error": "Invalid prediction type"}), 400
            
        # Get all predictions of the specified type
        all_predictions = DB.get_predictions()
        filtered_predictions = [p for p in all_predictions if p['type'] == prediction_type]
        
        if not filtered_predictions:
            return jsonify({"error": "No predictions found for the selected type"}), 404
        
        # Create DataFrame
        df = pd.DataFrame(filtered_predictions)
        
        # Format timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Get actual temperature and humidity for each prediction timestamp
        timestamps = [p['timestamp'] for p in filtered_predictions]
        readings_data = DB.get_readings_for_timestamps(timestamps)
        
        # Add temperature and humidity to DataFrame
        temperature_values = []
        humidity_values = []
        
        for timestamp in timestamps:
            reading = readings_data.get(timestamp, {'temperature': None, 'humidity': None})
            temperature_values.append(reading['temperature'])
            humidity_values.append(reading['humidity'])
        
        df['temperature'] = temperature_values
        df['humidity'] = humidity_values
        df['formatted_date'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
        
        # Round prediction to 2 decimal places
        df['prediction'] = df['prediction'].round(2)
        
        # Select and rename columns
        df = df[['formatted_date', 'type', 'humidity', 'temperature', 'prediction']]
        df.columns = ['Date', 'Type', 'Humidity', 'Temperature', 'Prediction']
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=f'{prediction_type.capitalize()} Predictions')
            
            # Access the worksheet to format the prediction column
            worksheet = writer.sheets[f'{prediction_type.capitalize()} Predictions']
            for idx, cell in enumerate(worksheet['E'][1:], 2):  # Column E is Prediction, start from row 2 (skip header)
                cell.number_format = '0.00'
        
        output.seek(0)
        
        # Return the Excel file
        return send_file(
            output, 
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'{prediction_type}_predictions.xlsx'
        )
    except Exception as e:
        print(f"Export error: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Start scheduler only if not in reloader
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        Thread(target=start_auto_input, daemon=True).start()

    app.run(debug=True, host="0.0.0.0", port=3000)
