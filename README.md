# yt-dlp REST API

A comprehensive REST API for YouTube video data extraction using yt-dlp, designed for containerized deployment with auto-updates.

## Features

- **Comprehensive YouTube Data**: Video info, subtitles, transcripts, and stream links
- **Auto-updates**: yt-dlp automatically checks for updates hourly
- **Rate Limiting**: Built-in rate limiting to prevent abuse (10 requests per 60 seconds by default)
- **Docker-ready**: Optimized for containerized deployment
- **Render-ready**: Pre-configured for deployment on Render.com

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information and available endpoints |
| `/health` | GET | Health check endpoint |
| `/download` | POST | Download video data with subtitles |
| `/get-stream` | GET | Get direct stream URL for video |
| `/subtitles` | GET | Get available subtitles |
| `/transcript` | GET | Get video transcript/closed captions |
| `/info` | GET | Get comprehensive video information |
| `/formats` | GET | Get available video formats |

## Configuration

The following environment variables can be set:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8080` | Server port |
| `AUTO_UPDATE_ENABLED` | `true` | Enable automatic yt-dlp updates |
| `UPDATE_CHECK_INTERVAL` | `3600` | Update check interval in seconds |
| `LOG_LEVEL` | `INFO` | Logging level |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |
| `RATE_LIMIT_MAX_REQUESTS` | `10` | Maximum requests per window |

## Deployment

### Local with Docker

```bash
docker-compose up -d
```

### Local with Docker (direct)

```bash
docker build -t yt-dlp-api .
docker run -p 8080:8080 -d yt-dlp-api
```

### Render.com

1. Fork this repository
2. Go to [Render.com](https://render.com) and create a new "Web Service"
3. Connect your repository
4. Set the build command: `pip install -r requirements.txt`
5. Set the start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
6. Add environment variables as needed
7. Deploy

### Render with Docker

1. Create a new "Web Service" on Render
2. Choose "Docker" as the type
3. Connect your repository
4. Set the start command: `uvicorn app:app --host 0.0.0.0 --port 8080`
5. Add environment variables
6. Deploy

### With uv (Development)

```bash
cd yt-dlp-backend
uv run app.py
```

## Usage Examples

### Get Video Info

```bash
curl "http://localhost:8080/info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Download Video with Subtitles

```bash
curl -X POST "http://localhost:8080/download" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "subtitles": true}'
```

### Get Subtitles

```bash
curl "http://localhost:8080/subtitles?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&languages=en,es"
```

### Get Transcript

```bash
curl "http://localhost:8080/transcript?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&language=en"
```

### Get Available Formats

```bash
curl "http://localhost:8080/formats?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Get Stream URL (Redirect)

```bash
curl -L "http://localhost:8080/get-stream?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&format=mp4"
```

## Rate Limiting

The API implements rate limiting to prevent abuse. Default settings:
- 10 requests per 60 seconds per IP
- Returns HTTP 429 when rate limit is exceeded

Rate limits can be configured via environment variables:
- `RATE_LIMIT_WINDOW`: Time window in seconds
- `RATE_LIMIT_MAX_REQUESTS`: Maximum requests per window

## Auto-Updates

The API automatically checks for yt-dlp updates every hour and installs them if available. This can be disabled by setting `AUTO_UPDATE_ENABLED=false`.

## Requirements

- Python 3.11+
- FFmpeg (for video processing)
- Docker (for containerized deployment)
- uv (for development)

## License

MIT
