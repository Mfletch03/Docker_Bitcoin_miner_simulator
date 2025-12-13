# Use a lightweight Python base image
FROM python:3.12-alpine

# Environment setup — unbuffered logging and no .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:${PATH}"

# Create and activate virtual environment
RUN python -m venv /opt/venv && pip install --upgrade pip

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python source files
COPY *.py .

# Expose ports (for MQTT, optional)
EXPOSE 1883 9001

# Run miner with unbuffered output
CMD ["python", "-u", "CC2.py"]
