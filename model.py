from tensorflow.keras.models import load_model
import numpy as np
import joblib
import os

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")  # Get the directory of the current file
lstm_model_hr_path = os.path.join(MODEL_DIR, "lstm_model.h5")
lstm_model_day_path = os.path.join(MODEL_DIR, "lstm_model_1.h5")
scaler_hr_path = os.path.join(MODEL_DIR, "scaler_1.pkl")
scaler_day_path = os.path.join(MODEL_DIR, "scaler.pkl")

lstm_model_hr = load_model(lstm_model_hr_path)
lstm_model_day = load_model(lstm_model_hr_path)
scaler_hr = joblib.load(scaler_hr_path)
scaler_day = joblib.load(scaler_day_path)


def predict_hour(user_input):
    user_input = np.array(user_input).reshape(1, 7)
    user_input_scaled = scaler_hr.transform(user_input)
    user_input_scaled = user_input_scaled.reshape(1, 1, 7)
    prediction_scaled = lstm_model_hr.predict(user_input_scaled)
    predicted_data = np.concatenate((prediction_scaled.reshape(1, 1), user_input_scaled[0, 0, 1:].reshape(1, 6)), axis=1)
    predicted_data = predicted_data.reshape(1, 7)
    nldc_demand_predicted = scaler_hr.inverse_transform(predicted_data)
    return nldc_demand_predicted[0][0]


def predict_day(user_input):
    
    # Prepare the input data (without the 'hour' variable)
    user_input = np.array(user_input).reshape(1, 6)

    # Scale the input data
    user_input_scaled = scaler_day.transform(user_input)
    user_input_scaled = user_input_scaled.reshape(1, 1, 6)  # Adjust shape for LSTM input

    # Predict NLDC Demand
    prediction_scaled = lstm_model_day.predict(user_input_scaled)

    # Combine the prediction with the other features for inverse scaling
    # The prediction corresponds to the first feature (NLDC Demand)
    predicted_data = np.concatenate((prediction_scaled.reshape(1, 1), user_input_scaled[0, 0, 1:].reshape(1, 5)), axis=1)

    # Reshape the prediction result for inverse scaling
    predicted_data = predicted_data.reshape(1, 6)
    nldc_demand_predicted = scaler_day.inverse_transform(predicted_data)

    # Extract and display the predicted NLDC Demand
    return nldc_demand_predicted[0][0]
