from typing import List, Dict, Tuple
from loguru import logger
from shared.utils import DBHelper
from lib.processor_result import ProcessorResult
from fuzzywuzzy import fuzz
from collections import defaultdict
import numpy as np
from scipy.optimize import linear_sum_assignment

class PricesConnector:
    def __init__(self):
        self.db = DBHelper()

    def connect(self) -> ProcessorResult:
        result = ProcessorResult(action="connect", entity="prices")
        unprocessed_prices = self._get_unprocessed_prices()
        
        # Group prices by launch_url
        prices_by_url = defaultdict(list)
        for price in unprocessed_prices:
            prices_by_url[price['launch_url']].append(price)
        
        for launch_url, prices in prices_by_url.items():
            try:
                self._process_prices_for_url(launch_url, prices)
                result.items_processed += len(prices)
            except Exception as e:
                logger.error(f"Error processing prices for URL {launch_url}: {str(e)}")
        
        return result

    def _get_unprocessed_prices(self) -> List[Dict]:
        return self.db.execute_query("""
            SELECT id, launch_url, name, price
            FROM car_prices
            WHERE date_processed IS NULL
        """)

    def _process_prices_for_url(self, launch_url: str, prices: List[Dict]) -> None:
        cars = self._get_cars_for_launch_url(launch_url)
        
        if not cars:
            logger.warning(f"No cars found for launch URL: {launch_url}")
            for price in prices:
                self._mark_price_as_processed(price['id'])
            return

        matches = self._match_cars_to_prices(cars, prices)
        
        for car, price in matches:
            if car and price:
                self._update_car_price(car, price['price'])
            self._mark_price_as_processed(price['id'])

    def _get_cars_for_launch_url(self, launch_url: str) -> List[Dict]:
        return self.db.execute_query("""
            SELECT c.id, c.variant, c.current_price, c.price_date
            FROM cars c
            JOIN launches l ON c.launch_id = l.id
            JOIN posts p ON l.post_id = p.id
            WHERE p.url = %s
        """, (launch_url,))

    def _match_cars_to_prices(self, cars: List[Dict], prices: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """
        Match cars to prices using the Hungarian algorithm for optimal assignment,
        without applying any similarity threshold.
        """
        # Create a similarity matrix (higher is better)
        similarity_matrix = np.zeros((len(cars), len(prices)))
        for i, car in enumerate(cars):
            for j, price in enumerate(prices):
                similarity_matrix[i][j] = fuzz.ratio(car['variant'].lower(), price['name'].lower())

        # Convert to a cost matrix (lower is better)
        cost_matrix = np.max(similarity_matrix) - similarity_matrix

        # Apply the Hungarian algorithm
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        # Create the matches
        matches = []
        matched_cars = set()
        matched_prices = set()

        for i, j in zip(row_ind, col_ind):
            matches.append((cars[i], prices[j]))
            matched_cars.add(i)
            matched_prices.add(j)

        # Add any unmatched cars or prices
        for i in range(len(cars)):
            if i not in matched_cars:
                matches.append((cars[i], None))
        for j in range(len(prices)):
            if j not in matched_prices:
                matches.append((None, prices[j]))

        # Log the matches for debugging
        for car, price in matches:
            if car and price:
                similarity = fuzz.ratio(car['variant'].lower(), price['name'].lower())
                logger.info(f"Matched car variant '{car['variant']}' to price name '{price['name']}' with similarity {similarity}")
            elif car:
                logger.info(f"Unmatched car variant: {car['variant']}")
            elif price:
                logger.info(f"Unmatched price name: {price['name']}")

        return matches

    def _update_car_price(self, car: Dict, new_price: int) -> None:
        if car['current_price'] != new_price:
            self.db.execute_query("""
                UPDATE cars
                SET current_price = %s, price_date = NOW()
                WHERE id = %s
            """, (new_price, car['id']))
            logger.info(f"Updated price for car {car['id']} from {car['current_price']} to {new_price}")

    def _mark_price_as_processed(self, price_id: int) -> None:
        self.db.execute_query("""
            UPDATE car_prices
            SET date_processed = NOW()
            WHERE id = %s
        """, (price_id,))
        pass