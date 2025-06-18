from flask import Flask, request, jsonify, render_template
from datetime import datetime
from DB import DB  # Your DB module
import pytz

# ✅ Must come before @app.route()
app = Flask(__name__)


@app.route('/latest-predictions', methods=['GET'])
def latest_predictions():
    try:
        last_p = DB.get_closest_predictions()
        return jsonify({
            "hourly": last_p['hourly'],
            "daily": last_p['daily'],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
