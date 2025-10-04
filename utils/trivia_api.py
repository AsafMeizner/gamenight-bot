# utils/trivia_api.py
import base64
import random
from typing import Dict, List, Optional, Tuple

import aiohttp

OTDB_BASE = "https://opentdb.com"
OTDB_AMOUNT_MAX = 50

OTDB_CATEGORIES: List[Dict] = []       # [{'id': 9, 'name': 'General Knowledge'}, ...]
OTDB_CAT_BY_NAME: Dict[str, int] = {}  # lower-name -> id
OTDB_CAT_BY_ID: Dict[int, str] = {}    # id -> name

def _b64decode(s: str) -> str:
    try:
        return base64.b64decode(s).decode("utf-8")
    except Exception:
        return s

async def load_categories():
    global OTDB_CATEGORIES, OTDB_CAT_BY_NAME, OTDB_CAT_BY_ID
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OTDB_BASE}/api_category.php") as r:
                data = await r.json()
        cats = data.get("trivia_categories", [])
        if isinstance(cats, list) and cats:
            OTDB_CATEGORIES = cats
            OTDB_CAT_BY_NAME = {c["name"].lower(): int(c["id"]) for c in cats}
            OTDB_CAT_BY_ID = {int(c["id"]): c["name"] for c in cats}
    except Exception:
        OTDB_CATEGORIES = []
        OTDB_CAT_BY_NAME = {}
        OTDB_CAT_BY_ID = {}

async def get_token(session: aiohttp.ClientSession) -> Optional[str]:
    try:
        async with session.get(f"{OTDB_BASE}/api_token.php?command=request") as r:
            data = await r.json()
            if data.get("response_code") == 0:
                return data.get("token")
    except Exception:
        return None
    return None

async def reset_token(session: aiohttp.ClientSession, token: str) -> bool:
    try:
        async with session.get(f"{OTDB_BASE}/api_token.php?command=reset&token={token}") as r:
            data = await r.json()
            return data.get("response_code") == 0
    except Exception:
        return False

async def fetch_questions(session: aiohttp.ClientSession, amount: int, token: Optional[str], category_id: Optional[int]) -> Tuple[List[Dict], Optional[int]]:
    amount = max(1, min(OTDB_AMOUNT_MAX, int(amount)))
    url = f"{OTDB_BASE}/api.php?amount={amount}&type=multiple&encode=base64"
    if token:
        url += f"&token={token}"
    if category_id:
        url += f"&category={int(category_id)}"
    try:
        async with session.get(url) as r:
            data = await r.json()
    except Exception:
        return [], 2
    rc = data.get("response_code", 2)
    if rc != 0:
        return [], rc
    out = []
    for item in data.get("results", []):
        q = _b64decode(item.get("question", ""))
        correct = _b64decode(item.get("correct_answer", ""))
        incorrect = [_b64decode(s) for s in item.get("incorrect_answers", [])]
        if len(incorrect) != 3:
            continue
        choices = incorrect + [correct]
        random.shuffle(choices)
        ans_idx = choices.index(correct)
        out.append({"question": q, "choices": choices, "answer": ans_idx})
    return out, 0

def resolve_category_id(name_or_id: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
    if not name_or_id:
        return None, None
    s = name_or_id.strip()
    if not s or s.lower() in ("any", "any category", "all", "random"):
        return None, None
    cid = OTDB_CAT_BY_NAME.get(s.lower())
    if cid:
        return cid, OTDB_CAT_BY_ID.get(cid, s)
    try:
        num = int(s)
        if num in OTDB_CAT_BY_ID:
            return num, OTDB_CAT_BY_ID[num]
        else:
            return num, f"Category {num}"
    except ValueError:
        return None, None
