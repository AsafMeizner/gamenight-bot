# utils/common.py
from pathlib import Path
import json
from typing import List, Dict
import discord

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

def load_lines(path: Path) -> List[str]:
    try:
        return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except FileNotFoundError:
        return []

def load_trivia_local(path: Path) -> List[Dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        good = []
        for item in data:
            if (
                isinstance(item, dict)
                and isinstance(item.get("question"), str)
                and isinstance(item.get("choices"), list)
                and len(item["choices"]) == 4
                and all(isinstance(c, str) for c in item["choices"])
                and isinstance(item.get("answer"), int)
                and 0 <= item["answer"] < 4
            ):
                good.append(item)
        return good
    except FileNotFoundError:
        return []
    except Exception:
        return []

def make_embed(title: str, desc: str = "", color: discord.Color = discord.Color.blurple()):
    return discord.Embed(title=title, description=desc, color=color)
