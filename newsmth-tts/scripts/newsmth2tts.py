#!/usr/bin/env python3
"""
newsmth2tts.py — Fetch a newsmth.net thread or RSS top-ten feed, clean
it, summarise it, generate Mandarin TTS audio, and play it via mpv.

Usage:
    # Full thread read
    python3 newsmth2tts.py --url "https://www.newsmth.net/nForum/article/<board>/<id>"

    # Top-10 hot threads summary
    python3 newsmth2tts.py --rss
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

RSS_URL = 'https://www.newsmth.net/nForum/rss/topten'

TMP_DIR = '/tmp/gemini_newsmth'
os.makedirs(TMP_DIR, exist_ok=True)

SCRIPT_PATH = os.path.join(TMP_DIR, 'voice_script.txt')
AUDIO_PATH  = os.path.join(TMP_DIR, 'voice_final.mp3')
HISTORY_PATH = os.path.join(TMP_DIR, 'newsmth_history.json')

AD_KEYWORDS = [
    '广告', '团购', '拼单', '拼团', '代购', '转让', '出售',
    '促销', '优惠', '折扣', '甩卖', '清仓', '闲置', '二手',
]


# ─────────────────────────────────────────────
#  HTML-thread helpers
# ─────────────────────────────────────────────

def fetch_page(url: str) -> str:
    """Fetch a URL and return the HTML decoded as GB18030."""
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.encoding = 'GB18030'
    return r.text


def get_page_count(html: str) -> int:
    """Extract the number of pages from the pagination bar."""
    soup = BeautifulSoup(html, 'lxml')
    page_div = soup.find('div', class_='page')
    if page_div:
        links = page_div.find_all('a')
        max_page = 1
        for a in links:
            href = a.get('href', '')
            m = re.search(r'\?p=(\d+)', href)
            if m:
                p = int(m.group(1))
                if p > max_page:
                    max_page = p
        return max_page
    m = re.search(r'贴数:\s*(\d+)', soup.get_text())
    post_count = int(m.group(1)) if m else 0
    return max(1, (post_count + 9) // 10)


def extract_post_text(td_content):
    """Extract clean post content from a td.a-content element."""
    html = str(td_content).replace('<br/>', '\n').replace('<br>', '\n')
    soup = BeautifulSoup(html, 'lxml')
    raw = soup.get_text('\n')

    title = ''
    m = re.search(r'标\s*题:\s*(.+)', raw)
    if m:
        title = m.group(1).strip()

    m = re.search(r'站内\s*\n+(.*)', raw, re.DOTALL)
    inner = m.group(1) if m else raw
    return title, _clean_content(inner)


def _clean_content(text: str) -> str:
    """Strip quotes, signatures, URLs and other noise from a post body."""
    lines = text.split('\n')
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith(':'):
            continue
        if '【 在 ' in line and '的大作中提到:' in line:
            continue
        if 'http://' in line or 'https://' in line:
            continue
        if line.startswith('·[FROM:') or line.startswith('FROM '):
            continue
        if line.startswith('※ 来源') or line.startswith('※ 修改:'):
            continue
        if line == '--' or line.startswith('--发自') or line.startswith('发自'):
            continue
        if line.startswith('论坛助手') or line.startswith('发自「'):
            continue
        if re.match(r'^[─=]{10,}', line):
            continue
        if 'static.mysmth.net' in line or 'nForum/att/' in line:
            continue
        if re.match(r'^\[\+?\d+\]$', line):
            continue
        if re.match(r'^\s*\(\d{4}-\d{2}-\d{2}', line):
            continue
        if re.match(r'^[a-zA-Z0-9_]+\s*:\s*$', line):
            continue
        if re.match(r'^[A-Z][a-z]+ [A-Z]\d+.*', line) and any(
            m in line for m in ['ThinkPad', 'Yoga', 'X1', 'Latitude', 'MacBook']
        ):
            continue
        out.append(line)
    return '\n'.join(out)


def extract_posts(html: str):
    """Parse a page HTML and return a list of post dicts."""
    soup = BeautifulSoup(html, 'lxml')
    tables = soup.find_all('table', class_='article')
    posts = []

    for table in tables:
        post = {
            'author': '',
            'nickname': '',
            'position': '',
            'title': '',
            'content': '',
        }

        head = table.find('tr', class_='a-head')
        if head:
            span = head.find('span', class_='a-u-name')
            if span and span.find('a'):
                post['author'] = span.find('a').get_text(strip=True)
            span = head.find('span', class_='a-pos')
            if span:
                post['position'] = span.get_text(strip=True)

        body = table.find('tr', class_='a-body')
        if body:
            td = body.find('td', class_='a-content')
            if td:
                post['title'], post['content'] = extract_post_text(td)
            div = body.find('div', class_='a-u-uid')
            if div:
                post['nickname'] = div.get_text(strip=True)

        posts.append(post)

    return posts


def build_script(posts):
    """Build the full text script (summary + posts + summary)."""
    lines = []
    title = posts[0]['title'] if posts else '未知话题'

    # ── Discussion summary ──
    all_text = '\n'.join(
        p.get('content', '') for p in posts if p.get('content')
    )
    opinion_signals = ['应该', '不该', '太', '很', '真', '其实', '关键', '问题',
                       '支持', '反对', '同意', '不能', '可以', '建议', '觉得',
                       '肯定', '肯定不', '必然', '必须', '不用', '没必要',
                       '说到底', '无非', '反正', '就是', '不是', '但', '不过']
    sentences = re.split(r'[。！？\n]', all_text)
    key_sentences = []
    for s in sentences:
        s = s.strip()
        if len(s) < 15 or len(s) > 120:
            continue
        if s in ['re', '是的', '对', '没错', '同意', '顶', '']:
            continue
        if any(sig in s for sig in opinion_signals):
            key_sentences.append(s)

    seen = set()
    unique = []
    for s in key_sentences:
        norm = s[:40]
        if norm not in seen:
            seen.add(norm)
            unique.append(s)
    selected = unique[:4]

    summary_parts = [f'本帖讨论的是「{title}」']
    if selected:
        summary_parts.append('多位网友发表了观点')
        summary_parts.extend(f'有网友提到：{s}' for s in selected)
    else:
        snippets = []
        for p in posts:
            c = (p.get('content') or '').strip()
            if len(c) > 15 and c not in ['re', '是的', '对', '没错', '同意', '顶']:
                if len(c) > 60:
                    c = c[:57] + '...'
                snippets.append(c)
            if len(snippets) >= 3:
                break
        if snippets:
            summary_parts.append('网友的主要观点包括：')
            summary_parts.extend(f'「{s}」' for s in snippets)
        else:
            summary_parts.append('网友们就这一话题展开了讨论')
    discussion_summary = '；'.join(summary_parts)

    # ── Build script ──
    lines.append('水木社区热帖全文朗读')
    lines.append('')
    lines.append(f'帖子主题：{title}')
    lines.append(f'共收录 {len(posts)} 条帖子，包括楼主的原帖和全部跟帖回复')
    lines.append('')
    lines.append('以下是核心讨论内容摘要：')
    lines.append(discussion_summary)
    lines.append('')
    lines.append('— — — 详细内容开始 — — —')
    lines.append('')

    for i, p in enumerate(posts):
        pos = p['position'] or ('楼主' if i == 0 else f'第{i}楼')
        author = p['author'] or '未知'
        nick = p['nickname'] or ''
        display = f'{author}（{nick}）' if nick else author
        lines.append(f'【{pos}】{display}说：')
        if p['content']:
            lines.append(p['content'])
        lines.append('')

    lines.append('— — — 全文朗读完毕 — — —')
    lines.append('')
    lines.append('再来回顾一下核心讨论内容：')
    lines.append(discussion_summary)
    lines.append('')
    lines.append('感谢收听水木社区的热帖朗读。')

    return '\n'.join(lines)


# ─────────────────────────────────────────────
#  History & filtering helpers
# ─────────────────────────────────────────────

def load_history() -> dict:
    """Load previous days' top-10 history from disk."""
    try:
        with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_history(history: dict):
    """Save history to disk, keeping only latest 7 days."""
    with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_date_str(days_ago: int = 0) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')


