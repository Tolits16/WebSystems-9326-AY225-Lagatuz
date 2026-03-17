# Ubisoft Gaming Industry Web Scraper
### Web Systems - Midterms Project

## How to Run
1. Open terminal inside the `python/` folder
2. Run: pip install flask requests beautifulsoup4
3. Run: py app.py
4. Open: http://localhost:5050

## Folder Structure
```
ubisoft_scraper/
  python/  <- app.py (scraper + Flask backend)
  html/    <- index.html (web dashboard)
  data/    <- games.json (saved after scraping)
  csv/     <- games.csv  (saved after scraping)
```

## Fields Scraped
1. Game Title
2. Release Date
3. Key Features
4. Platform Availability
5. Developer
6. Publisher
