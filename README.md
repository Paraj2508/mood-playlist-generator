# Mood Playlist Generator

Describe how you feel in a sentence or two, and get a Spotify playlist that matches your mood.

**Live demo:** https://YOUR-APP-NAME.onrender.com
*(Hosted on a free plan, so the first load after a quiet period can take about a minute.)*

## How it works

1. You type a short message about your mood.
2. The app looks for strong mood keywords (for example "exhausted" or "stressed"), then falls back to TextBlob sentiment polarity.
3. The mood maps to search terms, and the Spotify Web API (via Spotipy) finds a matching public playlist.
4. The playlist shows up in an embedded Spotify player. The page's accent color changes with the detected mood.

Supported moods: happy, chill, sad, angry, anxious, romantic, focused, tired.

## Tech stack

- **Backend:** Python, Flask, Spotipy, TextBlob, python-dotenv
- **Frontend:** HTML, CSS (mood-driven theme with CSS variables), Jinja2
- **Hosting:** Render (gunicorn)

## Run it locally

```bash
git clone https://github.com/YOUR_USERNAME/mood-playlist-generator.git
cd mood-playlist-generator
python -m venv venv
venv\Scripts\activate        # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project folder:

```
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SECRET_KEY=any-long-random-string
SPOTIFY_MARKET=IN
```

Get your Spotify credentials by creating an app at https://developer.spotify.com/dashboard.

Then run:

```bash
python app.py
```

and open http://127.0.0.1:5000.

## Project structure

```
mood_playlist_generator/
├── app.py
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    └── style.css
```

## Ideas for next steps

- Swap TextBlob for VADER and add negation handling
- Mood history and saved playlists
- "Log in with Spotify" to save playlists to the user's account
- Track-level view instead of a full-playlist embed
