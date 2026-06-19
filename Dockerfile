FROM python:3.10-slim

# Install system dependencies including ffmpeg and nodejs
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    nodejs \
    npm \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno (yt-dlp's preferred JS runtime for signature solving)
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"

# Set working directory
WORKDIR /app

# Install Python requirements (includes yt-dlp[default] with EJS scripts)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-fetch the yt-dlp EJS challenge solver scripts from GitHub
RUN python -m yt_dlp --update-to nightly 2>/dev/null || true
RUN python -c "import yt_dlp; ydl = yt_dlp.YoutubeDL({'remote_components': ['ejs:github'], 'quiet': True}); print('EJS scripts ready')" 2>/dev/null || true

# Copy the rest of the application
COPY . .

# Expose port (Render will override this, but it's good practice)
EXPOSE 5000

# Run the server using python
CMD ["python", "server.py"]
