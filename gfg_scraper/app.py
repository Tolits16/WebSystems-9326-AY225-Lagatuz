"""
================================================================
 GeeksforGeeks Academic Scraper
 Subject: Web Technology
 Description:
   A Flask web application that:
   1. Scrapes Web Technology articles from GeeksforGeeks
   2. Saves the data locally as JSON and CSV (offline capability)
   3. Generates a professional academic PDF learning module
   4. Provides a web dashboard to control everything
================================================================
"""

# -- Standard library imports
import os           # file/folder paths
import json         # saving data as JSON
import csv          # saving data as CSV
import re           # pattern matching in HTML
import time         # crawl delay between requests
import datetime     # timestamps and dates

# -- Flask web framework
from flask import Flask, jsonify, send_file, request, render_template_string

# -- Web scraping libraries
import requests                  # sends HTTP requests to GFG
from bs4 import BeautifulSoup    # parses the HTML we receive

# -- PDF generation library
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# -- App setup
app      = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")   # JSON/CSV saved here
PDF_DIR  = os.path.join(BASE_DIR, "pdfs")   # PDFs saved here
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PDF_DIR,  exist_ok=True)

# Change this to your actual name before presenting
STUDENT_NAME = "Master cedric lagatuz"

# ================================================================
# SECTION 1 -- TARGET URLS
# Only the URLs are listed here. NO article content is hardcoded.
# All data (titles, paragraphs, code) is fetched live from GFG.
# ================================================================
GFG_TOPICS = [
    {"slug": "html",              "url": "https://www.geeksforgeeks.org/html-tutorial/"},
    {"slug": "css",               "url": "https://www.geeksforgeeks.org/css-tutorial/"},
    {"slug": "javascript",        "url": "https://www.geeksforgeeks.org/javascript-tutorial/"},
    {"slug": "http",              "url": "https://www.geeksforgeeks.org/http-full-form/"},
    {"slug": "dns",               "url": "https://www.geeksforgeeks.org/domain-name-system-dns-in-application-layer/"},
    {"slug": "rest-api",          "url": "https://www.geeksforgeeks.org/rest-api-introduction/"},
    {"slug": "web-cookies",       "url": "https://www.geeksforgeeks.org/web-cookies/"},
    {"slug": "tcp-ip",            "url": "https://www.geeksforgeeks.org/tcp-ip-model/"},
    {"slug": "responsive-design", "url": "https://www.geeksforgeeks.org/responsive-web-design/"},
    {"slug": "json",              "url": "https://www.geeksforgeeks.org/javascript-json/"},
    {"slug": "ajax",              "url": "https://www.geeksforgeeks.org/ajax-introduction/"},
    {"slug": "websocket",         "url": "https://www.geeksforgeeks.org/what-is-web-socket-and-how-it-is-different-from-the-http/"},
]

# Browser-like headers so GFG does not block our requests
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ================================================================
# SECTION 2 -- THE SCRAPER
# scrape_article() visits one URL and extracts all 6 fields.
# Every field defaults to "Not Available" as required.
# ================================================================

