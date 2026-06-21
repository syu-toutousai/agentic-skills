---
name: newsmth-tts
description: >-
  Use ONLY when the user provides a newsmth.net (水木社区) forum thread URL
  and wants it read aloud as speech, OR when the user asks about "水木十大",
  "水木热门", "水木top10", "水木清华热帖" or similar phrases about the
  latest hot threads. Fetches the full thread (all pages), cleans
  quoted/redundant text, generates a spoken summary with TTS (edge-tts), and
  plays the audio via mpv. Input: a newsmth article URL or "十大" intent.
  Output: MP3 audio played through the system speaker.
---

# Skill: newsmth-tts — Newsmth Thread → TTS Audio

Turns a 水木社区 forum thread into a spoken audio broadcast. The skill fetches
every page of the thread, strips out redundant quoted replies and boilerplate,
generates a synopsis of the core discussion, synthesises natural Mandarin
speech with Microsoft Xiaoxiao (edge-tts), and plays the result through mpv.

## Requirements

- `python3` with packages: `requests`, `beautifulsoup4`, `lxml`, `edge-tts`
- `mpv` media player
- Internet access (for fetching pages and for edge-tts cloud API)

Install missing packages with:
```bash
pip3 install --break-system-packages requests beautifulsoup4 lxml edge-tts
```

## Companion script

This skill relies on the companion Python script located at:

```
`scripts/newsmth2tts.py` in this skill's directory
```

## Two modes of operation

### Mode 1: Read a single thread (`--url`)

| Parameter  | Required | Description |
|------------|----------|-------------|
| `--url`    | Yes      | Full newsmth article URL, e.g. `https://www.newsmth.net/nForum/article/AutoWorld/1945276079` |

Supports both `#!` fragment URLs and clean URLs:
- `https://www.newsmth.net/nForum/#!article/AutoWorld/1945276079`
- `https://www.newsmth.net/nForum/article/AutoWorld/1945276079`

### Mode 2: Top-10 hot threads overview (`--rss`)

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--rss`   | Yes      | Fetch the latest top-10 hot threads from the RSS feed and read summaries |

#### Smart filtering: skip ads & yesterday repeats

When `--rss` is used, the script can optionally filter out unwanted threads:

| Parameter | Description |
|-----------|-------------|
| `--skip <N> [<N> ...]` | Manually skip specific thread indices (1-based), e.g. `--skip 1 2 5` |
| `--no-filter` | Disable automatic filtering entirely |

**Default rules** (auto-triggered only when enough history data exists):

1. **Ads / group-buying** — threads whose titles contain keywords like 广告, 团购, 拼单, 代购, 转让, 出售, etc.
2. **Yesterday overlaps** — threads that appeared in the previous day's top-10, avoiding repeated content.

These rules activate automatically once at least one prior day's top-10 has been
recorded (i.e., the history file has yesterday's data). Until then, all 10
threads are included.

The AI assistant should inform the user whenever threads are filtered and why.

## Natural-language triggers

When the user says **any** of these (or similar), use the `--rss` mode:

- "水木十大热帖给我总结一下"
- "水木热门话题" / "水木十大"
- "水木清华有什么热门帖子"
- "水木top10" / "水木 hot topics"
- "看看水木今天的热帖"

When the user provides a **specific URL**, use the `--url` mode.

## Workflow

### Step 1 — Determine mode

- User gave a URL → `--url` mode
- User asked about 十大/热门/top10 → `--rss` mode

### Step 2 — Run the companion script

```bash
# URL mode:
python3 ~/.config/opencode/skills/newsmth-tts/newsmth2tts.py --url "<URL>"

# RSS mode (default — all 10 threads):
python3 ~/.config/opencode/skills/newsmth-tts/newsmth2tts.py --rss

# RSS mode with manual skip (e.g. skip threads 1, 2, 5):
python3 ~/.config/opencode/skills/newsmth-tts/newsmth2tts.py --rss --skip 1 2 5

