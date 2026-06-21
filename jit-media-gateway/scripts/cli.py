import sys
import json
import argparse
import os
from dotenv import load_dotenv

# Load .env from the skill's own directory (independent of octemp)
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path)

from tools import search_anilist_anime, search_tmdb, search_radio, search_podcast, search_soundcloud, search_manga, search_meal, embed_media, embed_meal_ui

def main():
    parser = argparse.ArgumentParser(description="JIT Media Gateway CLI for AI Agents")
    subparsers = parser.add_subparsers(dest="action")
    
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("media_type", choices=["anime", "movie", "tv", "radio", "podcast", "soundcloud", "manga", "meal"])
    search_parser.add_argument("query")
    search_parser.add_argument("--type", type=str, default="tracks", help="Semantic type (e.g., tracks, albums, playlists) for supported media like soundcloud")
    
    embed_parser = subparsers.add_parser("embed")
    embed_parser.add_argument("media_type")
    embed_parser.add_argument("media_id")
    embed_parser.add_argument("--episode", type=int, default=1)
    embed_parser.add_argument("--season", type=int, default=1)
    embed_parser.add_argument("--sub_or_dub", type=str, default="sub")
    
    args = parser.parse_args()
    
    if args.action == "search":
        if args.media_type == "anime":
            print(search_anilist_anime(args.query))
        elif args.media_type in ["movie", "tv"]:
            print(search_tmdb(args.query, args.media_type))
        elif args.media_type == "radio":
            print(search_radio(args.query))
        elif args.media_type == "podcast":
            print(search_podcast(args.query))
        elif args.media_type == "soundcloud":
            print(search_soundcloud(args.query, search_type=args.type))
        elif args.media_type == "manga":
            print(search_manga(args.query))
        elif args.media_type == "meal":
            print(search_meal(args.query))
            
    elif args.action == "embed":
        import subprocess
        import webbrowser
        
        # We need to bypass the XSS wrappers in models.py and get the raw URL
        if args.media_type == "radio":
            url = args.media_id
            print(f"🔊 Playing Audio Stream in background via mpv...")
            subprocess.Popen(["mpv", "--no-terminal", "--ao=pulse", "--no-video", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif args.media_type == "podcast":
            url = f"https://embed.podcasts.apple.com/us/podcast/id{args.media_id}"
            print(f"🌐 Opening Podcast in browser...")
            webbrowser.open(url)
        elif args.media_type == "soundcloud":
            url = f"https://w.soundcloud.com/player/?url={args.media_id}"
            print(f"🌐 Opening SoundCloud in browser...")
            webbrowser.open(url)
        elif args.media_type == "manga":
            print(f"📖 Manga found. (Browser UI not implemented, please read description)")
        elif args.media_type == "meal":
            print("🍔 Opening meal UI...")
            # Meal is complex base64 HTML, let's dump it to a temp file and open it
            res = embed_media(args.media_type, args.media_id, episode=args.episode, season=args.season, sub_or_dub=args.sub_or_dub)
            # The result is <div...><img onerror="..."></div> containing data:text/html;base64...
            # We can extract the base64 or just let the browser handle it
        else:
            # Anime, Movie, TV
            from models import MediaRegistry
            cls = MediaRegistry.get_media_class(args.media_type)
            if cls:
                media = cls(media_id=args.media_id, title="")
                url = media.get_embed_url(episode=args.episode, season=args.season, sub_or_dub=args.sub_or_dub)
                print(f"🍿 Opening Video Player in browser...")
                webbrowser.open(url)
            else:
                print("Unknown media type")

if __name__ == "__main__":
    main()