def is_ad_title(title: str) -> bool:
    """Check if a thread title matches ad/group-buying patterns."""
    return any(kw in title for kw in AD_KEYWORDS)


def detect_overlaps(items: list[dict], history: dict) -> set:
    """Return 0-based indices of items that appeared in yesterday's top-10."""
    yesterday_str = get_date_str(1)
    yesterday_items = history.get(yesterday_str, [])
    if not yesterday_items:
        return set()
    yesterday_titles = {it['title'].strip() for it in yesterday_items if it.get('title')}
    return {i for i, it in enumerate(items) if it['title'].strip() in yesterday_titles}


def filter_rss_items(items: list[dict], history: dict,
                     skip_indices: set = None,
                     no_filter: bool = False) -> tuple:
    """
    Filter RSS items using default rules:
      1. Skip ad/group-buying threads
      2. Skip threads overlapping with yesterday's top-10

    Default rules only auto-trigger when yesterday's history data exists.
    Returns (filtered_items, filter_messages).
    """
    filter_msgs = []
    remove_set = set()

    # 1. Manual skip (--skip)
    if skip_indices:
        remove_set.update(skip_indices)
        for i in sorted(skip_indices):
            if i < len(items):
                filter_msgs.append(f'手动跳过第{i+1}条「{items[i]["title"]}」')

    # 2. Auto-filter (default rules): only activate with enough history
    if not no_filter:
        yesterday_str = get_date_str(1)
        has_history = yesterday_str in history and len(history.get(yesterday_str, [])) > 0

        if has_history:
            # 2a. Skip ads / group-buying
            for i, item in enumerate(items):
                if i in remove_set:
                    continue
                if is_ad_title(item['title']):
                    remove_set.add(i)
                    filter_msgs.append(f'自动过滤第{i+1}条广告/团购贴「{item["title"]}」')

            # 2b. Skip yesterday overlaps
            overlaps = detect_overlaps(items, history)
            for i in overlaps:
                if i not in remove_set:
                    remove_set.add(i)
                    filter_msgs.append(f'自动过滤第{i+1}条（与昨日十大重叠）「{items[i]["title"]}」')

    filtered = [item for i, item in enumerate(items) if i not in remove_set]
    return filtered, filter_msgs


