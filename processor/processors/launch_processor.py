import concurrent.futures
import time
import threading
from typing import Dict, Any, List, Optional, Tuple
from langchain_community.callbacks.manager import get_openai_callback
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.language_models.base import BaseLanguageModel
from shared.utils import DBHelper
from lib.processor_result import ProcessorResult
from loguru import logger
from shared.lib.llm_usage import LLMUsage

class Car(BaseModel):
    launch_price: int = Field(description="Launch price of the car in USD")
    variant: str = Field(description="Specific variant of the car model")
    full_model_name: str = Field(description="Full name of the car model")
    body_type: str = Field(description="Type of car body (e.g., SUV, Sedan)")
    origin_country: str = Field(description="Country where the car is manufactured")
    engine_type: Optional[str] = Field(description="The type of engine. A fully combustion or gasoline engine should be 'Combustión' regardless of whether it has turbo or not. Must be chosen from one of these values: 'Combustión', 'Mild-hybrid', 'Hybrid', 'Plug-in hybrid', 'Eléctrico'")
    power: Optional[int] = Field(description="The power of the car's engine measured in hp")
    torque: Optional[int] = Field(description="The torque output of the car's engine, in Nm")
    num_cylinders: Optional[int] = Field(description="The number of cylinders in the engine")
    num_valves: Optional[int] = Field(description="The number of valves in the engine")
    battery_capacity: Optional[float] = Field(description="The battery capacity in kWh")
    range_kms: Optional[int] = Field(description="The range of the car on a full charge in km")
    transmission_type: Optional[str] = Field(description="The type of transmission. Separate prices for M/T and A/T versions indicates separate car versions with manual and automatic transmissions respectively. Must be chosen from one of these values: 'Manual', 'Automática - Secuencial', 'Automática - CVT', 'Automática - DCT', 'Automática - DSG', 'Automática - Doble embrague', 'Automática - AMT', 'Automática - Tiptronic', 'Automática - Relacion fija', 'Automática - 9G-TRONIC'")
    num_gears: Optional[int] = Field(description="The number of gears in the transmission")
    length: Optional[int] = Field(description="The length of the car in mm")
    width: Optional[int] = Field(description="The width of the car in mm")
    height: Optional[int] = Field(description="The height of the car in mm")
    trunk_capacity: Optional[int] = Field(description="The capacity of the car's trunk in litres")
    maximum_capacity: Optional[int] = Field(description="The maximum cargo capacity of the car in litres")
    fuel_capacity: Optional[int] = Field(description="The capacity of the car's fuel tank in litres")
    ground_clearance: Optional[int] = Field(description="The ground clearance of the car in mm")
    wheelbase: Optional[int] = Field(description="The distance between the centers of the front and rear wheels in mm")
    acceleration_0_100: Optional[float] = Field(description="The time it takes for the car to accelerate from 0 to 100 km/h in seconds")
    max_speed: Optional[int] = Field(description="The maximum speed of the car in km/h")
    fuel_consumption: Optional[float] = Field(description="The fuel consumption of the car in litres per 100km")
    front_suspension: Optional[str] = Field(description="The type of front suspension. Must be chosen from one of these values: 'McPherson', 'Doble horquilla', 'Multilink', 'Eje rígido', 'Barra de torsión semi-independiente', 'Brazo tirado', 'De Dion', 'Paralelo deformable', 'Neumática', 'Suspensión de barra de torsión', 'Suspensión adaptativa'")
    rear_suspension: Optional[str] = Field(description="The type of rear suspension. Must be chosen from one of these values: 'McPherson', 'Doble horquilla', 'Multilink', 'Eje rígido', 'Barra de torsión semi-independiente', 'Brazo tirado', 'De Dion', 'Paralelo deformable', 'Neumática', 'Suspensión de barra de torsión', 'Suspensión adaptativa'")
    front_brakes: Optional[str] = Field(description="The type of front brakes. Must be chosen from one of these values: 'Disco', 'Tambor', 'ABS', 'Cerámicos', 'Regenerativos', 'Estacionamiento eléctrico', 'Hidráulicos', 'Neumáticos', 'Zapata', 'Disco ventilados', 'Disco perforados', 'Disco ranurados', 'Disco flotantes', 'Disco fijos', 'Tambor de doble leva', 'Tambor de leva simple', 'Compresión del motor', 'Electromagnéticos', 'Cinta', 'Hidrostáticos'")
    rear_brakes: Optional[str] = Field(description="The type of rear brakes. Must be chosen from one of these values: 'Disco', 'Tambor', 'ABS', 'Cerámicos', 'Regenerativos', 'Estacionamiento eléctrico', 'Hidráulicos', 'Neumáticos', 'Zapata', 'Disco ventilados', 'Disco perforados', 'Disco ranurados', 'Disco flotantes', 'Disco fijos', 'Tambor de doble leva', 'Tambor de leva simple', 'Compresión del motor', 'Electromagnéticos', 'Cinta', 'Hidrostáticos'")
    traction: Optional[str] = Field(description="The traction type. Must be chosen from one of these values: 'Delantera', 'Trasera', '4x4'")
    weight: Optional[int] = Field(description="The weight of the car in kg")
    comfort_has_leather_seats: Optional[bool] = Field(default=False, description="Whether the car has leather seats")
    comfort_has_auto_climate_control: Optional[bool] = Field(default=False, description="Whether the car has automatic climate control")
    comfort_has_interior_ambient_lighting: Optional[bool] = Field(default=False, description="Whether the car has interior ambient lighting")
    comfort_has_multimedia_system: Optional[bool] = Field(default=False, description="Whether the car has a multimedia system")
    comfort_multimedia_system_screen_size: Optional[float] = Field(description="The screen size of the multimedia system in inches")
    comfort_has_apple_carplay: Optional[bool] = Field(default=False, description="Whether the car has Apple CarPlay")
    safety_num_airbags: Optional[int] = Field(description="The number of airbags in the car")
    safety_has_abs_brakes: Optional[bool] = Field(default=False, description="Whether the car has ABS brakes")
    safety_has_lane_keeping_assist: Optional[bool] = Field(default=False, description="Whether the car has lane keeping assist")
    safety_has_forward_collision_warning: Optional[bool] = Field(default=False, description="Whether the car has Forward Collision Warning")
    safety_has_auto_emergency_brake: Optional[bool] = Field(default=False, description="Whether the car has an automatic emergency brake system")
    safety_has_auto_high_beams: Optional[bool] = Field(default=False, description="Whether the car has automatic high beams")
    safety_has_auto_drowsiness_detection: Optional[bool] = Field(default=False, description="Whether the car has automatic driver drowsiness detection")
    safety_has_blind_spot_monitor: Optional[bool] = Field(default=False, description="Whether the car has a blind spot monitoring system")
    safety_ncap_rating: Optional[int] = Field(description="The Latin NCAP safety rating of the car")
    features_has_front_camera: Optional[bool] = Field(default=False, description="Whether the car has a front camera")
    features_has_rear_camera: Optional[bool] = Field(default=False, description="Whether the car has a rear camera")
    features_has_360_camera: Optional[bool] = Field(default=False, description="Whether the car has a 360-degree camera or more")
    features_has_front_parking_sensors: Optional[bool] = Field(default=False, description="Whether the car has front parking sensors")
    features_has_rear_parking_sensors: Optional[bool] = Field(default=False, description="Whether the car has rear parking sensors")
    features_has_parking_assist: Optional[bool] = Field(default=False, description="Whether the car has an automatic parking assist system")
    features_has_digital_instrument_cluster: Optional[bool] = Field(default=False, description="Whether the car has a digital instrument cluster")
    features_has_cruise_control: Optional[bool] = Field(default=False, description="Whether the car has cruise control")
    features_has_adaptive_cruise_control: Optional[bool] = Field(default=False, description="Whether the car has adaptive cruise control")
    features_has_tpms: Optional[bool] = Field(default=False, description="Whether the car has a tire pressure monitoring system")
    features_has_led_headlights: Optional[bool] = Field(default=False, description="Whether the car has LED headlights")
    features_has_engine_ignition_button: Optional[bool] = Field(default=False, description="Whether the car has an engine ignition button")
    features_has_keyless_entry: Optional[bool] = Field(default=False, description="Whether the car has keyless entry")
    features_has_sunroof: Optional[bool] = Field(default=False, description="Whether the car has a sunroof")
    features_num_speakers: Optional[int] = Field(description="The number of speakers in the car, including subwoofer if present")
    warranty_years: Optional[int] = Field(description="Warranty in number of years")
    warranty_kms: Optional[int] = Field(description="Warranty in number of kms")

