import argparse
from loguru import logger
from datetime import datetime
import sys
import os

# Add the shared directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
shared_dir = os.path.join(parent_dir, "shared")
sys.path.append(shared_dir)

from scraper import Scraper, download_page_images

def initiate_logs(log_level = "INFO"):
    # Configure loguru
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_name = f"{shared_dir}/logs/{current_time}_scraper.log"
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level=log_level)
    logger.add(log_file_name, rotation="10 MB", level=log_level)

def main():
    parser = argparse.ArgumentParser(description="Web scraper for https://www.autoblog.com.uy")
    parser.add_argument(
        "-o", "--options",
        nargs="+",
        choices=["prices", "sales", "launches", "contacts", "trials"],
        default=["prices", "sales", "launches", "contacts", "trials"],
        help="Specify which types of pages to scrape"
    )
    parser.add_argument(
        "-n", "--numpages",
        type=int,
        default=0,
        help="Number of pages to scrape (0 for all available up to the max date)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level"
    )
    parser.add_argument(
        "--download-images",
        action="store_true",
        help="Download images after scraping"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    initiate_logs(args.log_level)

    logger.info(f"Starting scraper with options: {args.options}, numpages: {args.numpages}")
    
    scraper = Scraper()
    pages_scraped = scraper.scrape(scrape_options=args.options, numpages=args.numpages)
    
    logger.info(f"Scraping complete. Total pages scraped: {pages_scraped}")

    if args.download_images:
        logger.info("Downloading images...")
        download_page_images()
        logger.info("Image download complete")

if __name__ == "__main__":
    main()