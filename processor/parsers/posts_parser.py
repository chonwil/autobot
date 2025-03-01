from shared.utils import DBHelper
from lib.processor_result import ProcessorResult
from bs4 import BeautifulSoup, Tag
from datetime import datetime
from loguru import logger
import html
import re

VALID_SECTION_TITLES = [
    "EXTERIOR", "INTERIOR", "MOTOR", "SEGURIDAD", "EQUIPAMIENTO", "PRECIO", "FICHA TÉCNICA",
    "MOTORES, BATERÍA Y TRANSMISIÓN", "A FAVOR", "EN CONTRA", "CONCLUSIÓN", "COMPETIDORES"
]

class PostsParser:
    def parse(self, entities="articles"):
        db = DBHelper()
        result = ProcessorResult(action="parse", entity=entities)
        
        if entities == "articles":
            posts = db.execute_query("SELECT * FROM posts WHERE (type = 'contact' or type='trial') AND date_parsed IS NULL")
        elif entities == "launches":
            posts = db.execute_query("SELECT * FROM posts WHERE type = 'launch' AND date_parsed IS NULL")
        
        for post in posts:
            self._parse_post(post, entities)
            db.update("posts", post["id"], {"date_parsed": datetime.now()})
            result.items_processed += 1
        
        return result
    
    def _parse_post(self, post, entities="articles"):
        db = DBHelper()
        soup = BeautifulSoup(post["html_content"], 'html.parser')
        text_content = html.unescape(soup.get_text(separator=' ', strip=True))
        article = {
            "post_id": post["id"],
            "title": post["title"].replace(" : Autoblog Uruguay | Autoblog.com.uy", "").strip(),
            "content": text_content
        }
        if entities == "articles":
            article["type"] = post["type"]
            comments_soup = BeautifulSoup(post["html_comments"], 'html.parser')
            text_comments = html.unescape(comments_soup.get_text(separator=' ', strip=True))
            article["comments"] = text_comments
            article_id = db.insert("articles", article)
            sections = self._parse_sections(soup)
            self._store_sections(sections, article_id)
            logger.info(f"Parsed article: {article["title"]}")
            
        elif entities == "launches":
            launch_id = db.insert("launches", article)
            similar_launches = self._get_similar_launches(soup)
            self._store_similar_launches(similar_launches, launch_id)
            logger.info(f"Parsed launch: {article["title"]}")
        
        return True
    
    def _parse_sections(self, soup: BeautifulSoup):
        for div in soup.find_all('div'):
            div.insert_before(soup.new_string('\n'))
        text_content = soup.get_text(separator='\n', strip=True)

        sections = []
        current_section = None
        
        # Split the text into lines and process each line
        lines = text_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if the line matches any keyword
            matching_keyword = next((kw for kw in VALID_SECTION_TITLES if (kw.lower() == line.lower().strip()) or ((kw.lower() +":") == line.lower().strip()) ), None)

            if matching_keyword:
                # If we find a new section, save the previous one (if exists) and start a new one
                if current_section:
                    sections.append(current_section)
                # Stop at the "FICHA TÉCNICA" section
                if matching_keyword == "FICHA TÉCNICA":
                    current_section = None
                    break
                current_section = {"title": matching_keyword, "content": ""}
            elif current_section:
                # If we're in a section, append the line to its content
                current_section["content"] += line + " "

        # Add the last section if it exists
        if current_section:
            sections.append(current_section)

        # Clean up the content: remove extra whitespace
        for section in sections:
            section["content"] = re.sub(r'\s+', ' ', section["content"]).strip()

        return sections

            
    def _get_similar_launches(self, soup: BeautifulSoup):
        # Find the tag containing "COMPETIDORES" or "COMPETIDORES:"
        competitors_tag = soup.find(lambda tag: tag.name and tag.string and 
                                    tag.string.strip() in ["COMPETIDORES", "COMPETIDORES:"])
        
        if not competitors_tag:
            return []
        
        # Find all <a> tags after the competitors tag
        links = competitors_tag.find_all_next('a')
        
        # Filter and extract the relevant links
        result = []
        for link in links:
            url = link.get('href', '')
            text = link.get_text(strip=True)
            if 'lanzamiento' in url.lower() and "www.autoblog.com.uy" in url.lower():
                result.append({
                                "url": url,
                                "name": text
                                })
        
        return result


    def _store_sections(self, sections, article_id: int):
        db = DBHelper()
        for section in sections:
            db.insert("article_sections", {
                "article_id": article_id,
                "title": section["title"],
                "content": section["content"]
            })
            
    def _store_similar_launches(self, similar_launches, launch_id: int):
        db = DBHelper()
        for launch in similar_launches:
            db.insert("similar_launches", {
                "launch_id": launch_id,
                "full_model_name": launch["name"],
                "url": launch["url"]
            })
            
    def reprocess_launches(self):
        result = ProcessorResult(action="special", entity="reprocess_similar_launches")
        db = DBHelper()
        db.execute_query("TRUNCATE TABLE similar_launches")
        launches = db.execute_query("""
                                    SELECT l.id, p.html_content, l.title
                                    FROM launches l 
                                    JOIN posts p on l.post_id = p.id""")
        for launch in launches:
            soup = BeautifulSoup(launch["html_content"], 'html.parser')
            similar_launches = self._get_similar_launches(soup)
            if similar_launches:
                self._store_similar_launches(similar_launches, launch["id"])
                logger.info(f"Reprocessed launch: {launch["title"]}")
                result.items_processed += 1
            
        return result