class Cars(BaseModel):
    """Identifying information about all cars in a text."""
    cars: List[Car]
    
DEFAULT_COMPANY = "openai"
DEFAULT_MODEL = "gpt-3.5-turbo"

class LLM:
    def __init__(self, model: str, company: str, temperature: str = "0", llm = None):
        self.model = model
        self.company = company
        self.temperature = temperature
        self.llm = llm

class LaunchProcessor:
    def __init__(self, max_workers=1):
        self.db = DBHelper()
        self.parser = PydanticOutputParser(pydantic_object=Cars)
        self.llms = []
        self.max_workers = max_workers
        self.lock = threading.Lock()
        self.llm_usage = LLMUsage(node_title="LaunchProcessor")

    def get_llm(self, company_name: str = DEFAULT_COMPANY, model_name: str = DEFAULT_MODEL, temperature: str = "0", max_retries=2) -> BaseLanguageModel:
        for llm in self.llms:
            if llm.company == company_name and llm.model == model_name:
                return llm.llm
        
        if (company_name == "openai"):
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=model_name, temperature=temperature, max_retries=max_retries)
        elif company_name == "groq":
            from langchain_groq import ChatGroq
            llm = ChatGroq(model=model_name, temperature=temperature, max_retries=max_retries)
        elif company_name == "anthropic":
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(model=model_name, temperature=temperature, max_retries=max_retries)
        else:
            raise ValueError(f"LLM provider {company_name} not supported")
        
        self.llms.append(LLM(model=model_name, company=company_name, temperature=temperature, llm=llm))
        return llm

    def process(self, company_name: str = DEFAULT_COMPANY, model_name: str = DEFAULT_MODEL, num_launches: int = 0) -> ProcessorResult:
        result = ProcessorResult(action="process", entity="launches")
        llm = self.get_llm(company_name, model_name)
        launches = self._get_unprocessed_launches(num_launches)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._process_launch, launch, llm, company_name, model_name) for launch in launches]
            for future in concurrent.futures.as_completed(futures):
                try:
                    processed, usage = future.result()
                    if processed:
                        with self.lock:
                            result.items_processed += 1
                            result.llm_usage.add_usage(usage)
                except Exception as e:
                    logger.error(f"Error processing launch: {str(e)}")
        
        return result

    def _process_launch(self, launch: Dict[str, Any], llm: BaseLanguageModel, company_name: str, model_name: str) -> Tuple[bool, LLMUsage]:
        usage = LLMUsage(action="extract_launch_attributes", model_name=model_name)
        start_time = time.time()
        
        try:
            logger.info(f"Processing launch {launch['id']} - {launch['title']}...")
            if company_name == "openai":
                with get_openai_callback() as cb:
                    car_attributes = self._extract_car_attributes(launch['content'], llm)
                usage.token_input = cb.prompt_tokens
                usage.token_output = cb.completion_tokens
                usage.cost = cb.total_cost
            else:
                car_attributes = self._extract_car_attributes(launch['content'], llm)
                # Estimate token usage and cost for non-OpenAI models
                usage.token_input, usage.token_output = self._estimate_token_usage(launch['content'], car_attributes)
                usage.cost = self._estimate_cost(company_name, model_name, usage.token_input, usage.token_output)
            
            if car_attributes.cars:
                for car in car_attributes.cars:
                    self._save_car_attributes(launch['id'], car.dict())
            self._mark_launch_as_processed(launch['id'])
            logger.info(f"Launch processed: {launch['id']}")
            
            usage.time = time.time() - start_time
            return True, usage
        except Exception as e:
            logger.error(f"Error processing launch {launch['id']}: {str(e)}")
            usage.time = time.time() - start_time
            return False, usage

    def test_process(self, launch_ids: List[int], model_name: str, company_name: str) -> Dict[int, Dict[str, Any]]:
        logger.info(f"\nModel {company_name} - {model_name} with launches {launch_ids}\n====================")
        llm = self.get_llm(company_name, model_name)
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._test_process_launch, launch_id, llm): launch_id for launch_id in launch_ids}
            for future in concurrent.futures.as_completed(futures):
                launch_id = futures[future]
                try:
                    results[launch_id] = future.result()
                except Exception as e:
                    logger.error(f"Error processing launch {launch_id}: {str(e)}")
                    results[launch_id] = {"error": str(e)}
        
        return results

    def _test_process_launch(self, launch_id: int, llm: BaseLanguageModel) -> Dict[str, Any]:
        launch = self._get_launch_by_id(launch_id)
        if launch:
            logger.info(f"Processing launch {launch_id}...")
            car_attributes = self._extract_car_attributes(launch['content'], llm)
            return car_attributes.dict()
        else:
            return {"error": "Launch not found"}

    def _get_unprocessed_launches(self, limit: int = 0) -> List[Dict[str, Any]]:
        query = """
            SELECT id, title, content
            FROM launches
            WHERE date_processed IS NULL
            ORDER BY id ASC
        """
        if limit > 0:
            query += f" LIMIT {limit}"
        
        return self.db.execute_query(query)

    def _get_launch_by_id(self, launch_id: int) -> Dict[str, Any]:
        launches = self.db.execute_query("""
            SELECT id, title, content
            FROM launches
            WHERE id = %s
        """, (launch_id,))
        return launches[0] if launches else None

    def _extract_car_attributes(self, content: str, llm: BaseLanguageModel) -> Dict[str, Any]:
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", """Extract information about all car variants mentioned in the given text. For each variant, provide a list of attributes as specified below. If an attribute is not mentioned for a specific variant, you can omit it. If any information that should be an integer is provided as a decimal, round to the nearest integer. The information should be retrieved in Spanish. 
                 
                 Format instructions:{format_instructions}"""),
                ("human", "{content}")
            ]
        )
        
        chain = prompt_template | llm | self.parser
        output = chain.invoke({"content":content, "format_instructions": self.parser.get_format_instructions()})
        return output

    def _save_car_attributes(self, launch_id: int, attributes: Dict[str, Any]):
        attributes['launch_id'] = launch_id
        self.db.insert('cars', attributes)

    def _mark_launch_as_processed(self, launch_id: int):
        self.db.update('launches', {'id': launch_id}, {'date_processed': 'NOW()'})

    def _estimate_token_usage(self, input_text: str, output: Cars) -> Tuple[int, int]:
        # Implement token estimation logic here for non-OpenAI models
        # This is a placeholder implementation
        input_tokens = len(input_text.split())
        output_tokens = sum(len(str(car).split()) for car in output.cars)
        return input_tokens, output_tokens

    def _estimate_cost(self, company_name: str, model_name: str, token_input: int, token_output: int) -> float:
        # Implement cost estimation logic here for non-OpenAI models
        # This is a placeholder implementation
        if company_name == "groq":
            # Add Groq pricing logic
            pass
        elif company_name == "anthropic":
            # Add Anthropic pricing logic
            pass
        # Add more pricing logic for other models/companies
        return 0.0