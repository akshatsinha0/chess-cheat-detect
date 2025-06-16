# Dockerfile

# 1. Use a slim Python base image for minimal footprint
FROM python:3.10-slim

# 2. Set working directory
WORKDIR /app

# 3. Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the entire project into the container
COPY . .

# 5. Ensure the Stockfish binary is executable
RUN chmod +x bin/stockfish

# 6. Expose any required ports (if UI served over HTTP)
#    e.g., EXPOSE 5000

# 7. Set the default command to run the application
CMD ["python", "main.py"]
