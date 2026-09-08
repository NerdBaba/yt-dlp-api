#!/usr/bin/env python3
"""
yt-dlp REST API with auto-updates, rate limiting, and comprehensive YouTube data extraction.
"""

import os
import re
import subprocess
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import yt_dlp

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="yt-dlp REST API",
    description="Comprehensive YouTube data extraction API with auto-updates",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting storage
rate_limit_data: Dict[str, List[float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 10  # per window


class DownloadRequest(BaseModel):
    url: str
    format: str = Field(default="best", description="Video format (best, mp4, webm, etc.)")
    quality: str = Field(default="highest", description="Video quality")
    audio_only: bool = Field(default=False, description="Extract audio only")
    subtitles: bool = Field(default=True, description="Download subtitles if available")
    proxy: Optional[str] = Field(default=None, description="Proxy URL")


def check_rate_limit(client_ip: str) -> bool:
    """Check if client is rate limited."""
    now = datetime.now().timestamp()
    
    if client_ip not in rate_limit_data:
        rate_limit_data[client_ip] = []
    
    # Clean old entries
    rate_limit_data[client_ip] = [
        t for t in rate_limit_data[client_ip] 
        if now - t < RATE_LIMIT_WINDOW
    ]
    
    if len(rate_limit_data[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    rate_limit_data[client_ip].append(now)
    return True


def check_yt_dlp_update():
    """Check for yt-dlp updates."""
    try:
        result = subprocess.run(
            ["pip", "index", "versions", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            version_match = re.search(r'yt-dlp\(([\d.]+)\)', result.stdout)
            if version_match:
                latest_version = version_match.group(1)
                current_version = subprocess.run(
                    ["pip", "show", "yt-dlp"],
                    capture_output=True,
                    text=True
                )
                
                if latest_version not in current_version.stdout:
                    logger.info(f"Updating yt-dlp to version {latest_version}")
                    subprocess.run(
                        ["pip", "install", "--upgrade", "yt-dlp"],
                        check=True
                    )
    except Exception as e:
        logger.warning(f"Failed to check for yt-dlp updates: {e}")


async def periodic_update_check():
    """Periodically check for updates."""
    import asyncio
    while True:
        await asyncio.sleep(3600)  # 1 hour
        check_yt_dlp_update()


def extract_yt_data(url: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Extract data from YouTube using yt-dlp."""
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
        return info


@app.on_event("startup")
async def startup_event():
    """Initialize the application."""
    logger.info("Starting yt-dlp REST API...")
    check_yt_dlp_update()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "yt-dlp REST API",
        "version": "1.0.0",
        "description": "YouTube data extraction API with comprehensive features",
        "endpoints": {
            "download": "/download",
            "get-stream": "/get-stream",
            "subtitles": "/subtitles",
            "transcript": "/transcript",
            "info": "/info",
            "formats": "/formats"
        },
        "rate_limit": {
            "max_requests": RATE_LIMIT_MAX_REQUESTS,
            "window_seconds": RATE_LIMIT_WINDOW
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/download")
async def download_video(
    request: DownloadRequest,
    client_ip: Optional[str] = Query(default="127.0.0.1", description="Client IP for rate limiting")
):
    """Download and extract video data."""
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    try:
        ydl_options = {
            'quiet': True,
            'no_warnings': False,
            'extract_flat': False,
            'skip_download': True,
            'writesubtitles': request.subtitles,
            'subtitleslangs': ['en', 'en-US', 'en-GB', 'es', 'fr', 'de', 'ja', 'zh', 'zh-Hant', 'zh-Hans'],
            'subtitlesformat': 'srt',
            'forcejson': True,
        }
        
        if request.audio_only:
            ydl_options['format'] = 'bestaudio/best'
        else:
            # Use 'bestvideo' as default - yt-dlp will select best available
            ydl_options['format'] = request.format if request.format != "best" else "bestvideo"
        
        if request.proxy:
            ydl_options['proxy'] = request.proxy
        
        info = extract_yt_data(request.url, ydl_options)
        
        # Extract subtitles
        subtitles = {}
        if request.subtitles and info.get('subtitles'):
            for lang, subs in info['subtitles'].items():
                subtitles[lang] = [sub.get('url') for sub in subs if sub.get('url')]
        
        # Extract available formats
        formats = []
        if 'formats' in info:
            for fmt in info['formats']:
                if fmt.get('format_id') and fmt.get('ext'):
                    formats.append({
                        'format_id': fmt.get('format_id'),
                        'ext': fmt.get('ext'),
                        'resolution': fmt.get('resolution'),
                        'filesize': fmt.get('filesize'),
                        'filesize_approx': fmt.get('filesize_approx'),
                        'vcodec': fmt.get('vcodec'),
                        'acodec': fmt.get('acodec'),
                        'dynamic_range': fmt.get('dynamic_range'),
                        'container': fmt.get('container'),
                        'url': fmt.get('url'),
                    })
        
        return {
            "success": True,
            "video_id": info.get('id'),
            "title": info.get('title'),
            "duration": info.get('duration'),
            "formats": formats[:20],
            "subtitles": subtitles if subtitles else None
        }
        
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/get-stream")
async def get_stream_url(
    url: str = Query(..., description="YouTube URL"),
    format: str = Query(default="bestvideo+bestaudio/best", description="Video format"),
    client_ip: Optional[str] = Query(default="127.0.0.1", description="Client IP for rate limiting")
):
    """Get direct stream URL for YouTube video."""
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    try:
        ydl_options = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format': format if format != "best" else "bestvideo+bestaudio/best",
        }
        
        info = extract_yt_data(url, ydl_options)
        
        # Get best format URL
        best_format = None
        if 'formats' in info:
            for fmt in info['formats']:
                if fmt.get('url'):
                    best_format = fmt
                    break
        
        if not best_format or not best_format.get('url'):
            raise HTTPException(status_code=404, detail="No streamable format found")
        
        # Redirect to the stream URL
        return RedirectResponse(url=best_format['url'])
        
    except Exception as e:
        logger.error(f"Error streaming video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/subtitles")
async def get_subtitles(
    url: str = Query(..., description="YouTube URL"),
    languages: str = Query(default="en", description="Comma-separated language codes"),
    client_ip: Optional[str] = Query(default="127.0.0.1", description="Client IP for rate limiting")
):
    """Get YouTube subtitles."""
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    try:
        lang_list = [lang.strip() for lang in languages.split(',')]
        
        ydl_options = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': True,
            'subtitleslangs': lang_list,
            'subtitlesformat': 'srt',
        }
        
        info = extract_yt_data(url, ydl_options)
        
        subtitles = {}
        if info.get('subtitles'):
            for lang, subs in info['subtitles'].items():
                subtitles[lang] = []
                for sub in subs:
                    subtitles[lang].append({
                        'url': sub.get('url'),
                        'ext': sub.get('ext'),
                        'data': sub.get('data') if sub.get('data') else None
                    })
        
        return {
            "success": True,
            "video_id": info.get('id'),
            "title": info.get('title'),
            "subtitles": subtitles,
            "available_languages": list(info.get('subtitles', {}).keys()) if info.get('subtitles') else []
        }
        
    except Exception as e:
        logger.error(f"Error getting subtitles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/transcript")
async def get_transcript(
    url: str = Query(..., description="YouTube URL"),
    language: str = Query(default="en", description="Language code"),
    client_ip: Optional[str] = Query(default="127.0.0.1", description="Client IP for rate limiting")
):
    """Get video transcript."""
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    try:
        ydl_options = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': True,
            'subtitleslangs': [language],
            'subtitlesformat': 'srt',
            'writeautomaticsub': True,
        }
        
        info = extract_yt_data(url, ydl_options)
        
        transcript_text = ""
        languages_available = []
        
        if info.get('subtitles'):
            for lang, subs in info['subtitles'].items():
                languages_available.append(lang)
                if lang == language or language in lang:
                    for sub in subs:
                        if sub.get('data'):
                            transcript_text += sub['data'] + "\n"
        
        return {
            "success": True,
            "video_id": info.get('id'),
            "transcript": transcript_text if transcript_text else None,
            "languages": languages_available if languages_available else None
        }
        
    except Exception as e:
        logger.error(f"Error getting transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/info")
async def get_video_info(
    url: str = Query(..., description="YouTube URL"),
    client_ip: Optional[str] = Query(default="127.0.0.1", description="Client IP for rate limiting")
):
    """Get comprehensive video information."""
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    try:
        ydl_options = {
            'quiet': True,
            'no_warnings': False,
            'extract_flat': False,
            'skip_download': True,
            'writesubtitles': True,
            'subtitleslangs': ['en', 'en-US', 'en-GB'],
            'subtitlesformat': 'srt',
            'forcejson': True,
        }
        
        info = extract_yt_data(url, ydl_options)
        
        video_info = {
            'id': info.get('id'),
            'title': info.get('title'),
            'description': info.get('description'),
            'duration': info.get('duration'),
            'view_count': info.get('view_count'),
            'like_count': info.get('like_count'),
            'dislike_count': info.get('dislike_count'),
            'upload_date': info.get('upload_date'),
            'uploader': info.get('uploader'),
            'uploader_id': info.get('uploader_id'),
            'channel': info.get('channel'),
            'channel_id': info.get('channel_id'),
            'formats': [],
            'subtitles': {},
            'chapters': info.get('chapters'),
            'thumbnails': info.get('thumbnails'),
            'categories': info.get('categories'),
            'tags': info.get('tags'),
            'age_limit': info.get('age_limit'),
            'average_rating': info.get('average_rating'),
            'source_url': info.get('webpage_url'),
            'live_status': info.get('live_status'),
            'release_timestamp': info.get('release_timestamp'),
        }
        
        if 'formats' in info:
            for fmt in info['formats'][:30]:
                video_info['formats'].append({
                    'format_id': fmt.get('format_id'),
                    'ext': fmt.get('ext'),
                    'resolution': fmt.get('resolution'),
                    'filesize': fmt.get('filesize'),
                    'vcodec': fmt.get('vcodec'),
                    'acodec': fmt.get('acodec'),
                    'dynamic_range': fmt.get('dynamic_range'),
                })
        
        if info.get('subtitles'):
            for lang, subs in info['subtitles'].items():
                video_info['subtitles'][lang] = [sub.get('url') for sub in subs if sub.get('url')]
        
        if info.get('automatic_captions'):
            video_info['automatic_captions'] = {}
            for lang, subs in info['automatic_captions'].items():
                video_info['automatic_captions'][lang] = [sub.get('url') for sub in subs if sub.get('url')]
        
        return video_info
        
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/formats")
async def get_formats(
    url: str = Query(..., description="YouTube URL"),
    client_ip: Optional[str] = Query(default="127.0.0.1", description="Client IP for rate limiting")
):
    """Get available formats for a video."""
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    try:
        ydl_options = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        info = extract_yt_data(url, ydl_options)
        
        formats = []
        if 'formats' in info:
            for fmt in info['formats']:
                formats.append({
                    'format_id': fmt.get('format_id'),
                    'ext': fmt.get('ext'),
                    'resolution': fmt.get('resolution'),
                    'filesize': fmt.get('filesize'),
                    'filesize_approx': fmt.get('filesize_approx'),
                    'vcodec': fmt.get('vcodec'),
                    'acodec': fmt.get('acodec'),
                    'dynamic_range': fmt.get('dynamic_range'),
                    'container': fmt.get('container'),
                    'url': fmt.get('url'),
                    'is_dash': fmt.get('acodec') == 'none' or fmt.get('vcodec') == 'none',
                })
        
        return {
            "success": True,
            "video_id": info.get('id'),
            "title": info.get('title'),
            "formats": formats
        }
        
    except Exception as e:
        logger.error(f"Error getting formats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
