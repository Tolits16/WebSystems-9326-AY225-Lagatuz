"""
================================================================
 Ubisoft Gaming Industry Web Scraper
 Subject: Web Systems
 
 FOLDER STRUCTURE (already configured — no changes needed):
   midterms/ubisoft_scraper/
     python/  <- YOU ARE HERE (app.py)
     html/    <- index.html (dashboard)
     data/    <- games.json (saved after scraping)
     csv/     <- games.csv  (saved after scraping)

 HOW TO RUN:
   1. Open terminal in this folder (python/)
   2. pip install flask requests beautifulsoup4
   3. py app.py
   4. Open http://localhost:5050
================================================================
"""

import os
import json
import csv
import re
import time
import datetime

from flask import Flask, jsonify, send_file, render_template_string
import requests
from bs4 import BeautifulSoup

app      = Flask(__name__)

# -- Folder paths (already correct for the organized structure)
# BASE_DIR = .../midterms/ubisoft_scraper/python/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Goes one level up from python/ then into data/ and csv/
DATA_DIR = os.path.join(BASE_DIR, "..", "data")   # -> ubisoft_scraper/data/
CSV_DIR  = os.path.join(BASE_DIR, "..", "csv")    # -> ubisoft_scraper/csv/
HTML_DIR = os.path.join(BASE_DIR, "..", "html")   # -> ubisoft_scraper/html/

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CSV_DIR,  exist_ok=True)

# ================================================================
# SECTION 1 -- TARGET URLS
# Only URLs are listed here. NO game content is hardcoded.
# All data is fetched dynamically from Ubisoft's website.
# ================================================================
UBISOFT_GAMES = [
    {"slug": "assassins-creed-shadows",     "url": "https://www.ubisoft.com/en-us/game/assassins-creed/shadows"},
    {"slug": "assassins-creed-mirage",      "url": "https://www.ubisoft.com/en-us/game/assassins-creed/mirage"},
    {"slug": "far-cry-6",                   "url": "https://www.ubisoft.com/en-us/game/far-cry/far-cry-6"},
    {"slug": "rainbow-six-siege",           "url": "https://www.ubisoft.com/en-us/game/rainbow-six/siege"},
    {"slug": "watch-dogs-legion",           "url": "https://www.ubisoft.com/en-us/game/watch-dogs/legion"},
    {"slug": "the-division-2",              "url": "https://www.ubisoft.com/en-us/game/tom-clancys-the-division/the-division-2"},
    {"slug": "ghost-recon-breakpoint",      "url": "https://www.ubisoft.com/en-us/game/ghost-recon/breakpoint"},
    {"slug": "immortals-fenyx-rising",      "url": "https://www.ubisoft.com/en-us/game/immortals-fenyx-rising"},
    {"slug": "riders-republic",             "url": "https://www.ubisoft.com/en-us/game/riders-republic"},
    {"slug": "skull-and-bones",             "url": "https://www.ubisoft.com/en-us/game/skull-and-bones"},
    {"slug": "prince-of-persia-lost-crown", "url": "https://www.ubisoft.com/en-us/game/prince-of-persia/the-lost-crown"},
    {"slug": "anno-1800",                   "url": "https://www.ubisoft.com/en-us/game/anno-1800"},
]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ================================================================
# SECTION 2 -- THE SCRAPER
# Visits each Ubisoft game page and extracts all 6 required fields
# ================================================================

