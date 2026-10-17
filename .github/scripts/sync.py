"""Copy the already public board snapshot; runtime has no dependency on origin."""
import concurrent.futures
import json
import re
import urllib.request
from pathlib import Path

ORIGIN = "https://verstak.46.17.96.29.sslip.io/"
ROOT = Path(__file__).resolve().parents[2]

def download(path, limit):
    with urllib.request.urlopen(ORIGIN + path, timeout=20) as response:
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("Public file too large")
    return payload

try:
    board = json.loads(download("board.json", 2_000_000))
    assert isinstance(board["videos"], list) and 0 < len(board["videos"]) <= 120
    def thumbnail(row):
        video_id = row.get("id", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError("Invalid video identifier")
        path = "thumbs/" + video_id + ".jpg"
        if row.get("thumbnail") != path:
            row["thumbnail"] = None
            return
        target = ROOT / path
        try:
            if not target.exists():
                image = download(path, 1_500_000)
                if not image.startswith(b"\xff\xd8"):
                    raise ValueError("Not a JPEG")
                target.write_bytes(image)
        except Exception:
            if not target.exists():
                row["thumbnail"] = None
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(thumbnail, board["videos"]))
    board["coverage"]["self_hosted_previews"] = sum(bool(r.get("thumbnail")) for r in board["videos"])
    temporary = ROOT / "board.json.tmp"
    temporary.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(ROOT / "board.json")
    print("Public snapshot refreshed:", len(board["videos"]), "videos at", board["fetched_at"])
except Exception as error:
    print("Origin unavailable; keeping bundled public snapshot:", type(error).__name__)
