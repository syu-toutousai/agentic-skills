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

## 🤖 Universal Agentic Compatibility
This repository is designed to be **Agent-Agnostic**. Whether you are running **AutoGPT, OpenInterpreter, LangChain**, or any other framework, your agent can seamlessly utilize these skills with zero friction.

### Why it's Frictionless:
- **CLI-First Architecture**: Every skill exposes a standard Python CLI interface (e.g., `scripts/cli.py`).
- **Structured Output**: The CLI returns deterministic JSON responses (`{"media_id": 123}`, `{"error": "..."}`), allowing your agent to safely parse state without hallucinating over raw text logs.
- **Native Execution**: Agents can completely bypass complex web UI scrapers or Gradio endpoints by executing the python CLI directly in their terminal environment.

**Example Invocation for any Agent:**
```bash
# Agent executes search
result=$(python3 ~/.gemini/skills/jit-media-gateway/scripts/cli.py search movie "Inception")

# Agent parses JSON and natively triggers playback
python3 ~/.gemini/skills/jit-media-gateway/scripts/cli.py embed movie 27205
```
