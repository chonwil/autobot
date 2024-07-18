# 🚗🤖 Autobot: An automotive RAG application 

Autobot is a RAG (Retrieval Augmented Generation) appliaction used to obtain insights about cars and the Uruguayan car market. I built autobot as a personal learning project, as it can be used to test multiple approaches to data processing, extraction and interaction using generative AI techniques.

Autobot has data processing pipeline designed to scrape, parse, analyze, and structure automotive data from https://www.autoblog.com.uy. It utilizes advanced natural language processing techniques and machine learning models to structure data and extract meaningful insights from automotive articles, sales reports, and vehicle specifications.

Once the data has been analyzed and structured, the chatbot application can be used to interact with the data.

### Requirements

An OpenAI account and API KEY is required to run the project, along with an account in Pinecone, an index and an API key. Note that as of July 2024, using the OpenAI models to extract, structure and upload the necessary data may cost between $5 - $10 approximately for a full run.


## Features

- Web scraping of automotive articles, sales reports, and price listings
- Parsing and structuring of scraped data
- Natural language processing of articles and comments
- Sentiment analysis and summarization of article content
- Extraction of detailed vehicle specifications
- Matching and linking of related automotive data
- Database storage and management of processed information, in both relational and vector stores
- Integration with various AI models for advanced analysis, including OpenAI, Anthropic and Llama3 (via Groq). Currently only OpenAI is required for processing.

## Project Structure

The project is organized into several key components:

- `scraper/`: Web scraping modules
- `processor/`: Processes scraped data into a structured representation
- `processor/processors/`: Data processing and analysis modules
- `processor/connectors/`: Modules for linking and matching related data
- `processor/parsers/`: Modules for parsing specific types of content
- `processor/uploaders/`: Modules for uploading processed data
- `chatbot/`: Modules for different chatbot implementations
- `chatbot/ui`: Application frontend libraries
- `chatbot/models`: Interaction models library
- `shared/`: Shared utilities and libraries

## Installation

1. Clone the repository:

```
git clone https://github.com/chonwil/autobot.git
cd autobot
```

2. Install the required dependencies:

```
pip install -r requirements.txt
```

3. Set up the database:
- Install PostgreSQL
- Create a new database for the project
- Update the database configuration in the `.env` file

4. Set up environment variables:
- Copy the `.env.example` file to `.env`
- Fill in the required API keys and configuration values

## Usage

### Scraping Data

To scrape new data:

```
python main_scraper.py
```

Options:
- `-o`: Specify which types of pages to scrape (prices, sales, launches, contacts or trials)
- `-n`: Number of pages to scrape (0 for all available)
- `--log-level`: Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--download-images`: Download images after scraping

### Processing Data

To process the scraped data:

```
python main_processor.py
```

Options:
- `-o`: Specify which types of data to process (prices, sales, launches, articles)
- `-a`: Specify which actions to perform (parse, process, connect, upload)
- `-n`: Number of items to process (0 for all available)
- `--log-level`: Set the logging level
- `--init-db`: Initialize the database by clearing all tables (use with caution)

## License

This project is licensed under the MIT License. See the [License.txt](License.txt) file for details.