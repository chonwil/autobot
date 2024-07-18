import argparse
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
    log_file_name = f"{shared_dir}/logs/{current_time}_processor.log"
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level=log_level)
    logger.add(log_file_name, rotation="10 MB", level=log_level)
    
def initialize_db():
    # Clear the content of all the database tables, EXCEPT for the Scraper tables
    from shared.utils import DBHelper
    db = DBHelper()
    db.execute_query("""TRUNCATE
                        car_articles, 
                        similar_cars, 
                        similar_launches, 
                        article_sections, 
                        articles, 
                        unclassified_car_sales, 
                        similar_launches, 
                        cars,
                        launches,
                        car_sales,
                        car_models,
                        car_prices,
                        sales_reports
                        RESTART IDENTITY""")
    db.execute_query("UPDATE posts SET date_parsed = NULL")
    logger.info("Database tables cleared.")

def main():
    parser = argparse.ArgumentParser(description="Data processor for posts scraped from https://www.autoblog.com.uy")
    parser.add_argument(
        "-o", "--options",
        nargs="+",
        choices=["prices", "sales", "launches", "articles"],
        default=["prices", "sales", "launches", "articles"],
        help="Specify which types of posts to process"
    )
    parser.add_argument(
        "-a", "--actions",
        nargs="+",
        choices=["parse", "process", "connect", "upload"],
        default=["parse", "process", "connect", "upload"],
        help="Specify which actions to perform"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level"
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize the database by clearing all tables"
    )
    parser.add_argument(
        "-n", "--num-items",
        type=int,
        default=0,
        help="Number of items to process (0 for all available)"
    )
    parser.add_argument(
        "-s", "--special",
        required=False,
        type=str,
        default=None,
        help="Execute a specific function"
    )
    
    
    args = parser.parse_args()
    
    # Configure logging
    initiate_logs(args.log_level)

    logger.info(f"Starting processor with options: {args.options}, actions: {args.actions}")
    
    if args.init_db:
        confirm = input("Are you sure you want to initialize the database? This will clear all the tables and reset the posts dates. It will NOT clear any scraped pages. Type 'yes' to confirm: ")
        if confirm.lower() == "yes":
            initialize_db()
        else:
            logger.info("Database initialization canceled by the user.")
        return

    from processor import Processor
    from lib.processor_result import ProcessorResult
    
    processor = Processor()
    if (args.special is not None):
        result = processor.special(args.special)
    else:
        result = processor.process(actions=args.actions, entities=args.options, num_items=args.num_items)

    
    logger.success("Processor finished. {} items processed.", result.items_processed)
    

if __name__ == "__main__":
    main()