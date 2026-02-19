FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies including CMake and OpenCV dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        cmake \
        libopencv-dev \
        python3-opencv \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
# Primero instalamos OpenCV para evitar compilación
RUN pip install --no-cache-dir opencv-python-headless==4.8.1.78 \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install "numpy<2"  # 👈 fuerza numpy 1.x para compatibilidad con dlib

# Copy project
COPY . .

# Create staticfiles and media directories
RUN mkdir -p staticfiles media

# Make start script executable
RUN chmod +x start.sh

# Expose port 8000 (Coolify routes traffic to this port)
EXPOSE 8000

# Use start script
CMD ["./start.sh"]
