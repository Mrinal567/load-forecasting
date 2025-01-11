from flask import Flask, request, jsonify, render_template
from datetime import datetime
from DB import DB
from model import predict_day, predict_hour

app = Flask(__name__)

# Initialize the database connection
DB.init()

@app.route("/")
def home():
    # Get the current date and time
    now = datetime.now()
    data = DB.get_data()
    return render_template(
        "index.html",
        year=now.year,
        month=now.month,
        day=now.day,
        hour=now.hour,
        humidity=data['humidity'],
        temperature=data['temperature'],
    )

@app.route('/insert', methods=['POST'])
def insert_data():
    try:
        humidity = request.form.get('humidity')
        temperature = request.form.get('temperature')
        device_id = request.form.get('device_id')

        if not humidity or not temperature or not device_id:
            return jsonify({"error": "table_name and data are required"}), 400

        inserted_id = DB.insert_data('readings', {
            'temperature': temperature,
            'humidity': humidity,
            'device_id': device_id
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
    temparature = request.form.get('temperature')
    humidity = request.form.get('humidity')

    try:
        if hour:
            user_input = [nldc_demand, temparature, humidity, hour, day, month, year]
            prediction = predict_hour(user_input)
        else:
            user_input = [nldc_demand, temparature, humidity, day, month, year]
            prediction = predict_day(user_input)
        return jsonify({"prediction": prediction}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port="80")
