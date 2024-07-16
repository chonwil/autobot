import re
from typing import List, Dict, Any
from collections import Counter
from fuzzywuzzy import fuzz
from loguru import logger
from shared.utils import DBHelper
from lib.processor_result import ProcessorResult

class LaunchesConnector:
    def __init__(self):
        self.db = DBHelper()
        self.models = None

    def connect(self) -> ProcessorResult:
        result = ProcessorResult(action="connect", entity="launches")
        
        # Part 1: Connect launches to car models
        launches = self._get_unconnected_launches()
        for launch in launches:
            try:
                car_model = self._find_matching_car_model(launch)
                if car_model:
                    self._update_launch(launch['id'], car_model['id'])
                    result.items_processed += 1
            except Exception as e:
                logger.error(f"Error processing launch ID {launch['id']}: {str(e)}")
        
        # Part 2: Populate similar_cars table
        cars_to_process = self._get_cars_not_in_similar_cars()
        for car in cars_to_process:
            try:
                similar_cars = self._get_similar_cars(car['id'], car['launch_id'])
                self._add_similar_cars(car['id'], similar_cars)
                logger.info(f"Found {len(similar_cars)} similar cars for car ID {car['id']}")
                result.items_processed += len(similar_cars)
            except Exception as e:
                logger.error(f"Error processing similar cars for car ID {car['id']}: {str(e)}")
        
        return result

    def _get_unconnected_launches(self) -> List[Dict[str, Any]]:
        return self.db.execute_query("""
            SELECT DISTINCT l.id, 
                   ARRAY_AGG(c.full_model_name) AS full_model_names
            FROM launches l
            JOIN cars c ON l.id = c.launch_id
            WHERE l.car_model_id IS NULL
            GROUP BY l.id
        """)

    def _get_car_models(self) -> List[Dict[str, Any]]:
        return self.db.execute_query("SELECT id, make, model FROM car_models")

    def _find_matching_car_model(self, launch: Dict[str, Any]) -> Dict[str, Any]:
        self.models = self.models or self._get_car_models()
        car_models = self.models
        best_match = None
        highest_ratio = 0

        # Select the most common full_model_name
        full_model_name = self._select_most_common_model(launch['full_model_names'])
        full_model_name = self._normalize_string(full_model_name)

        for car_model in car_models:
            combined_name = self._normalize_string(f"{car_model['make']} {car_model['model']}")
            ratio = fuzz.partial_ratio(full_model_name, combined_name)

            if ratio > highest_ratio:
                if ratio == 100:
                    return car_model
                highest_ratio = ratio
                best_match = car_model
        
        logger.warning(f"No matching car model found for {full_model_name}. Highest ratio: {highest_ratio}, best match: {best_match['make']} {best_match['model']}")
        return None

    def _select_most_common_model(self, full_model_names: List[str]) -> str:
        counter = Counter(full_model_names)
        most_common = counter.most_common(1)
        return most_common[0][0] if most_common else ''

    def _normalize_string(self, s: str) -> str:
        # Remove special characters and convert to lowercase
        return re.sub(r'[^a-zA-Z0-9\s]', '', s).lower()

    def _update_launch(self, launch_id: int, car_model_id: int) -> None:
        self.db.execute_query(
            "UPDATE launches SET car_model_id = %s WHERE id = %s",
            (car_model_id, launch_id)
        )
        logger.info(f"Updated launch ID {launch_id} with car_model_id {car_model_id}")
        
    def _get_cars_not_in_similar_cars(self) -> List[Dict[str, Any]]:
        return self.db.execute_query("""
            SELECT DISTINCT c.id, c.launch_id
            FROM cars c
            LEFT JOIN similar_cars sc ON c.id = sc.launch_car_id
            WHERE sc.launch_car_id IS NULL
        """)

    def _get_similar_cars(self, car_id: int, launch_id: int) -> List[int]:
        similar_launches = self.db.execute_query("""
            SELECT DISTINCT sl.url
            FROM similar_launches sl
            WHERE sl.launch_id = %s
        """, (launch_id,))

        similar_car_ids = []
        for similar_launch in similar_launches:
            similar_cars = self.db.execute_query("""
                SELECT c.id
                FROM cars c
                LEFT JOIN launches l ON l.id = c.launch_id
                LEFT JOIN posts p ON l.post_id = p.id
                WHERE p.url = %s AND c.id != %s
            """, (similar_launch['url'], car_id))
            similar_car_ids.extend([car['id'] for car in similar_cars])

        return similar_car_ids

    def _add_similar_cars(self, car_id: int, similar_car_ids: List[int]) -> None:
        for similar_car_id in similar_car_ids:
            # Check if the relationship already exists
            existing = self.db.execute_query("""
                SELECT 1 FROM similar_cars
                WHERE launch_car_id = %s AND similar_car_id = %s
            """, (car_id, similar_car_id))

            if not existing:
                self.db.execute_query("""
                    INSERT INTO similar_cars (launch_car_id, similar_car_id)
                    VALUES (%s, %s)
                """, (car_id, similar_car_id))
                logger.info(f"Added similar car relationship: {car_id} - {similar_car_id}")