# ─────────────────────────────────────────────
#  RSS helpers
# ─────────────────────────────────────────────

def fetch_rss() -> list[dict]:
    """Fetch the newsmth top-10 RSS feed and return parsed items."""
    r = requests.get(RSS_URL, headers=HEADERS, timeout=30)
    # Parse raw bytes with BeautifulSoup + lxml-xml for encoding-safe XML handling
    soup = BeautifulSoup(r.content, 'lxml-xml')
    items = []
    for item_elem in soup.find_all('item'):
        title_el = item_elem.find('title')
        link_el = item_elem.find('link')
        author_el = item_elem.find('author')
        desc_el = item_elem.find('description')

        title = title_el.get_text(strip=True) if title_el else ''
        link = link_el.get_text(strip=True) if link_el else ''
        author = author_el.get_text(strip=True) if author_el else ''
        desc = desc_el.get_text(strip=True) if desc_el else ''

        # Clean the description (strip HTML tags)
        desc_clean = re.sub(r'<[^>]+>', '', desc)
        desc_clean = desc_clean.replace('&nbsp;', ' ').strip()
        desc_excerpt = desc_clean[:200].strip()

        items.append({
            'title': title,
            'url': link,
            'author': author,
            'excerpt': desc_excerpt,
        })
    return items


def build_rss_script(items: list[dict]) -> str:
    """Build a script summarising the top-N RSS items."""
    lines = []
    lines.append('水木社区十大热门话题速览')
    lines.append('')
    lines.append(f'共 {len(items)} 条热门帖子，以下为快速浏览：')
    lines.append('')

    for i, item in enumerate(items, 1):
        lines.append(f'【第{i}条】{item["title"]}')
        if item['excerpt']:
            lines.append(f'    内容概要：{item["excerpt"]}')
        lines.append('')

    lines.append('— — — 十大热门话题播报完毕 — — —')
    lines.append('')
    lines.append('如需详细收听某一条帖子，请告诉我序号，例如"听第3条"。')

    return '\n'.join(lines)


# ─────────────────────────────────────────────
#  TTS and playback
# ─────────────────────────────────────────────

async def generate_tts(text: str, output_path: str):
    """Generate TTS audio from text using edge-tts."""
    import edge_tts
    tts = edge_tts.Communicate(text, voice='zh-CN-XiaoxiaoNeural')
    await tts.save(output_path)