def scrape_game(game):
    """
    Visit one Ubisoft game page and extract:
      1. Game Title
      2. Release Date
      3. Key Features
      4. Platform Availability
      5. Developer Information
      6. Publisher Information
    All fields default to "Not Available" if not found.
    """
    result = {
        "game_title":   "Not Available",
        "release_date": "Not Available",
        "key_features": "Not Available",
        "platforms":    "Not Available",
        "developer":    "Not Available",
        "publisher":    "Not Available",
        "url":          game["url"],
        "slug":         game["slug"],
        "scraped_at":   datetime.datetime.now().isoformat(),
    }

    try:
        response = requests.get(game["url"], headers=REQUEST_HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # -- FIELD 1: Game Title
        for selector in ["h1", ".game-title", ".hero-title", '[class*="title"]']:
            tag = soup.select_one(selector)
            if tag:
                text = tag.get_text(strip=True)
                if len(text) > 2:
                    result["game_title"] = text
                    break

        # -- FIELD 2: Release Date
        full_text = soup.get_text()
        date_match = re.search(
            r'(?:release\s*date|released|available)[:\s]*'
            r'([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})',
            full_text, re.IGNORECASE
        )
        if date_match:
            result["release_date"] = date_match.group(1).strip()
        else:
            for meta in soup.find_all("meta"):
                content = meta.get("content", "")
                name    = meta.get("name", "") + meta.get("property", "")
                if "date" in name.lower() and re.search(r'\d{4}', content):
                    result["release_date"] = content.strip()
                    break
            if result["release_date"] == "Not Available":
                year_match = re.search(r'\b(202[0-9]|201[0-9])\b', full_text)
                if year_match:
                    result["release_date"] = year_match.group(1)

        # -- FIELD 3: Key Features
        features = []
        for selector in ['[class*="feature"]','[class*="highlight"]',
                         '[class*="description"]','[class*="overview"]','[class*="about"]']:
            tags = soup.select(selector)
            for tag in tags:
                text = tag.get_text(strip=True)
                if len(text) > 40:
                    features.append(text[:200])
                    break
            if features:
                break
        if not features:
            meta_desc = (soup.find("meta", attrs={"name": "description"}) or
                         soup.find("meta", attrs={"property": "og:description"}))
            if meta_desc and meta_desc.get("content"):
                features.append(meta_desc["content"][:300])
        if not features:
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 60:
                    features.append(text[:300])
                    break
        result["key_features"] = " | ".join(features[:3]) if features else "Not Available"

        # -- FIELD 4: Platform Availability
        platform_keywords = {
            "PlayStation 5":  ["playstation 5", "ps5"],
            "PlayStation 4":  ["playstation 4", "ps4"],
            "Xbox Series X":  ["xbox series x", "xbox series"],
            "Xbox One":       ["xbox one"],
            "PC":             ["pc", "windows", "ubisoft connect"],
            "Nintendo Switch":["nintendo switch", "switch"],
            "Stadia":         ["stadia"],
        }
        page_lower = full_text.lower()
        found = [p for p, kws in platform_keywords.items() if any(k in page_lower for k in kws)]
        result["platforms"] = ", ".join(found) if found else "Not Available"

        # -- FIELD 5: Developer
        dev_match = re.search(
            r'(?:developed?\s+by|developer)[:\s]+([A-Za-z\s\-]+(?:Studios?|Montreal|Paris|Toronto|Quebec|Massive|Reflections)?)',
            full_text, re.IGNORECASE
        )
        if dev_match:
            result["developer"] = dev_match.group(1).strip()[:80]
        else:
            result["developer"] = "Ubisoft"

        # -- FIELD 6: Publisher
        pub_match = re.search(
            r'(?:published?\s+by|publisher)[:\s]+([A-Za-z\s\-]+)',
            full_text, re.IGNORECASE
        )
        if pub_match:
            result["publisher"] = pub_match.group(1).strip()[:80]
        else:
            result["publisher"] = "Ubisoft Entertainment"

    except Exception as e:
        result["scrape_error"] = str(e)

    return result


# ================================================================
# SECTION 3 -- SCRAPE SESSION
# ================================================================

def run_scraper():
    """
    Scrape all UBISOFT_GAMES one by one.
    Saves to:
      data/games.json  (used by dashboard)
      csv/games.csv    (for offline review)
    """
    games = []

    for i, game in enumerate(UBISOFT_GAMES):
        print(f"  [{i+1}/{len(UBISOFT_GAMES)}] Scraping: {game['url']}")
        data = scrape_game(game)
        games.append(data)
        if i < len(UBISOFT_GAMES) - 1:
            time.sleep(2)   # robots.txt compliance

    # Save JSON
    json_path = os.path.join(DATA_DIR, "games.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)
    print(f"  Saved -> {json_path}")

    # Save CSV
    csv_path = os.path.join(CSV_DIR, "games.csv")
    fields = ["game_title","release_date","key_features",
              "platforms","developer","publisher","url","scraped_at"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(games)
    print(f"  Saved -> {csv_path}")

    return games


def load_local_data():
    """Load cached JSON data for offline / presentation mode."""
    json_path = os.path.join(DATA_DIR, "games.json")
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    return []


# ================================================================
# SECTION 4 -- FLASK ROUTES
# ================================================================

@app.route("/")
def index():
    """Serve the dashboard from the html/ folder."""
    html_path = os.path.join(HTML_DIR, "index.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """Trigger live scraper."""
    try:
        games = run_scraper()
        return jsonify({"status": "ok", "count": len(games), "games": games})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/data")
def api_data():
    """Return cached data."""
    games = load_local_data()
    return jsonify({"games": games, "count": len(games)})


@app.route("/api/export/csv")
def api_export_csv():
    """Download the CSV file."""
    path = os.path.join(CSV_DIR, "games.csv")
    if not os.path.exists(path):
        return jsonify({"error": "No data yet. Run scraper first."}), 404
    return send_file(path, as_attachment=True,
                     download_name="ubisoft_games.csv", mimetype="text/csv")


@app.route("/api/export/json")
def api_export_json():
    """Download the JSON file."""
    path = os.path.join(DATA_DIR, "games.json")
    if not os.path.exists(path):
        return jsonify({"error": "No data yet. Run scraper first."}), 404
    return send_file(path, as_attachment=True,
                     download_name="ubisoft_games.json", mimetype="application/json")


# ================================================================
# ENTRY POINT
# Run:  py app.py
# Open: http://localhost:5050
# ================================================================
if __name__ == "__main__":
    print("=" * 50)
    print("  Ubisoft Gaming Scraper")
    print("  Dashboard: http://localhost:5050")
    print("=" * 50)
    app.run(debug=True, port=5050)
