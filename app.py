from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from newspaper import Article
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import random
import sqlite3

# Initialize FastAPI app
app = FastAPI()

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# SQLite Database Setup
DATABASE = "click_counts.db"

def initialize_database():
    """Create the database and table if not exists."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS button_clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            button_name TEXT UNIQUE,
            click_count INTEGER DEFAULT 0
        )
    """)
    # Insert default buttons if not present
    for button in ["youtube", "wikipedia", "google"]:
        cursor.execute("""
            INSERT OR IGNORE INTO button_clicks (button_name, click_count)
            VALUES (?, ?)
        """, (button, 0))
    conn.commit()
    conn.close()

# Initialize the database
initialize_database()

# Helper Functions
def fetch_article_urls(query, start=0, num_results=10):
    headers = {'User-Agent': 'Mozilla/5.0'}
    search_url = f"https://www.google.com/search?q={query}&start={start}&num={num_results}"
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    links = []
    for a in soup.find_all('a'):
        href = a.get('href')
        if href and "http" in href and "google" not in href:
            links.append(href.split("&")[0].split("?q=")[-1])
    return list(set(links))  # Remove duplicates

def get_random_error_title():
    error_titles = [
        "Karanveer Mehra Steals the Spotlight in Bigg Boss 18!",
        "Drama Unfolds: Karanveer Mehra's Bold Moves in BB18",
        "Bigg Boss 18 Update: Karanveer Mehra's Shocking Revelation!",
        "Karanveer Mehra Emerges as a Fan Favorite in Bigg Boss 18"
    ]
    return random.choice(error_titles)

def extract_article_content(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        publish_date = article.publish_date or datetime.now()  # Use current time if date is missing
        if publish_date.tzinfo is not None:
            publish_date = publish_date.replace(tzinfo=None)
        return {
            "title": article.title,
            "text": article.text[:150],  # Preview text
            "url": url,
            "image": article.top_image,
            "date": publish_date
        }
    except Exception as e:
        return {
            "title": get_random_error_title(),
            "text": "Click on Read More",
            "url": url,
            "image": None,
            "date": datetime.now()
        }

def update_click_count(button_name: str):
    """Increment the click count for a button."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE button_clicks
        SET click_count = click_count + 1
        WHERE button_name = ?
    """, (button_name,))
    conn.commit()
    conn.close()

def get_click_counts():
    """Retrieve all click counts."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT button_name, click_count
        FROM button_clicks
    """)
    counts = cursor.fetchall()
    conn.close()
    return {name: count for name, count in counts}

# Routes
@app.post("/button-click/{button_name}")
async def button_click(button_name: str):
    """Handle button click and update the database."""
    valid_buttons = ["youtube", "wikipedia", "google"]
    if button_name in valid_buttons:
        update_click_count(button_name)
        counts = get_click_counts()
        return JSONResponse(content={"message": f"{button_name.capitalize()} button clicked!", "counts": counts})
    else:
        return JSONResponse(content={"error": "Invalid button name"}, status_code=400)

@app.get("/click-counts")
async def click_counts():
    """Retrieve the current click counts for all buttons."""
    counts = get_click_counts()
    return counts

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, page: int = Query(1)):
    query = "Karan Veer Mehra latest news articles"
    articles_per_page = 10  # Articles to display per page
    start_index = (page - 1) * articles_per_page

    # Fetch articles for the current page
    article_urls = fetch_article_urls(query, start=start_index, num_results=articles_per_page)
    articles = [extract_article_content(url) for url in article_urls]

    # Sort articles by date (newest first)
    articles.sort(key=lambda x: x['date'], reverse=True)

    # Pagination controls
    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if len(article_urls) == articles_per_page else None

    # Top 5 articles for the carousel (always from the latest articles fetched)
    top_articles = articles[:5] if page == 1 else []

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "articles": articles,
            "top_articles": top_articles,
            "page": page,
            "prev_page": prev_page,
            "next_page": next_page,
        }
    )
