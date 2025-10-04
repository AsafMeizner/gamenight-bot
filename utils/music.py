# utils/music.py
import random
from typing import Dict, List, Optional, Tuple
import aiohttp

ITUNES_URL = "https://itunes.apple.com/search"

# random lightweight search seeds to get varied tracks
SEARCH_SEEDS = [
    "love", "night", "day", "dance", "heart", "blue", "red", "time", "dream",
    "fire", "light", "moon", "star", "gold", "rain", "wind", "river", "city",
    "summer", "winter", "happy", "sad", "rock", "pop", "rap", "classic", "piano"
]

async def fetch_itunes_tracks(session: aiohttp.ClientSession, term: str, limit: int = 25, country: str = "US") -> List[Dict]:
    params = {
        "term": term,
        "media": "music",
        "entity": "song",
        "limit": max(1, min(50, limit)),
        "country": country
    }
    try:
        async with session.get(ITUNES_URL, params=params) as r:
            data = await r.json()
            results = data.get("results", [])
            # Keep those with previewUrl present
            return [t for t in results if t.get("previewUrl")]
    except Exception:
        return []

async def get_guess_song_pack(count: int = 10) -> List[Dict]:
    """
    Returns a list of tracks with fields:
    previewUrl, trackName, artistName, collectionName, artworkUrl100
    """
    out: List[Dict] = []
    seen_urls = set()
    async with aiohttp.ClientSession() as session:
        tries = 0
        while len(out) < count and tries < count * 5:
            term = random.choice(SEARCH_SEEDS)
            tracks = await fetch_itunes_tracks(session, term, limit=25)
            random.shuffle(tracks)
            for t in tracks:
                url = t.get("previewUrl")
                if not url or url in seen_urls:
                    continue
                out.append({
                    "preview": url,
                    "track": t.get("trackName", "Unknown"),
                    "artist": t.get("artistName", "Unknown"),
                    "album": t.get("collectionName", "Unknown"),
                    "art": t.get("artworkUrl100")
                })
                seen_urls.add(url)
                if len(out) >= count:
                    break
            tries += 1
    return out
