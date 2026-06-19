FROM python:3.10-slim

# Install system dependencies: ffmpeg, nodejs (for yt-dlp JS challenge solving)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python requirements (yt-dlp[default] includes bundled EJS solver scripts)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 5000

# Run the server
CMD ["python", "server.py"]
