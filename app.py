from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
from newspaper import Article
from datetime import datetime

app = Flask(__name__)

# Function to fetch article URLs dynamically
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

# Function to extract article content
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
        return {"title": "Error Loading Article", "text": str(e), "url": url, "image": None, "date": datetime.now()}

@app.route('/')
def home():
    query = "Karan Veer Mehra bigg boss 18  news articles"
    articles_per_page = 10  # Articles to display per page
    page = int(request.args.get('page', 1))  # Current page, default is 1
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

    return render_template(
        'index.html',
        articles=articles,
        top_articles=top_articles,
        page=page,
        prev_page=prev_page,
        next_page=next_page
    )

if __name__ == "__main__":
    app.run(debug=True)