# Use an official lightweight Python image
FROM python:3.10-slim

# Install system dependencies for PDF export (WeasyPrint)
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-cffi \
    python3-brotli \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Start the application using the existing run script
CMD ["python", "scripts/run_api.py", "--host", "0.0.0.0", "--port", "8000"]
