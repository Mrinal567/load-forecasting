# Use the official Python image as the base image
FROM python:3.9-slim

# Set environment variables to prevent Python from buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FLASK_ENV production


# Set the working directory inside the container
WORKDIR /app

COPY . .

# Install dependencies from the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app into the container

# Expose the port the Flask app runs on
EXPOSE 80

# Define the entry point for running the Flask app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:80", "main:app"]
# CMD ["python", "main.py"]