def scrape_article(topic):
    """
    Visit one GFG article and extract the 6 required fields:
      1. Topic Title       - from the <h1> tag
      2. Difficulty Level  - from GFG badge elements or regex scan
      3. Key Concepts      - from the first real article paragraph
      4. Code Snippet      - from <pre> blocks with actual code
      5. Complexity        - from paragraphs mentioning O() notation
      6. References        - from the References section at article bottom
    """

    # All fields start as "Not Available" -- blank is not allowed
    result = {
        "topic_title":      "Not Available",
        "difficulty_level": "Not Available",
        "key_concepts":     "Not Available",
        "code_snippet":     "Not Available",
        "complexity":       "Not Available",
        "references":       [],
        "url":              topic["url"],
        "slug":             topic["slug"],
        "scraped_at":       datetime.datetime.now().isoformat(),
    }

    try:
        # Fetch the page HTML from GFG
        response = requests.get(topic["url"], headers=REQUEST_HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # --- FIELD 1: Topic Title ---
        # GFG puts the article title inside the first <h1> tag
        h1 = soup.find("h1")
        if h1:
            result["topic_title"] = h1.get_text(strip=True)

        # --- FIELD 2: Difficulty Level ---
        # Strategy A: look for short standalone labels in any tag
        # GFG uses "Easy", "Medium", "Hard" as badge text
        for tag in soup.find_all(["a", "span", "div", "p"]):
            text = tag.get_text(strip=True)
            if text in ("Easy", "Medium", "Hard", "Basic", "Advance"):
                result["difficulty_level"] = text
                break
        # Strategy B: scan full page text for "Difficulty: Medium" patterns
        if result["difficulty_level"] == "Not Available":
            full_text = soup.get_text()
            m = re.search(
                r'(?:difficulty|level)\s*[:\-]?\s*(Easy|Medium|Hard|Basic|Advance)',
                full_text, re.IGNORECASE
            )
            if m:
                result["difficulty_level"] = m.group(1).capitalize()

        # --- FIELD 3: Key Technical Concepts ---
        # GFG wraps article content in a div -- we find the first
        # meaningful paragraph (over 80 characters long)
        article_body = (
            soup.find("div", class_=re.compile(r"article--viewer_ArticleContents", re.I)) or
            soup.find("div", class_=re.compile(r"article-content", re.I)) or
            soup.find("div", class_=re.compile(r"entry-content",   re.I)) or
            soup.find("article")
        )
        if article_body:
            for p in article_body.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 80:
                    result["key_concepts"] = text[:1200]
                    break
        # Fallback: search the entire page if article div not found
        if result["key_concepts"] == "Not Available":
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 100:
                    result["key_concepts"] = text[:1200]
                    break

        # --- FIELD 4: Code Snippet ---
        # GFG wraps code examples in <pre><code> blocks
        # We skip inline snippets (no newlines = not a real code block)
        for pre in soup.find_all("pre"):
            code_text = pre.get_text()
            if "\n" in code_text and len(code_text.strip()) > 30:
                result["code_snippet"] = code_text.strip()[:800]
                break
        # Fallback to <code> tags if no <pre> found
        if result["code_snippet"] == "Not Available":
            for code in soup.find_all("code"):
                code_text = code.get_text()
                if "\n" in code_text and len(code_text.strip()) > 30:
                    result["code_snippet"] = code_text.strip()[:800]
                    break

        # --- FIELD 5: Complexity Analysis ---
        # Collect up to 3 lines that mention time/space complexity
        complexity_parts = []
        for tag in soup.find_all(["p", "li", "td", "h2", "h3", "h4"]):
            text = tag.get_text(strip=True)
            if re.search(r'(time complexity|space complexity|O\s*\()', text, re.IGNORECASE):
                if len(text) > 5 and text not in complexity_parts:
                    complexity_parts.append(text)
                if len(complexity_parts) >= 3:
                    break
        if complexity_parts:
            result["complexity"] = "  |  ".join(complexity_parts)[:600]

        # --- FIELD 6: References / Related Links ---
        # FIX from audit: We specifically target the "References" heading
        # at the bottom of the article, not nav or header links.
        links = []

        # Find the References or Similar Reads section heading
        ref_heading = None
        for tag in soup.find_all(["h2", "h3", "h4", "p", "strong"]):
            if any(kw in tag.get_text(strip=True).lower()
                   for kw in ["references", "similar reads", "related articles", "also read"]):
                ref_heading = tag
                break

        if ref_heading:
            # Collect links from elements that come after the heading
            for sibling in ref_heading.find_next_siblings():
                for a in sibling.find_all("a", href=True):
                    href  = a["href"]
                    label = a.get_text(strip=True)
                    if (href.startswith("https://www.geeksforgeeks.org/") and
                            len(label) > 5 and
                            "/tag/"      not in href and
                            "/category/" not in href):
                        links.append({"label": label[:80], "url": href})
                if len(links) >= 5:
                    break

        # Fallback: collect links from the article body only (not nav/footer)
        if not links and article_body:
            seen = set()
            for a in article_body.find_all("a", href=True):
                href  = a["href"]
                label = a.get_text(strip=True)
                if (href.startswith("https://www.geeksforgeeks.org/") and
                        len(label) > 8 and
                        href not in seen and
                        "/tag/"     not in href and
                        "/category/" not in href and
                        "/courses/"  not in href):
                    links.append({"label": label[:80], "url": href})
                    seen.add(href)
                if len(links) >= 5:
                    break

        result["references"] = links

    except Exception as e:
        result["scrape_error"] = str(e)

    return result


# ================================================================
# SECTION 3 -- SCRAPE SESSION
# Loops through all URLs, respects crawl delay, saves to files.
# ================================================================

def run_scraper():
    """
    Run the full scrape session:
    - Visits each URL in GFG_TOPICS
    - Waits 2 seconds between requests (robots.txt compliance)
    - Saves results to JSON and CSV for offline use
    """
    articles = []

    for i, topic in enumerate(GFG_TOPICS):
        print(f"  [{i+1}/{len(GFG_TOPICS)}] Scraping: {topic['url']}")
        article = scrape_article(topic)
        articles.append(article)

        # robots.txt compliance -- polite crawl delay
        if i < len(GFG_TOPICS) - 1:
            time.sleep(2)

    # Save JSON -- this is what the dashboard and PDF generator read
    json_path = os.path.join(DATA_DIR, "scraped_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    # Save CSV -- for offline review in Excel/Sheets
    csv_path = os.path.join(DATA_DIR, "scraped_data.csv")
    fields = ["topic_title", "difficulty_level", "key_concepts",
              "code_snippet", "complexity", "url", "scraped_at"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(articles)

    return articles


def load_local_data():
    """
    Load previously scraped data from the local JSON file.
    Enables offline / presentation mode -- no internet needed
    after the first scrape has been done.
    """
    json_path = os.path.join(DATA_DIR, "scraped_data.json")
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    return []


# ================================================================
# SECTION 4 -- PDF GENERATOR
# Builds a professional academic PDF from the scraped data.
# Uses ReportLab, a Python library for creating PDFs.
# ================================================================

GREEN   = colors.HexColor("#2F9E44")
DARK    = colors.HexColor("#1A1A2E")
ACCENT  = colors.HexColor("#E8F5E9")
GRAY    = colors.HexColor("#6C757D")
CODE_BG = colors.HexColor("#263238")

DIFF_COLORS = {
    "Easy":    colors.HexColor("#2E7D32"),
    "Medium":  colors.HexColor("#E65100"),
    "Hard":    colors.HexColor("#B71C1C"),
    "Basic":   colors.HexColor("#1565C0"),
    "Advance": colors.HexColor("#6A1B9A"),
}


def _draw_page_chrome(canvas, doc):
    """
    Draws the header and footer on every single page.
    ReportLab calls this automatically for each page.

    Header (top green band):
      - Left:  "Web Technology -- GeeksforGeeks Academic Scraper"
      - Right: Subject category + date

    Footer (bottom dark band):
      - Left:  "Generated by [STUDENT_NAME]"
      - Right: "Page N"
    """
    W, H = A4
    canvas.saveState()

    # Header band
    canvas.setFillColor(GREEN)
    canvas.rect(0, H - 1.4*cm, W, 1.4*cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(1.5*cm, H - 0.85*cm, "Web Technology — GeeksforGeeks Academic Scraper")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(
        W - 1.5*cm, H - 0.85*cm,
        f"Subject: Web Technology  •  {datetime.date.today().strftime('%B %d, %Y')}"
    )

    # Footer band
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, W, 1.1*cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(
        1.5*cm, 0.38*cm,
        f"Generated by {STUDENT_NAME}  •  Source: geeksforgeeks.org  •  For Academic Use Only"
    )
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawRightString(W - 1.5*cm, 0.38*cm, f"Page {doc.page}")

    canvas.restoreState()


def generate_pdf(articles, filename="learning_module.pdf"):
    """
    Build the complete academic PDF.
    Structure:
      Page 1   -- Cover page (title + metadata table)
      Page 2   -- Table of Contents
      Pages 3+ -- One page per article with all 6 fields
    """
    pdf_path = os.path.join(PDF_DIR, filename)

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        topMargin=2.2*cm, bottomMargin=1.8*cm,
        leftMargin=2*cm,  rightMargin=2*cm,
    )

    # Text styles
    s_title    = ParagraphStyle("T",  fontName="Helvetica-Bold", fontSize=28, textColor=DARK,  alignment=TA_CENTER, spaceAfter=8)
    s_subtitle = ParagraphStyle("S",  fontName="Helvetica",      fontSize=13, textColor=GRAY,  alignment=TA_CENTER, spaceAfter=6)
    s_toc_head = ParagraphStyle("TH", fontName="Helvetica-Bold", fontSize=16, textColor=DARK,  spaceAfter=12)
    s_toc_item = ParagraphStyle("TI", fontName="Helvetica",      fontSize=10, textColor=DARK,  leftIndent=12, spaceAfter=5)
    s_art_num  = ParagraphStyle("AN", fontName="Helvetica-Bold", fontSize=18, textColor=GREEN)
    s_art_title= ParagraphStyle("AT", fontName="Helvetica-Bold", fontSize=15, textColor=DARK,  spaceAfter=6)
    s_label    = ParagraphStyle("L",  fontName="Helvetica-Bold", fontSize=9,  textColor=GREEN, spaceBefore=10, spaceAfter=3)
    s_body     = ParagraphStyle("B",  fontName="Helvetica",      fontSize=9.5,textColor=DARK,  leading=15, alignment=TA_JUSTIFY, spaceAfter=4)
    s_code     = ParagraphStyle("C",  fontName="Courier",        fontSize=8,  textColor=colors.white, leading=13, spaceAfter=4)
    s_ref      = ParagraphStyle("R",  fontName="Helvetica",      fontSize=8.5,textColor=colors.HexColor("#1565C0"), leftIndent=14, spaceAfter=3)
    s_badge    = ParagraphStyle("BG", fontName="Helvetica-Bold", fontSize=9,  textColor=colors.white, alignment=TA_CENTER)

    story = []

    # Cover Page
    story.append(Spacer(1, 3.5*cm))
    story.append(HRFlowable(width="100%", thickness=6, color=GREEN, spaceAfter=18))
    story.append(Paragraph("WEB TECHNOLOGY", s_subtitle))
    story.append(Paragraph("Academic Learning Module", s_title))
    story.append(Paragraph("GeeksforGeeks Content Extractor", s_subtitle))
    story.append(HRFlowable(width="60%", thickness=2, color=GREEN, spaceAfter=20))
    story.append(Spacer(1, 0.5*cm))

    cover_meta = [
        ["Subject Category", "Web Technology"],
        ["Total Topics",     str(len(articles))],
        ["Date Generated",   datetime.date.today().strftime("%B %d, %Y")],
        ["Source",           "www.geeksforgeeks.org"],
        ["Prepared by",      STUDENT_NAME],
    ]
    ct = Table(cover_meta, colWidths=[5.5*cm, 9*cm])
    ct.setStyle(TableStyle([
        ("BACKGROUND",     (0,0),(0,-1), ACCENT),
        ("TEXTCOLOR",      (0,0),(0,-1), GREEN),
        ("TEXTCOLOR",      (1,0),(1,-1), DARK),
        ("FONTNAME",       (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTNAME",       (1,0),(1,-1), "Helvetica"),
        ("FONTSIZE",       (0,0),(-1,-1),10),
        ("ROWBACKGROUNDS", (0,0),(-1,-1),[colors.white, ACCENT]),
        ("BOX",            (0,0),(-1,-1),1, GREEN),
        ("INNERGRID",      (0,0),(-1,-1),0.5,colors.HexColor("#C8E6C9")),
        ("PADDING",        (0,0),(-1,-1),8),
        ("VALIGN",         (0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(ct)
    story.append(PageBreak())

    # Table of Contents
    story.append(Paragraph("Table of Contents", s_toc_head))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GREEN, spaceAfter=10))
    toc_rows = []
    for i, art in enumerate(articles, 1):
        title = art.get("topic_title", art["slug"])
        diff  = art.get("difficulty_level", "N/A")
        ds = ParagraphStyle("dc", fontName="Helvetica", fontSize=9, textColor=GREEN, alignment=TA_CENTER)
        toc_rows.append([Paragraph(f"<b>{i:02d}.</b>  {title}", s_toc_item),
                         Paragraph(f"<b>{diff}</b>", ds)])
    tt = Table(toc_rows, colWidths=[13.5*cm, 3*cm])
    tt.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white, ACCENT]),
        ("BOX",          (0,0),(-1,-1),0.5,colors.HexColor("#C8E6C9")),
        ("INNERGRID",    (0,0),(-1,-1),0.5,colors.HexColor("#E8F5E9")),
        ("PADDING",      (0,0),(-1,-1),6),
        ("VALIGN",       (0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(tt)
    story.append(PageBreak())

    # One page per article
    for idx, art in enumerate(articles, 1):
        title    = art.get("topic_title",      art["slug"])
        diff     = art.get("difficulty_level", "Not Available")
        concepts = art.get("key_concepts",     "Not Available")
        code     = art.get("code_snippet",     "Not Available")
        complex_ = art.get("complexity",       "Not Available")
        refs     = art.get("references",       [])

        diff_color = DIFF_COLORS.get(diff, GRAY)
        block = []

        # Article header row
        hdr = Table(
            [[Paragraph(f"{idx:02d}", s_art_num),
              Paragraph(title, s_art_title),
              Paragraph(f"<font color='white'><b> {diff} </b></font>", s_badge)]],
            colWidths=[1.4*cm, 12.5*cm, 2.6*cm]
        )
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (2,0),(2,0), diff_color),
            ("VALIGN",        (0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1),4),
            ("BOTTOMPADDING", (0,0),(-1,-1),4),
            ("LINEBELOW",     (0,0),(-1,0),2, GREEN),
        ]))
        block.append(hdr)
        block.append(Spacer(1, 0.25*cm))

        # Field 3: Key Concepts
        block.append(Paragraph("KEY TECHNICAL CONCEPTS", s_label))
        block.append(Paragraph(concepts, s_body))

        # Field 4: Code Snippet
        block.append(Paragraph("CODE IMPLEMENTATION", s_label))
        if code != "Not Available":
            safe = code.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            cb = Table([[Paragraph(safe, s_code)]], colWidths=[doc.width])
            cb.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,-1),CODE_BG),
                ("PADDING",   (0,0),(-1,-1),10),
                ("BOX",       (0,0),(-1,-1),0.5, GREEN),
            ]))
            block.append(cb)
        else:
            block.append(Paragraph("Not Available", s_body))

        # Field 5: Complexity
        block.append(Paragraph("COMPLEXITY ANALYSIS", s_label))
        block.append(Paragraph(complex_, s_body))

        # Field 6: References
        block.append(Paragraph("REFERENCES / RELATED LINKS", s_label))
        if refs:
            for ref in refs[:5]:
                safe_label = ref["label"].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                block.append(Paragraph(f"• <link href='{ref['url']}'>{safe_label}</link>", s_ref))
        else:
            block.append(Paragraph("Not Available", s_body))

        block.append(Spacer(1, 0.3*cm))
        block.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#C8E6C9"), spaceAfter=6))

        story.append(KeepTogether(block[:6]))
        for item in block[6:]:
            story.append(item)
        if idx < len(articles):
            story.append(PageBreak())

    # Build -- _draw_page_chrome runs on every page
    doc.build(story, onFirstPage=_draw_page_chrome, onLaterPages=_draw_page_chrome)
    return pdf_path


