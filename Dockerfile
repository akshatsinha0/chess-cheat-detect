FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && \
    apt-get install -y libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bin/stockfish/stockfish-ubuntu-x86-64-avx2 /app/engine/stockfish
RUN chmod +x /app/engine/stockfish
COPY models/ /app/models/
COPY . .
CMD ["python", "main.py"]
