import re
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup, NavigableString, Tag
from fuzzywuzzy import fuzz
from loguru import logger
from shared.utils import DBHelper
from lib.processor_result import ProcessorResult

class ArticlesConnector:
    def __init__(self):
        self.db = DBHelper()

    def connect(self) -> ProcessorResult:
        result = ProcessorResult(action="connect", entity="articles")
        
        # Connect articles to launches
        unconnected_articles = self._get_unconnected_articles()
        logger.info(f"Found {len(unconnected_articles)} unconnected articles")

        for article in unconnected_articles:
            try:
                launch_links = self._extract_launch_links(article['html_content'])
                if not launch_links:
                    logger.warning(f"No launch links found for article ID {article['id']}")
                    continue

                car_names = self._get_car_names_for_launches(launch_links)
                if not car_names:
                    logger.warning(f"No car names found for article ID {article['id']}")
                    continue

                best_match = self._find_best_match(article['title'], car_names, threshold=65)
                if best_match:
                    self._update_article(article['id'], best_match[1])
                    result.items_processed += 1
                    logger.info(f"Connected article '{article['title']}' to launch with car {best_match[0]}, score: {best_match[2]}")
                else:
                    logger.warning(f"No matching car found for article ID {article['id']}")

            except Exception as e:
                logger.error(f"Error processing article ID {article['id']}: {str(e)}")

        # Connect articles to main cars
        unlinked_articles = self._get_articles_without_car_link()
        logger.info(f"Found {len(unlinked_articles)} articles unlinked to main cars")

        for article in unlinked_articles:
            try:
                car_names = self._get_car_names_for_launch(article['related_launch_id'])
                if not car_names:
                    logger.warning(f"No car names found for article ID {article['id']}")
                    continue

                best_match = self._find_best_match(article['title'], car_names, threshold=70)
                if best_match:
                    self._link_article_to_car(article['id'], best_match[1])
                    result.items_processed += 1
                    logger.info(f"Connected article '{article['title']}' to car {best_match[0]}, score: {best_match[2]}")
                    logger.info(f"Linked article ID {article['id']} to car ID {best_match[1]}")
                else:
                    logger.warning(f"No matching car found for article ID {article['id']} with threshold 70")

            except Exception as e:
                logger.error(f"Error linking article ID {article['id']} to car: {str(e)}")

        return result

    def _get_unconnected_articles(self) -> List[Dict[str, Any]]:
        return self.db.execute_query("""
            SELECT a.id, a.title, p.html_content
            FROM articles a
            JOIN posts p ON a.post_id = p.id
            WHERE a.related_launch_url IS NULL
        """)

    def _get_articles_without_car_link(self) -> List[Dict[str, Any]]:
        return self.db.execute_query("""
            SELECT a.id, a.title, l.id AS related_launch_id
            FROM articles a
            JOIN posts p ON a.post_id = p.id
            JOIN launches l ON l.post_id = (SELECT p2.id FROM posts p2 WHERE url = a.related_launch_url LIMIT 1)
            LEFT JOIN car_articles ca ON a.id = ca.article_id
            WHERE ca.article_id IS NULL AND a.related_launch_url IS NOT NULL
        """)

    def _extract_launch_links(self, html_content: str) -> List[str]:
        soup = BeautifulSoup(html_content, 'html.parser')
        launch_links = []

        for element in soup.recursiveChildGenerator():
            if isinstance(element, NavigableString):
                if "COMPETIDORES" in element.strip().upper():
                    break
            elif isinstance(element, Tag):
                if element.name == 'a' and element.has_attr('href'):
                    href = element['href']
                    if "www.autoblog.com.uy" in href and "lanzamiento" in href:
                        launch_links.append(href)

        return launch_links

    def _get_car_names_for_launches(self, launch_links: List[str]) -> List[Tuple[str, int]]:
        placeholders = ','.join(['%s'] * len(launch_links))
        query = f"""
            SELECT DISTINCT c.full_model_name || ' ' || c.variant AS car_name, l.id AS launch_id
            FROM cars c
            JOIN launches l ON c.launch_id = l.id
            JOIN posts p ON l.post_id = p.id
            WHERE p.url IN ({placeholders})
        """
        results = self.db.execute_query(query, tuple(launch_links))
        return [(result['car_name'], result['launch_id']) for result in results]
    
    def _get_car_names_for_launch(self, launch_id: int) -> List[Tuple[str, int]]:
        query = """
            SELECT DISTINCT c.full_model_name || ' ' || c.variant AS car_name, c.id AS car_id
            FROM cars c
            WHERE c.launch_id = %s
        """
        results = self.db.execute_query(query, (launch_id,))
        return [(result['car_name'], result['car_id']) for result in results]

    def _find_best_match(self, article_title: str, car_names: List[Tuple[str, int]], threshold: int = 65) -> Tuple[str, int, int]:
        best_match = None
        highest_ratio = 0

        for car_name, car_id in car_names:
            ratio = fuzz.partial_ratio(self._normalize_string(article_title), self._normalize_string(car_name))
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match = (car_name, car_id, highest_ratio)

        if ratio >= threshold:
            return best_match
        return None

    @staticmethod
    def _normalize_string(s: str) -> str:
        return re.sub(r'[^a-zA-Z0-9\s]', '', s).lower()

    def _update_article(self, article_id: int, launch_id: int) -> None:
        self.db.execute_query("""
            UPDATE articles
            SET related_launch_url = (SELECT url FROM posts WHERE id = (SELECT post_id FROM launches WHERE id = %s))
            WHERE id = %s
        """, (launch_id, article_id))

    def _link_article_to_car(self, article_id: int, car_id: int) -> None:
        self.db.execute_query("""
            INSERT INTO car_articles (article_id, car_id)
            VALUES (%s, %s)
            ON CONFLICT (article_id, car_id) DO NOTHING
        """, (article_id, car_id))
        pass