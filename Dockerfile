FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy
WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    build-essential \
    pkg-config \
    python3-dev \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp \
    -o /usr/local/bin/yt-dlp \
    && chmod a+rx /usr/local/bin/yt-dlp

COPY requirements.txt .
RUN pip install --no-cache-dir "Cython<3" setuptools
RUN pip install --no-cache-dir --no-build-isolation "av>=10,<11"
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY . .

RUN mkdir -p transcripts extractions output logs cookies

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