# ================================================================
# SECTION 5 -- FLASK ROUTES
# Each route is one URL that the browser/dashboard can call.
# ================================================================

@app.route("/")
def index():
    html_path = os.path.join(BASE_DIR, "templates", "index.html")
    with open(html_path, encoding="utf-8") as f:
        return render_template_string(f.read())


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """Trigger live scraper. Called by 'Run Scraper' button."""
    try:
        articles = run_scraper()
        return jsonify({"status": "ok", "count": len(articles), "articles": articles})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/data")
def api_data():
    """Return cached data. Called by 'Load Cached Data' button."""
    articles = load_local_data()
    return jsonify({"articles": articles, "count": len(articles)})


@app.route("/api/generate-pdf", methods=["POST"])
def api_generate_pdf():
    """Generate PDF from cached data. Called by 'Generate PDF' button."""
    articles = load_local_data()
    if not articles:
        return jsonify({"error": "No scraped data found. Run the scraper first."}), 400
    try:
        ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"WebTech_LearningModule_{ts}.pdf"
        path     = generate_pdf(articles, filename)
        return jsonify({"status": "ok", "filename": filename, "path": path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<filename>")
def api_download(filename):
    """Send a PDF file to the browser as a download."""
    path = os.path.join(PDF_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    return send_file(path, as_attachment=True,
                     download_name=filename, mimetype="application/pdf")


@app.route("/api/files")
def api_files():
    """Return list of generated PDFs and whether cached data exists."""
    pdfs     = sorted([f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")], reverse=True)
    has_data = os.path.exists(os.path.join(DATA_DIR, "scraped_data.json"))
    return jsonify({"pdfs": pdfs, "has_data": has_data})


# ================================================================
# ENTRY POINT
# Run:  python app.py
# Open: http://localhost:5050
# ================================================================
if __name__ == "__main__":
    print("=" * 50)
    print("  GFG Academic Scraper - Web Technology Project")
    print("  Dashboard: http://localhost:5050")
    print("=" * 50)
    app.run(debug=True, port=5050)