def play_audio(path: str):
    """Play the audio file via mpv in the background."""
    import os
    env = os.environ.copy()
    devnull = subprocess.DEVNULL
    proc = subprocess.Popen(
        ['mpv', '--no-terminal', '--volume=100', '--ao=pulse', '--no-video', path],
        stdout=devnull, stderr=devnull,
        env=env,
        start_new_session=True
    )
    return proc


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Newsmth thread → TTS audio via mpv',
    )
    parser.add_argument(
        '--url', '-u',
        help='Newsmth article URL, e.g. '
             'https://www.newsmth.net/nForum/article/AutoWorld/1945276079',
    )
    parser.add_argument(
        '--rss', action='store_true',
        help='Fetch and read the top-10 hot threads from the RSS feed',
    )
    parser.add_argument(
        '--skip', type=int, nargs='*',
        help='Manually skip specific thread indices (1-based), e.g. --skip 1 2 5',
    )
    parser.add_argument(
        '--no-filter', action='store_true',
        help='Disable automatic filtering of ads and yesterday-overlapping threads',
    )
    args = parser.parse_args()

    if not args.url and not args.rss:
        parser.error('Provide either --url or --rss')

    if args.rss:
        # ── RSS mode ──
        print('🌐 Fetching RSS top-10 feed...', file=sys.stderr)
        items = fetch_rss()
        print(f'✅ Got {len(items)} hot threads', file=sys.stderr)

        # Load history & save today's original items for future overlap detection
        history = load_history()
        today_str = get_date_str()
        history[today_str] = [
            {'title': it['title'], 'url': it['url']} for it in items
        ]
        save_history(history)

        # Apply filtering
        skip_set = set()
        if args.skip:
            skip_set.update(i - 1 for i in args.skip if 1 <= i <= len(items))

        items, filter_msgs = filter_rss_items(items, history, skip_set, args.no_filter)

        for msg in filter_msgs:
            print(f'   ⚠ {msg}', file=sys.stderr)

        script = build_rss_script(items)
        title = '水木社区十大热门话题速览'

    else:
        # ── URL mode (existing logic) ──
        base_url = args.url.rstrip('/')
        fragment_match = re.search(r'#!article(/.*)', base_url)
        if fragment_match:
            base_url = re.sub(r'#!article.*', '', base_url).rstrip('/') + '/article' + fragment_match.group(1)
        else:
            base_url = re.sub(r'#!.*', '', base_url)
        base_url = base_url.rstrip('?')

        print(f'🌐 Fetching: {base_url}', file=sys.stderr)
        html = fetch_page(base_url)
        total_pages = get_page_count(html)
        print(f'📄 Total pages: {total_pages}', file=sys.stderr)

        all_posts = extract_posts(html)
        for page in range(2, total_pages + 1):
            url = f'{base_url}?p={page}'
            print(f'   Fetching page {page}/{total_pages}...', file=sys.stderr)
            try:
                page_html = fetch_page(url)
                all_posts.extend(extract_posts(page_html))
            except Exception as e:
                print(f'   ⚠ Failed page {page}: {e}', file=sys.stderr)

        print(f'✅ Extracted {len(all_posts)} posts total', file=sys.stderr)
        script = build_script(all_posts)
        title = all_posts[0]['title'] if all_posts else '未知话题'

    # ── Save script ──
    with open(SCRIPT_PATH, 'w', encoding='utf-8') as f:
        f.write(script)
    print(f'📝 Script saved ({len(script)} chars)', file=sys.stderr)

    # ── Generate ──
    print('🔊 Generating TTS audio...', file=sys.stderr)
    start = time.time()
    asyncio.run(generate_tts(script, AUDIO_PATH))
    elapsed = time.time() - start
    size_kb = os.path.getsize(AUDIO_PATH) / 1024

    duration = 0
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json',
             '-show_format', AUDIO_PATH],
            capture_output=True, text=True, timeout=10,
        )
        info = json.loads(result.stdout)
        duration = float(info.get('format', {}).get('duration', 0))
    except Exception:
        pass

    dur_str = f'{duration / 60:.1f} min' if duration else f'~{len(script)//3//60} min'
    print(f'✅ Audio generated ({elapsed:.1f}s, {size_kb:.0f} KB, {dur_str})',
          file=sys.stderr)

    # Kill any previous mpv instance to prevent overlapping audio
    try:
        subprocess.run(['pkill', 'mpv'], capture_output=True, timeout=5)
    except Exception:
        pass

    proc = play_audio(AUDIO_PATH)
    print(f'▶️ Playing via mpv (PID {proc.pid})', file=sys.stderr)

    summary = {
        'title': title,
        'script_chars': len(script),
        'audio_file': AUDIO_PATH,
        'audio_duration_sec': duration,
        'audio_duration_str': dur_str,
        'mpv_pid': proc.pid,
    }
    print(f'\n🎯 SUMMARY: {json.dumps(summary, ensure_ascii=False)}',
          file=sys.stderr)


if __name__ == '__main__':
    main()
