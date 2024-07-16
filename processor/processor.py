from shared.lib.llm_usage import LLMUsage
from lib.processor_result import ProcessorResult
from loguru import logger
    
class Processor:
    
    def _parse(self, entities):
        from parsers import PriceParser, PostsParser, SalesParser
        results = ProcessorResult(action="parse", entity="")
        
        if "prices" in entities:
            parser = PriceParser()
            results.append_result(parser.parse())
            
        if "articles" in entities:
            parser = PostsParser()
            results.append_result(parser.parse(entities="articles"))
            
        if "launches" in entities:
            parser = PostsParser()
            results.append_result(parser.parse(entities="launches"))
            
        if "sales" in entities:
            parser = SalesParser()
            results.append_result(parser.parse())
            
        return results
            

    def _process(self, entities, num_items: int = 0):
        results = ProcessorResult(action="process", entity="")
        
        if "sales" in entities:
            from processors import SalesProcessor
            processor = SalesProcessor()
            results.append_result(processor.process())
        
        if "launches" in entities:
            from processors import LaunchProcessor
            processor = LaunchProcessor()
            processor_result = processor.process(num_launches=num_items)
            logger.info(processor_result.llm_usage.print_summary_per_model())
            results.append_result(processor_result)
        
        if "articles" in entities:
            from processors import ArticlesProcessor
            processor = ArticlesProcessor()
            processor_result = processor.process(num_articles=num_items)
            logger.info(processor_result.llm_usage.print_summary_per_model_action())
            results.append_result(processor_result)
        return results
        
    
    def _connect(self, entities):
        pass
    
    def _upload(self, entities):
        pass

    def process(self, actions, entities, num_items: int = 0) -> ProcessorResult:
        result = ProcessorResult(llm_usage=LLMUsage(node_title="Processor"))
        if "parse" in actions:
            result.append_result(self._parse(entities))
            
        if "process" in actions:
            result.append_result(self._process(entities, num_items))
            
        if "connect" in actions:
            result.append_result(self._connect(entities))
            
        if "upload" in actions:
            result.append_result(self._upload(entities))
            
        return result
