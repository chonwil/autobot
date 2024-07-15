from shared.utils import DBHelper
from lib.processor_result import ProcessorResult
from bs4 import BeautifulSoup
from datetime import datetime
from loguru import logger

class PriceParser:
    def parse(self):
        result = ProcessorResult(action="parse", entity="prices")
        db = DBHelper()
        
        prices_page = db.execute_query("SELECT * FROM posts WHERE type = 'prices' AND date_parsed IS NULL ORDER BY date_scraped DESC LIMIT 1")

        if not prices_page:
            logger.info("No prices to parse. Skipping...")
            return result

        cars = self._extract_car_prices(prices_page[0]["html_content"])
        result.items_processed = self._store_prices(cars)
        db.update("posts", prices_page[0]["id"], {"date_parsed": datetime.now()})

        logger.info(f"Prices post parsed. Stored {result.items_processed} car prices in the database.")
        return result
    
    def _extract_car_prices(self, html_content):
        cars = []
        soup = BeautifulSoup(html_content, 'html.parser')
        for li in soup.find_all("li"):
            if (li.find("a")):
                try:
                    car_url = li.find("a")["href"]
                    car_name = li.find("a").text
                    car_price = ''.join(filter(str.isdigit, li.text.split("-")[-1].strip()))
                    cars.append({"name": car_name, "launch_url": car_url, "price": car_price})
                except Exception as e:
                    logger.error(f"An error occurred: {str(e)} in {li.text}")
        return cars

    def _store_prices(self, cars):
        cars_stored = 0
        db = DBHelper()
        for car in cars:
            try:
                existing_cars = db.select_by_attributes("car_prices", {"name": car["name"]})
                if not existing_cars:
                    db.insert("car_prices", car)
                    cars_stored += 1
            except Exception as e:
                logger.error(f"An error occurred: {str(e)}")
        return cars_stored