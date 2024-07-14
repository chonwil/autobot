import locale
from datetime import datetime, timedelta
from urllib.parse import urlparse
import os
import requests
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from loguru import logger

from utils import DBHelper

# Configure loguru
logger.add("logs/scraper.log", rotation="10 MB", level="INFO")

class ScraperConfig:
    LOCALE = 'es_ES.UTF-8'
    MAX_POST_AGE = 1500  # Maximum age of posts to scrape in days
    URLS = {
        "PRICES": "https://www.autoblog.com.uy/p/precios-0km.html",
        "SALES": "https://www.autoblog.com.uy/search/label/Ventas?max-results=20&by-date=false",
        "LAUNCHES": "https://www.autoblog.com.uy/search/label/Lanzamientos?max-results=20&by-date=false",
        "CONTACT": "https://www.autoblog.com.uy/search/label/Contacto?max-results=20&by-date=false",
        "TRIALS": "https://www.autoblog.com.uy/search/label/Pruebas?max-results=20&by-date=false"
    }

class WebDriverManager:
    @staticmethod
    def get_driver() -> webdriver.Chrome:
        chrome_options = webdriver.ChromeOptions()
        prefs = {"profile.managed_default_content_settings.images": 2}
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(15)
        return driver

class Scraper:
    def __init__(self):
        self.driver = WebDriverManager.get_driver()
        self.posts_scraped = 0
        locale.setlocale(locale.LC_TIME, ScraperConfig.LOCALE)

    def scrape(self, scrape_options: Optional[List[str]] = None, numpages: int = 0) -> int:
        scrape_options = scrape_options or ["prices", "sales", "launches", "contacts", "trials"]
        
        scrape_functions = {
            "prices": self.scrape_prices,
            "sales": lambda: self.scrape_indexed_posts(ScraperConfig.URLS["SALES"], "sales", numpages),
            "launches": lambda: self.scrape_indexed_posts(ScraperConfig.URLS["LAUNCHES"], "launch", numpages),
            "contacts": lambda: self.scrape_indexed_posts(ScraperConfig.URLS["CONTACT"], "contact", numpages),
            "trials": lambda: self.scrape_indexed_posts(ScraperConfig.URLS["TRIALS"], "trial", numpages)
        }
        
        try:
            for option in scrape_options:
                scrape_func = scrape_functions.get(option)
                if scrape_func:
                    self.posts_scraped += scrape_func()
                else:
                    logger.warning(f"Invalid option: {option}. Skipping...")
        except Exception as e:
            logger.exception(f"An error occurred during scraping: {str(e)}")
        finally:
            self.driver.quit()
                
        return self.posts_scraped

    def scrape_prices(self) -> int:
        logger.info("Scraping prices...")
        posts_scraped = 0
        try:
            self.driver.get(ScraperConfig.URLS["PRICES"])
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "main-wrapper")))
            html_content = self.driver.find_element(By.CSS_SELECTOR, "div.post-body.entry-content").get_attribute('outerHTML')
            self.store_page_content(self.driver.current_url, self.driver.title, "prices", html_content)
            posts_scraped += 1
        except TimeoutException:
            logger.error("Timeout occurred while loading the prices post")
        except Exception as e:
            logger.exception(f"An error occurred while scraping prices: {str(e)}")
            
        logger.info("Scraping prices complete")
        return posts_scraped

    def scrape_indexed_posts(self, original_url: str, post_type: str, num_posts: int) -> int:
        posts_scraped = 0
        logger.info(f"Scraping {post_type} pages...")
        url = original_url
        
        try:
            while True:
                self.driver.get(url)
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "main-wrapper")))
                older_link_element = self.driver.find_element(By.CSS_SELECTOR, 'a.blog-pager-older-link') 
                url = older_link_element.get_attribute('href')
                
                posts = self.parse_posts_in_list(self.driver.page_source)
                
                for post in posts:
                    if self.is_valid_for_type(post, post_type) and not self.post_exists_in_db(post):
                        self.scrape_post(post["url"], post_type, post["date"], post["image_url"])
                        posts_scraped += 1
                        
                    if num_posts > 0 and posts_scraped >= num_posts:
                        return posts_scraped
                
                    if datetime.now() - post["date"] > timedelta(days=ScraperConfig.MAX_POST_AGE):
                        return posts_scraped
        except TimeoutException:
            logger.error(f"Timeout occurred while loading the index page {self.driver.current_url}, stopping {post_type} scraping.")
        except Exception as e:
            logger.exception(f"An error occurred while scraping {post_type} pages: {e}")

        logger.info(f"Scraping {post_type} pages complete.")
        return posts_scraped

    @staticmethod
    def parse_posts_in_list(html_content: str) -> List[Dict]:
        soup = BeautifulSoup(html_content, 'html.parser')
        posts = soup.find_all('div', class_='post-outer')
        extracted_data = []

        for post in posts:
            title_tag = post.find('h3', class_='post-title entry-title')
            
            if title_tag:
                title = title_tag.get_text().strip()
                url = title_tag.find('a')['href']
                
                image_container = post.find('div', class_='post-body entry-content')
                image_url = ''
                if image_container:
                    image_tag = image_container.find('img')
                    if image_tag and 'src' in image_tag.attrs:
                        image_url = image_tag['src']
                
                date_script = post.find('script', text=lambda x: x and 'var ultimaFecha' in x)
                if date_script:
                    date_line = date_script.string.strip()
                    date_str = date_line.split('=')[1].strip().strip("';")
                    date_obj = datetime.strptime(date_str, '%A, %d de %B de %Y')
                    extracted_data.append({
                        'title': title,
                        'url': url,
                        'image_url': image_url,
                        'date': date_obj
                    })

        return extracted_data

    def scrape_post(self, url: str, post_type: str, date_published: Optional[datetime] = None, image_url: Optional[str] = None):
        try:
            logger.info(f"Scraping {url}...")
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "main-wrapper")))
            html_content = self.driver.find_element(By.CSS_SELECTOR, "div.post-body.entry-content").get_attribute('outerHTML')
            html_comments = '' if post_type == "prices" else self.scrape_post_comments()
            self.store_page_content(self.driver.current_url, self.driver.title, post_type, html_content, html_comments, date_published, image_url)
        except TimeoutException:
            logger.error(f"Timeout occurred while loading post {url}, continuing with other posts")
        except Exception as e:
            logger.exception(f"An error occurred while scraping post {url}: {e}")

    def scrape_post_comments(self) -> str:
        comments_html = ""
        try:
            disqus_thread_div = self.driver.find_element(By.ID, "disqus_thread")
            iframes = disqus_thread_div.find_elements(By.CSS_SELECTOR, "iframe")
            if len(iframes) > 1:
                self.driver.switch_to.frame(iframes[1])
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "conversation")))
                comments_html = self.driver.find_element(By.ID, "conversation").get_attribute('outerHTML')
                self.driver.switch_to.default_content()
        except TimeoutException:
            logger.error(f"Timeout occurred while loading the comments iframe for {self.driver.current_url}, ignoring comments for this article.")
        except Exception as e:
            logger.exception(f"An error occurred while scraping comments: {e}")

        return comments_html

    @staticmethod
    def is_valid_for_type(post: Dict, post_type: str) -> bool:
        if post_type == "launch":
            return post['title'].startswith("Lanzamiento")
        elif post_type == "trial":
            return post['title'].startswith("Prueba")
        elif post_type == "contact":
            return post['title'].startswith("Contacto")
        elif post_type == "sales":
            return post['title'].startswith("Ventas")
        return True

    @staticmethod
    def post_exists_in_db(post: Dict) -> bool:
        db = DBHelper()
        return db.exists("posts", {"url": post["url"]})

    @staticmethod
    def store_page_content(url: str, title: str, post_type: str, html_content: str, html_comments: str = '',
                           date_published: Optional[datetime] = None, image_url: Optional[str] = None):
        db = DBHelper()
        return db.insert("posts", {
            "url": url,
            "title": title,
            "type": post_type,
            "date_published": date_published,
            "html_content": html_content,
            "html_comments": html_comments,
            "image_url": image_url
        })

def download_page_images():
    """Downloads images from URLs in the database that are not present in the local directory."""
    db = DBHelper()
    image_urls = db.execute_query("SELECT DISTINCT image_url FROM posts WHERE image_url IS NOT NULL AND image_url != ''")

    images_directory = os.path.join(os.path.dirname(__file__), '..', 'shared', 'data', "images", "posts")
    os.makedirs(images_directory, exist_ok=True)

    for url_tuple in image_urls:
        image_url = url_tuple["image_url"]
        parsed_url = urlparse(image_url)
        filename = os.path.basename(parsed_url.path)
        local_path = os.path.join(images_directory, filename)

        if not os.path.exists(local_path):
            try:
                response = requests.get(image_url)
                response.raise_for_status()
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Downloaded and saved: {filename}")
            except Exception as e:
                logger.exception(f"Error downloading {image_url}: {e}")