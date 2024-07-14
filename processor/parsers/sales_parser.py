from shared.utils import DBHelper
from lib.processor_result import ProcessorResult
from bs4 import BeautifulSoup
import re
from datetime import datetime
from loguru import logger


import locale
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

class SalesParser:
    def parse(self):
        db = DBHelper()
        result = ProcessorResult(action="parse", entity="sales")
        
        posts = db.select_by_attributes("posts", {"type": "sales"})
        
        for post in posts:
            if post['date_parsed'] is None and "los 10" not in post['title'].lower():
                date = self._get_month_and_year(post)
                if date:
                    self._parse_post(post, date)
                    db.update("posts", post["id"], {"date_parsed": datetime.now()})
                    logger.info(f"Parsed sales report: {post['title']}")
                    result.items_processed += 1
        
        return result
    
    def _get_month_and_year(self, post):
        # Define a regular expression pattern for Spanish month names and a four-digit year
        month_names = "(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)"
        pattern = re.compile(month_names + r".*(\d{4})", re.IGNORECASE)
        # Search for month and year in the post title
        match = pattern.search(post['title'])
        if match:
            month_name, year = match.groups()
            # Convert month name to number
            month_number = datetime.strptime(month_name, '%B').month
            return {"month": month_number, "year": year}
        
        return None
    
    def _parse_post(self, post, date):
        db = DBHelper()
        sales_report_id = db.insert("sales_reports", {
            "post_id": post["id"],
            "month": date['month'],
            "year": date['year'],
            "type": "monthly"
        })
    
        # Extract data from each li element
        soup = BeautifulSoup(post['html_content'], 'html.parser')
        ventas_anuales_index = soup.text.find("ventas anuales")
        
        if ventas_anuales_index != -1:
            # Convert the index in text to an index in html_content
            ventas_anuales_html_index = post['html_content'].find("ventas anuales")
            
        li_elements = soup.find_all('li')
        prev_li = None
        for li in li_elements:
            # Check if the current li element is before "ventas anuales"
            li_html_index = post['html_content'].find(str(li))
            li_html_index = post['html_content'].find(str(prev_li))
            if ventas_anuales_index < 0 or (li_html_index < ventas_anuales_html_index and (prev_li == None or li_html_index < post['html_content'].find(str(prev_li)))):
                data = self._extract_model_and_units(li.text)

                if data:
                    try:
                        import psycopg2
                        db.insert("unclassified_car_sales", {
                            "sales_report_id": sales_report_id,
                            "model": data["model"],
                            "units": data["units"]
                        })
                    except psycopg2.errors.UniqueViolation as e:
                        logger.warning(f"Error - duplicate car {data["model"]} in report: {post['title']}")
                prev_li = li
            else:
                # Stop the iteration as we've reached the "ventas anuales" part
                break
    
    def _extract_model_and_units(self, text):
        # Remove any HTML tags
        text = re.sub('<[^<]+?>', '', text).strip()
        
        # Split the text into model and units
        parts = text.rsplit(' - ', 1)
        if len(parts) == 2:
            model, units_text = parts
            # Extract the number of units
            units = int(re.search(r'\d+', units_text).group())
            return {
                "model": model.strip(), 
                "units": units
            }
        return None