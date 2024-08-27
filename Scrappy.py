from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)

visited_urls = set()


class Article:
    def __init__(self):
        self.title = ''
        self.price = 0.0
        self.reviews = 0.0
        self.rating = 0.0
        self.discount = 0.0
        self.image = None
        self.url = None
        self.description = ''
        self.bought = ''

    def to_dict(self):
        return {
            "title": self.title,
            "price": self.price,
            "reviews": self.reviews,
            "rating": self.rating,
            "discount": self.discount,
            "image": self.image,
            "url": self.url,
            "description": self.description,
            "bought": self.bought,
        }


def get_soup(url: str) -> BeautifulSoup | None:
    try:
        response = requests.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'lxml')
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None


def get_title(soup):
    if soup:
        title_tag = soup.select_one("#productTitle")
        return title_tag.get_text(strip=True) if title_tag else 'No title found'
    return 'No title found'


def get_price(soup):
    if soup:
        price_tag = soup.select_one('span.a-offscreen')
        return price_tag.get_text(strip=True) if price_tag else 'No price found'
    return 'No price found'


def get_bought(soup):
    if soup:
        bought = soup.select_one('#social-proofing-faceout-title-tk_bought')
        return bought.get_text(strip=True) if bought else None
    return None


def get_reviews(soup):
    if soup:
        review_tag = soup.select_one("#acrCustomerReviewText")
        return review_tag.get_text(strip=True) if review_tag else 'No reviews found'
    return 'No reviews found'


def get_rating(soup):
    if soup:
        rating_tag = soup.select_one("#acrPopover")
        return rating_tag.get_text(strip=True) if rating_tag else 'No rating found'
    return 'No rating found'


def get_image(soup):
    if soup:
        image_tag = soup.select_one("#landingImage")
        return image_tag.attrs.get("src") if image_tag else None
    return None


def get_description(soup):
    if soup:
        description_tag = soup.select_one("#feature-bullets")
        return description_tag.text.strip() if description_tag else None
    return None


def get_product_info(url):
    soup = get_soup(url)
    if not soup:
        return None

    return {
        "title": get_title(soup),
        "price": get_price(soup),
        "reviews": get_reviews(soup),
        "bought": get_bought(soup),
        "image": get_image(soup),
        "description": get_description(soup),
    }


def parse_listing(listing_url):
    global visited_urls
    response = requests.get(listing_url)
    print(response.status_code)

    soup_search = BeautifulSoup(response.text, "lxml")
    link_elements = soup_search.select("[data-asin] h2 a")
    page_data = []
    print('Nice')

    for link in link_elements:
        full_url = urljoin(listing_url, link.attrs.get("href"))
        if full_url not in visited_urls:
            visited_urls.add(full_url)
            print(f"Scraping product from {full_url[:100]}", flush=True)
            product_info = get_product_info(full_url)
            if product_info:
                page_data.append(product_info)

    next_page_el = soup_search.select_one('a.s-pagination-next')
    if next_page_el:
        next_page_url = next_page_el.attrs.get('href')
        next_page_url = urljoin(listing_url, next_page_url)
        print(f'Scraping next page: {next_page_url}', flush=True)
        page_data += parse_listing(next_page_url)

    return page_data


@app.route('/Scrappy-product', methods=['POST'])
def scrape_product():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400

    soup = get_soup(url)
    if not soup:
        return jsonify({"error": "Failed to retrieve content from URL"}), 500

    article = Article()
    article.title = get_title(soup)
    article.price = get_price(soup)
    article.description = get_description(soup)
    article.bought = get_bought(soup)
    article.image = get_image(soup)
    article.url = url
    article.rating = get_rating(soup)
    article.reviews = get_reviews(soup)
    return jsonify(article.to_dict())


@app.route('/Scrappy-list', methods=['POST'])
def scrape_list():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        listing_info = parse_listing(url)
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": "An error occurred while processing the request"}), 500

    if not listing_info:
        return jsonify({"error": "Failed to retrieve content from URL"}), 500

    return jsonify(listing_info), 200


if __name__ == '__main__':
    app.run(debug=True)
