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
        
        launches = self._get_unconnected_launches()
        
        for launch in launches:
            try:
                car_model = self._find_matching_car_model(launch)
                if car_model:
                    self._update_launch(launch['id'], car_model['id'])
                    result.items_processed += 1
            except Exception as e:
                logger.error(f"Error processing launch ID {launch['id']}: {str(e)}")
        
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