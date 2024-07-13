# Autobot - A RAG appliaction for cars in the Uruguayan market
---
This RAG application is a personal learning project that aims to answer questions about cars in the Uruguayan market based on data collected from https://www.autoblog.com.uy.

This Blog contains a wealth of information about cars, including:
- Car launches (containing car characteristics and main features)
- Car contacts & trials, which include thorough tests the site author has conducted
- Price lists, showing current market prices for new cars
- Monthly sales volume reports

The RAG application should be able to do the following:
- Answer questions about a specific car model, such as asking about a specific feature, E.g. "How many airbags does the Nissan Kicks Exclusive have?"
- Compare one car model with another. E.g. "What are the differences between the Changan CS35 Plus and the Nissan Kicks Exclusive?"
- Ask an opinion about a specific car model, E.g. "What are the best features of the Nissan Kicks", or "Is the nissan kicks easy to drive?"
- Ask car purchase recommendations (i.e. as if the user is speaking to a salesperson). E.g. "I am looking an SUV under 40.000 USD with good safety features, can you give me any suggestions?"
- Ask general car-related questions, e.g. "What is adaptive cruise control?"
The application should also be able to have a normal conversation if the conversation goes off topic, E.g. "Hi! What is your name?"

## Structure
The application will contain the following directories:
1. *scraper*, a web scraper capable of scraping content from the website and storing it in a local database
2. *processor*, a data processor capable of extracting data from the scraped website and storing it in processed and structured representations, such as tables of features, vectors or graphs. This processor may use LLMs itself for data extraction.
3. *chatbot*, a web-based chatbot interface, which should support using more than one strategy (for learning purposes)
4. *shared*, a directory containing resources such as DB utilities, data stores, logs etc.

## External applications & services
The application will use external applications and services in order to accomplish its objectives wherever possible. It should also be built in such a way that it can be hosted in a web environment.

