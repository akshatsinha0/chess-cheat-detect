# Dockerfile

# 1. Use a minimal Python base image
FROM python:3.10-slim

# 2. Set working directory
WORKDIR /app

# 3. Install system libraries required by OpenCV
RUN apt-get update && \
    apt-get install -y libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# 4. Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy Linux-native Stockfish binary and grant execute permissions
COPY bin/stockfish/stockfish-ubuntu-x86-64-avx2 /app/engine/stockfish
RUN chmod +x /app/engine/stockfish

# 6. Copy trained anomaly detection model
COPY models/ /app/models/

# 7. Copy application source code
COPY . .

# 8. Default command to launch the application
CMD ["python", "main.py"]
