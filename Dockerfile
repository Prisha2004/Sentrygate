FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download FastEmbed model during build for instant startup
RUN python3 -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"

# Copy application files
COPY . .

# Hugging Face Spaces expects port 7860
EXPOSE 7860

# Start the server on port 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]