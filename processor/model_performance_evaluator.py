from loguru import logger
from datetime import datetime
import sys
import os

# Add the shared directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
shared_dir = os.path.join(parent_dir, "shared")
sys.path.append(parent_dir)


def initiate_logs(log_level = "INFO"):
    # Configure loguru
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_name = f"{shared_dir}/logs/{current_time}_model_performance_evaluator.log"
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level=log_level)
    logger.add(log_file_name, rotation="10 MB", level=log_level)

import json
import csv
from typing import Dict, Any
from pathlib import Path
from loguru import logger
from processors import LaunchProcessor, Car

class ModelPerformanceTester:
    def __init__(self):
        self.launch_processor = LaunchProcessor()
        self.models = [
            {"company": "groq", "model": "llama3-8b-8192"},
            {"company": "openai", "model": "gpt-4o"},
            {"company": "openai", "model": "gpt-3.5-turbo"},
            {"company": "anthropic", "model": "claude-3-5-sonnet-20240620"},
        ]
        self.launch_ids = [1]
        base_path = Path(Path(__file__).parent.parent, 'shared', 'data', 'evaluations', 'launch_processor')
        self.results_dir = Path(base_path, "model_test_results")
        self.correct_dir = Path(base_path, "correct_results")
        self.detailed_results_dir = Path(base_path, "detailed_results")
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure all necessary directories exist."""
        for directory in [self.results_dir, self.correct_dir, self.detailed_results_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def run_tests(self):
        """Run tests for all models and launch IDs."""
        for model in self.models:
            results = self._process_launches(model)
            self._save_results(model, results)

    def _process_launches(self, model: Dict[str, str]) -> Dict[int, Dict[str, Any]]:
        """Process launches for a given model."""
        results = {}
        for launch_id in self.launch_ids:
            try:
                result = self.launch_processor.test_process([launch_id], model["model"], model["company"])
                results[launch_id] = result[launch_id]
            except Exception as e:
                logger.error(f"Error processing launch {launch_id} for {model['company']}_{model['model']}: {str(e)}")
                results[launch_id] = {"error": str(e)}
        return results

    def _save_results(self, model: Dict[str, str], results: Dict[int, Dict[str, Any]]):
        """Save results to a JSON file."""
        filename = self.results_dir / f"{model['company']}_{model['model']}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {filename}")

    def compare_results(self):
        """Compare results from all models with the correct data."""
        model_scores = {f"{model['company']}_{model['model']}": self._calculate_scores(model) 
                        for model in self.models}
        self._display_scores(model_scores)

    def _calculate_scores(self, model: Dict[str, str]) -> Dict[str, Any]:
        """Calculate scores for a model's results."""
        results = self._load_results(model)
        overall_score = 0
        variant_scores = {}
        attribute_scores = {attr: {"correct": 0, "total": 0} for attr in Car.__fields__}

        for launch_id, launch_results in results.items():
            correct_data = self._load_correct_data(launch_id)
            variant_scores[launch_id] = self._calculate_variant_score(launch_results, correct_data)
            overall_score += self._calculate_attribute_scores(launch_results, correct_data, attribute_scores)

        total_attributes = sum(score["total"] for score in attribute_scores.values())
        overall_score = (overall_score / total_attributes) * 100 if total_attributes > 0 else 0

        attribute_accuracy = {
            attr: (scores["correct"] / scores["total"]) * 100 if scores["total"] > 0 else 0
            for attr, scores in attribute_scores.items()
        }

        return {
            "overall_score": overall_score,
            "variant_scores": variant_scores,
            "attribute_accuracy": attribute_accuracy
        }

    def _calculate_variant_score(self, launch_results: Dict[str, Any], correct_data: Dict[str, Dict[str, str]]) -> str:
        """Calculate the variant score for a launch."""
        detected_variants = len(launch_results.get('cars', []))
        expected_variants = len(correct_data)
        return f"{detected_variants}/{expected_variants}"

    def _calculate_attribute_scores(self, launch_results: Dict[str, Any], correct_data: Dict[str, Dict[str, str]], 
                                    attribute_scores: Dict[str, Dict[str, int]]) -> int:
        """Calculate attribute scores for a launch."""
        score = 0
        for car in launch_results.get('cars', []):
            matching_variant = next((v for v in correct_data.values() if v['launch_price'] == str(car['launch_price'])), None)
            if matching_variant:
                for attr, value in car.items():
                    if attr in matching_variant:
                        attribute_scores[attr]["total"] += 1
                        if self._values_match(value, matching_variant[attr]):
                            attribute_scores[attr]["correct"] += 1
                            score += 1
        return score

    @staticmethod
    def _values_match(value: Any, correct_value: str) -> bool:
        """Check if the extracted value matches the correct value."""
        return (correct_value.strip() == '' and (value == '' or value is None or value is False or value == 0)) or str(value).lower().strip() == correct_value.lower().strip()

    def _load_results(self, model: Dict[str, str]) -> Dict[int, Dict[str, Any]]:
        """Load results from a JSON file."""
        filename = self.results_dir / f"{model['company']}_{model['model']}.json"
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Results file not found: {filename}")
            return {}

    def _load_correct_data(self, launch_id: int) -> Dict[str, Dict[str, str]]:
        """Load correct data from a CSV file."""
        filename = self.correct_dir / f"{launch_id}.csv"
        correct_data = {}
        try:
            with open(filename, 'r') as f:
                reader = csv.reader(f, delimiter=';')
                headers = next(reader)
                for row in reader:
                    attribute = row[0]
                    for i, value in enumerate(row[1:], 1):
                        if headers[i] not in correct_data:
                            correct_data[headers[i]] = {}
                        correct_data[headers[i]][attribute] = value
            return correct_data
        except FileNotFoundError:
            logger.error(f"Correct data file not found: {filename}")
            return {}

    def _display_scores(self, model_scores: Dict[str, Dict[str, Any]]):
        """Display scores for all models."""
        for model, scores in model_scores.items():
            print(f"\nScores for {model}:\n=======================")
            print(f"Overall score: {scores['overall_score']:.2f}%")
            print("Variants detected/expected:")
            for launch_id, score in scores['variant_scores'].items():
                print(f"  Launch {launch_id}: {score}")
            print("Attribute accuracy:")
            for attr, accuracy in scores['attribute_accuracy'].items():
                print(f"  {attr}: {accuracy:.2f}%")

    def generate_detailed_results(self):
        """Generate detailed CSV results for each launch."""
        for launch_id in self.launch_ids:
            correct_data = self._load_correct_data(launch_id)
            model_results = {f"{model['company']}_{model['model']}": self._load_results(model).get(str(launch_id), {})
                             for model in self.models}
            
            filename = self.detailed_results_dir / f"results_{launch_id}.csv"
            self._write_detailed_results(filename, correct_data, model_results)
            logger.info(f"Detailed results for launch {launch_id} saved to {filename}")

    def _write_detailed_results(self, filename: Path, correct_data: Dict[str, Dict[str, str]], 
                                model_results: Dict[str, Dict[str, Any]]):
        """Write detailed results to a CSV file."""
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Attribute', 'Correct'] + list(model_results.keys()))
            
            for variant_index, (variant_name, correct_variant) in enumerate(correct_data.items()):
                if variant_index > 0:
                    writer.writerow([])  # Add a blank row between variants
                writer.writerow([f"Variant {variant_index + 1}", variant_name])
                
                for attr in Car.__fields__:
                    row = [attr, correct_variant.get(attr, '')]
                    for model_name, model_result in model_results.items():
                        model_variant = next((car for car in model_result.get('cars', [])
                                              if str(car.get('launch_price')) == correct_variant.get('launch_price')),
                                             {})
                        row.append(model_variant.get(attr, ''))
                    writer.writerow(row)

if __name__ == "__main__":
    tester = ModelPerformanceTester()
    # Uncomment the following line to run the tests
    tester.run_tests()
    tester.compare_results()
    tester.generate_detailed_results()