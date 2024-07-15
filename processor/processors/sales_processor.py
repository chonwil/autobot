from shared.utils import DBHelper
from lib.processor_result import ProcessorResult
from loguru import logger
from typing import List, Dict

CAR_BRANDS = [
    "Alfa Romeo", "Audi", "BMW", "BYD", "Baic", "Bestune", "Brilliance", "Changan", "Chery", "Chevrolet", "Citroën", "DFM", "DFSK", "Dodge", "Dongfeng", "FAW", "Fiat", "Ford", "Foton"
    "Geely", "Great Wall", "Haval" "Honda", "Hyundai", "Iveco", "JAC", "JMC" "Jaguar", "Jeep", "Jetour", "Kaiyi", "Karry", "Kia", "Land Rover", "Leapmotor", "MG", "MINI", "Maple", "Maserati", "Maxus", "Mazda",
    "Mercedes-AMG", "Mercedes-Benz", "Mitsubishi", "Nissan", "Omoda", "Opel", "Peugeot", "Porsche", "RAM", "Renault", "Seat", "Suzuki", "Subaru", "Toyota", "Victory", "Volkswagen", "Volvo", "ZNA"
]

MULTIPLE_WORD_CAR_MODELS = ["M2 Competition", "M3 Competition", "M4 Competition", "M8 Competition", "Serie 1", "Serie 2", "Serie 3", "Serie 4", "Serie 5", "Serie 6", "Serie 7", "Serie 8",
                            "New F3", "New e2", "New CS15", "Tiggo 2", "Tiggo 4", "Tiggo 7", "Tiggo 8", "Serie K", "Serie C", "Serie EC", "Serie V", "Grand Siena", "Nueva Strada", "Mobi Trekking",
                            "View Cargo", "Toano Cargo", "New Coolray", "Grand i10", "New Kona", "Touring Cargo", "Grand Cherokee", "Range Evoque", "Range Rover", "Range Sport", "Range Velar" "Cooper S", 
                            "Cooper SE", "John Cooper Works", "Clase A", "Clase C", "Clase CLA", "Clase B", "Clase E", "Clase G", "Clase S", "New Sentra", "New Versa", "New 2008", "New 208", "Grand Captur", 
                            "Grand Vitara", "Land Cruiser"]

class CarModel:
    def __init__(self, make: str, model: str):
        self.make = make
        self.model = model

class SalesProcessor:
    def __init__(self):
        self.db = DBHelper()

    def process(self) -> ProcessorResult:
        result = ProcessorResult(action="process", entity="sales")
        models = self._extract_car_models()
        result.items_processed += self._save_car_models(models)
        result.items_processed += self._classify_sales()
        return result
    
    def _extract_car_models(self) -> List[CarModel]:
        model_names = self.db.execute_query("SELECT DISTINCT model FROM unclassified_car_sales ORDER BY model ASC")
        logger.info(f"Extracting car models from {len(model_names)} unclassified sales.")
        
        return [self._parse_model_name(model["model"]) for model in model_names]

    def _parse_model_name(self, model_name: str) -> CarModel:
        make = next((brand for brand in CAR_BRANDS if model_name.lower().startswith(brand.lower())), None)
        if not make:
            make = model_name.split()[0]

        remaining_words = model_name.replace(make, "", 1).strip()
        model = next((m for m in MULTIPLE_WORD_CAR_MODELS if m.lower() in remaining_words.lower()), None)
        if not model:
            model = remaining_words.split()[0] if remaining_words else make

        return CarModel(make, model)
        
    def _save_car_models(self, models: List[CarModel]) -> int:
        items_processed = 0

        for car_model in models:
            if not self._model_exists(car_model):
                self.db.execute_query(
                    "INSERT INTO car_models (make, model) VALUES (%s, %s)",
                    (car_model.make, car_model.model)
                )
                items_processed += 1
            
        logger.info(f"Saved {items_processed} new car models.")
        return items_processed

    def _model_exists(self, car_model: CarModel) -> bool:
        existing = self.db.execute_query(
            "SELECT id FROM car_models WHERE make = %s AND model = %s", 
            (car_model.make, car_model.model)
        )
        return bool(existing)
    
    def _classify_sales(self) -> int:
        unclassified_sales = self._get_unclassified_sales()
        items_processed = 0

        for sale in unclassified_sales:
            car_model = self._find_car_model(sale['model'])
            if car_model:
                if not self._sale_exists(sale, car_model[0]['id']):
                    self._insert_classified_sale(sale, car_model[0])
                    self._delete_unclassified_sale(sale)
                    items_processed += 1
                    self._log_classification(sale, car_model[0], "Classified")
                else:
                    self._log_classification(sale, car_model[0], "Already classified")
                    self._delete_unclassified_sale(sale)
            else:
                logger.warning(f"Could not classify sale: {sale['model']}, {sale['units']} units, {sale['year']}-{sale['month']}")

        return items_processed

    def _get_unclassified_sales(self) -> List[Dict]:
        return self.db.execute_query("""
            SELECT us.sales_report_id, us.model, us.units, sr.year, sr.month
            FROM unclassified_car_sales us
            JOIN sales_reports sr ON us.sales_report_id = sr.id
        """)

    def _find_car_model(self, model_name: str) -> List[Dict]:
        return self.db.execute_query("""
            SELECT id, make, model 
            FROM car_models 
            WHERE LOWER(%s) LIKE CONCAT('%%', LOWER(make), ' ', LOWER(model), '%%')
        """, (model_name,))

    def _sale_exists(self, sale: Dict, car_model_id: int) -> bool:
        existing_sale = self.db.execute_query("""
            SELECT * FROM car_sales 
            WHERE sales_report_id = %s AND car_model_id = %s
        """, (sale['sales_report_id'], car_model_id))
        return bool(existing_sale)

    def _insert_classified_sale(self, sale: Dict, car_model: Dict):
        self.db.execute_query("""
            INSERT INTO car_sales (sales_report_id, car_model_id, units)
            VALUES (%s, %s, %s)
        """, (sale['sales_report_id'], car_model['id'], sale['units']))

    def _delete_unclassified_sale(self, sale: Dict):
        self.db.execute_query(
            "DELETE FROM unclassified_car_sales WHERE sales_report_id = %s AND model = %s", 
            (sale['sales_report_id'], sale['model'])
        )

    def _log_classification(self, sale: Dict, car_model: Dict, status: str):
        logger.info(f"{status} sale: {car_model['make']} {car_model['model']}, {sale['units']} units, {sale['year']}-{sale['month']}")