# RSS mode without automatic filtering:
python3 ~/.config/opencode/skills/newsmth-tts/newsmth2tts.py --rss --no-filter
```

The script will:

1. **Fetch** the data (all pages of a thread, or the RSS feed).
2. **Extract** each post, stripping quoted text, forum signatures, URLs, and noise.
3. **Generate** a spoken summary of the core discussion points.
4. **Wrap** the summary around the full content (beginning + end).
5. **Synthesise** the full script into an MP3 via edge-tts (`zh-CN-XiaoxiaoNeural`).
6. **Play** the MP3 through mpv in the background.
7. **Print** a JSON summary (title, post count, audio duration, file path, PID).

### Step 3 — Report to the user

Tell the user:
- The mode used (URL or RSS)
- How many posts / threads were processed
- The audio duration
- That playback has started

In RSS mode, also mention that they can ask to hear any single thread in full
by saying e.g. "听第3条".

## Output files

| File | Description |
|------|-------------|
| `/tmp/opencode/voice_script.txt` | Clean text script used for TTS |
| `/tmp/opencode/voice_final.mp3` | Generated MP3 audio file |

## Constraints (MUST follow)

### Sequential playback — ONE audio at a time

Never start a new TTS playback while a previous one is still playing. This is
critical because multiple mpv instances will play simultaneously through the
same speaker, creating garbled overlapping audio.

**Rules:**

1. The companion script `newsmth2tts.py` now has a built-in `pkill mpv` guard
   that kills any previous mpv before starting a new play. This is the last
   line of defence.

2. **At the AI level** (more important): Before running a new `--url` or
   `--rss` invocation, first check if an mpv process is already running:
   ```bash
   pgrep -x mpv && echo "PLAYING" || echo "IDLE"
   ```
   If `PLAYING`, either:
   - **Wait** for it to finish (poll every 10 seconds), or
   - **Ask** the user if they want to interrupt the current playback.

3. Never invoke the script twice concurrently. Wait for one run to complete
   (including TTS generation + mpv start) before starting another.

4. When the user provides multiple URLs or requests in sequence, queue them
   and play one after the other — never in parallel.

## Design notes

- **Encoding**: newsmth uses GB18030/GBK for HTML and GB2312 for RSS. The
  script detects and decodes accordingly.
- **Redundancy removal**: Every reply quotes the parent post with `:`-prefixed
  lines and `【在 xxx 的大作中提到:】` blocks. The script strips all of these.
- **Summary**: A short synopsis of the discussion is prepended and appended
  to the audio so the listener gets the gist immediately and as a recap.
- **TTS voice**: `zh-CN-XiaoxiaoNeural` (Microsoft Xiaoxiao, female,
  Mandarin). Edge-tts is preferred over gTTS for higher naturalness and
  faster generation.
- **RSS**: The `--rss` flag reads the GB2312-encoded RSS XML, extracts titles,
  authors and descriptions, and builds a concise audio overview.
- **History tracking**: Each day's top-10 is saved to
  `/tmp/opencode/newsmth_history.json`. This enables overlap detection across
  consecutive days. Only the latest 7 days are retained.
- **`#!` URL support**: URLs with `#!article/Board/Id` fragments are
  automatically converted to clean `/article/Board/Id` paths.

## Examples

| User says | Action |
|-----------|--------|
| `https://www.newsmth.net/nForum/article/AutoWorld/1945276079 帮我读一下` | `--url "..."` |
| `水木十大热帖有哪些` | `--rss` |
| `今天水木清华有什么热门话题` | `--rss` |
| `除了广告和昨天重复的，听听其余的热帖` | `--rss` (auto-filter kicks in if history data exists) |
| `跳过第1、2、5条，讲别的` | `--rss --skip 1 2 5` |
| `不要自动过滤，全部播报` | `--rss --no-filter` |
| `听听第3条` | Extract URL RSS item #3 → `--url "..."` |
→ `--url "..."` |
