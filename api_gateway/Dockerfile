# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the service code
COPY . .

# Expose the port for the API Gateway
EXPOSE 8000

# Command to run the API Gateway
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]