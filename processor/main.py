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

from processor import Processor, ProcessorResult

def initiate_logs(log_level = "INFO"):
    # Configure loguru
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_name = f"{shared_dir}/logs/{current_time}_scraper.log"
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level=log_level)
    logger.add(log_file_name, rotation="10 MB", level=log_level)

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
    
    args = parser.parse_args()
    
    # Configure logging
    initiate_logs(args.log_level)

    logger.info(f"Starting processor with options: {args.options}, actions: {args.actions}")
    
    processor = Processor()
    result = processor.process(actions=args.actions, entities=args.options)
    

if __name__ == "__main__":
    main()