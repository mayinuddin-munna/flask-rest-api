# Use an official Python runtime as base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the application code
COPY app.py .

# Install Flask
RUN pip install --no-cache-dir flask

# Expose port 5000 (the port your Flask app runs on)
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]