# Dockerfile

# 1. Use a slim Python base image for minimal footprint
FROM python:3.10-slim

# 2. Set working directory inside container
WORKDIR /app

# 3. Copy only dependency manifest first for layer caching
COPY requirements.txt .

# 4. Install Python dependencies without cache to keep image small
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy Stockfish binary and grant execute permissions
#    Adjust source filename to match your local binary under bin/stockfish
COPY bin/stockfish/stockfish-windows-x86-64-avx2.exe /app/bin/stockfish
RUN chmod +x /app/bin/stockfish

# 6. Copy remaining application source code
COPY . .

# 7. (Optional) Expose port if serving a web UI or API
# EXPOSE 5000

# 8. Default command to launch the application
CMD ["python", "main.py"]
