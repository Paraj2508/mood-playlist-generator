import logging
import os
import random
import re

import spotipy
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from spotipy.oauth2 import SpotifyClientCredentials
from textblob import TextBlob

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("mood-playlist")

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
MAX_INPUT_CHARS = 500
SEARCH_LIMIT = 10
SPOTIFY_MARKET = os.getenv("SPOTIFY_MARKET", "IN")  # ISO country code
PLAYLIST_ID_RE = re.compile(r"^[A-Za-z0-9]{10,30}$")

client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
if not client_id or not client_secret:
    raise RuntimeError(
        "Missing Spotify credentials. Set SPOTIPY_CLIENT_ID and "
        "SPOTIPY_CLIENT_SECRET in your .env file."
    )

app = Flask(__name__)
# Set SECRET_KEY in .env so sessions survive restarts.
app.secret_key = os.getenv("SECRET_KEY") or os.urandom(24)

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=client_id, client_secret=client_secret
    ),
    requests_timeout=10,
    retries=2,
)

# --------------------------------------------------------------------------
# Mood model
# --------------------------------------------------------------------------
MOODS = {
    "happy": {
        "label": "Happy and energetic",
        "queries": ["happy upbeat feel good", "good vibes pop hits", "dance party energy"],
    },
    "chill": {
        "label": "Chill and relaxed",
        "queries": ["chill lofi beats", "relaxing acoustic evening", "mellow indie chill"],
    },
    "sad": {
        "label": "Sad and reflective",
        "queries": ["sad acoustic songs", "melancholy piano", "heartbreak ballads"],
    },
    "angry": {
        "label": "Angry and fired up",
        "queries": ["angry rock workout", "rage metal", "aggressive hip hop"],
    },
    "anxious": {
        "label": "Anxious and overwhelmed",
        "queries": ["calming ambient", "anxiety relief music", "peaceful piano calm"],
    },
    "romantic": {
        "label": "Romantic",
        "queries": ["romantic love songs", "love songs bollywood", "date night r&b"],
    },
    "focused": {
        "label": "Focused",
        "queries": ["deep focus study", "instrumental concentration", "coding music"],
    },
    "tired": {
        "label": "Tired and winding down",
        "queries": ["sleepy slow songs", "late night wind down", "soft lullaby instrumental"],
    },
}

# Strong keywords win over raw polarity, since polarity alone cannot tell
# "angry" from "sad" or "anxious" from "tired".
KEYWORDS = {
    "angry": ["angry", "furious", "rage", "mad", "annoyed", "frustrated", "irritated", "pissed off"],
    "anxious": ["anxious", "anxiety", "stressed", "overwhelmed", "nervous", "worried", "panic", "on edge"],
    "romantic": ["crush", "romantic", "in love", "date night", "miss you", "missing you"],
    "focused": ["focus", "study", "studying", "coding", "concentrate", "concentrating", "homework"],
    "tired": ["tired", "exhausted", "sleepy", "drained", "insomnia", "burned out", "burnt out"],
}


def detect_mood(text):
    """Return (mood_key, reason) for the given text."""
    lowered = text.lower()

    best_key, best_hits = None, []
    for key, words in KEYWORDS.items():
        hits = [w for w in words if re.search(rf"\b{re.escape(w)}\b", lowered)]
        if len(hits) > len(best_hits):
            best_key, best_hits = key, hits

    if best_key:
        return best_key, f"You mentioned “{best_hits[0]}”."

    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0.3:
        return "happy", "Your message reads as positive."
    if polarity < -0.1:
        return "sad", "Your message reads as low."
    return "chill", "Your message reads as calm or neutral."


# --------------------------------------------------------------------------
# Spotify
# --------------------------------------------------------------------------
def find_playlist(queries, exclude_id=None):
    """Search Spotify and return a random playlist id, avoiding exclude_id."""
    query = random.choice(queries)
    try:
        results = sp.search(
            q=query, type="playlist", limit=SEARCH_LIMIT, market=SPOTIFY_MARKET
        )
    except Exception:
        log.exception("Spotify search failed for query %r", query)
        return None

    items = ((results or {}).get("playlists") or {}).get("items") or []
    ids = [
        item["id"]
        for item in items
        if item and item.get("id") and PLAYLIST_ID_RE.match(item["id"])
    ]
    candidates = [pid for pid in ids if pid != exclude_id] or ids
    return random.choice(candidates) if candidates else None


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.get("/")
def index():
    return render_template(
        "index.html",
        result=session.get("result"),
        error=session.pop("error", None),
        user_input=session.get("user_input", ""),
        max_chars=MAX_INPUT_CHARS,
    )


@app.post("/")
def generate():
    text = request.form.get("mood_text", "").strip()
    session["user_input"] = text[:MAX_INPUT_CHARS]

    if not text:
        session["error"] = "Write a sentence or two about how you feel first."
        session.pop("result", None)
        return redirect(url_for("index"))

    if len(text) > MAX_INPUT_CHARS:
        session["error"] = f"Keep it under {MAX_INPUT_CHARS} characters."
        session.pop("result", None)
        return redirect(url_for("index"))

    mood_key, reason = detect_mood(text)
    mood = MOODS[mood_key]

    previous = session.get("result") or {}
    playlist_id = find_playlist(mood["queries"], exclude_id=previous.get("playlist_id"))

    if playlist_id is None:
        session["error"] = (
            "Spotify didn’t return a playlist. Try again in a moment."
        )
        session.pop("result", None)
    else:
        session["result"] = {
            "mood_key": mood_key,
            "mood_label": mood["label"],
            "reason": reason,
            "playlist_id": playlist_id,
        }

    # Post/Redirect/Get: refreshing the page won't resubmit the form.
    return redirect(url_for("index"))


@app.post("/reset")
def reset():
    session.pop("result", None)
    session.pop("user_input", None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
