# Antigravity Agentic Skills Repository

This repository contains custom, non-native skills for the Antigravity Agentic OS. These skills extend the agent's capabilities to natively parse user intent and trigger advanced workflows (e.g., streaming media, TTS, etc.) directly on the user's machine.

## Skills Included

### 1. JIT Media Gateway (`jit-media-gateway`)
A natural language media router that parses user intent for movies, anime, music, manga, and live TV (IPTV), resolves the media ID via TMDB/Anilist, and outputs the embedded media player natively or orchestrates `mpv` for playback.
- **Dependencies**: 
  - Python 3.10+
  - `mpv` (for native video/audio streaming)
  - `yt-dlp` (for YouTube live stream resolution)
  - `requests` (Python package)

### 2. Newsmth TTS (`newsmth-tts`)
A TTS engine skill that parses newsmth.net (水木社区) forum thread URLs, cleans the quoted text, and generates a spoken audio summary using `edge-tts`.
- **Dependencies**:
  - Python 3.10+
  - `edge-tts` (Python package / CLI)
  - `mpv` (for playing the generated MP3)
  - `beautifulsoup4` (Python package for HTML parsing)

## Installation

1. Clone this repository directly into the Gemini skills directory:
   ```bash
   git clone https://github.com/syu-toutousai/agentic-skills.git ~/.gemini/skills/
   ```

2. Ensure all system dependencies are installed:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install mpv yt-dlp
   # macOS
   brew install mpv yt-dlp
   ```

3. Install Python dependencies:
   ```bash
   pip install requests edge-tts beautifulsoup4
   ```

4. **Environment Variables**:
   Navigate to the `jit-media-gateway/scripts` directory and copy the template `.env.example` file to `.env`:
   ```bash
   cd ~/.gemini/skills/jit-media-gateway/scripts
   cp .env.example .env
   ```
   Fill in your actual API keys (e.g., TMDB, SoundCloud, HuggingFace) inside the `.env` file.

## Usage
These skills are automatically loaded by the Antigravity engine upon startup. Simply prompt the agent in natural language (e.g., "Play Naruto" or "Read this newsmth thread").
