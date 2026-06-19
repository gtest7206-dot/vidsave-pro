FROM node:22-slim AS node
FROM python:3.10-slim

# Install system dependencies: ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
        && rm -rf /var/lib/apt/lists/*

        # Copy node binary from node image
        COPY --from=node /usr/local/bin/node /usr/local/bin/node

        # Set working directory
        WORKDIR /app

        # Install Python requirements
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        # Copy the rest of the application
        COPY . .

        # Expose port
        EXPOSE 5000

        # Run the server
        CMD ["python", "server.py"]
        
