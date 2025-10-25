FROM python:3.11-slim

# Keep Python output unbuffered
ENV PYTHONUNBUFFERED=1
# Ensure Tesseract binary path (can be overridden by environment / Render)
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV PORT=8000

# Install system dependencies required for tesseract, opencv wheel and pdf support
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    poppler-utils \
    build-essential \
    pkg-config \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install python dependencies (use --no-cache-dir to reduce image size)
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Default command (for production remove --reload)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]