# Use official Python base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt to the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the container
COPY toggle.py .

# Make sure the script is executable
RUN chmod +x toggle.py

# Set the entry point to the Python script
ENTRYPOINT ["python3", "toggle.py"]
