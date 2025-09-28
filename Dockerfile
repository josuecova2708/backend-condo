FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies including CMake and OpenCV dependencies
# Install system dependencies
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


# Install Python dependencies
COPY requirements.txt .

# First install OpenCV from system packages to avoid compilation
RUN pip install --no-cache-dir opencv-python-headless

# Then install the rest of dependencies
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create staticfiles directory
RUN mkdir -p staticfiles

# Make start script executable
RUN chmod +x start.sh

# Expose port (Railway will override this with $PORT)
EXPOSE $PORT

# Use start script
CMD ["./start.sh"]