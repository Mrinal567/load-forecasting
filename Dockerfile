# Use the official Python image as the base image
FROM python:3.9-slim

# Set environment variables to prevent Python from buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install dependencies from the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app into the container
COPY . /app

# Expose the port the Flask app runs on
EXPOSE 80

# Define the entry point for running the Flask app
CMD ["python", "main.py"]
