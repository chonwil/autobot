from shared.lib.llm_usage import LLMUsage

from parsers import PriceParser
from lib.processor_result import ProcessorResult
    

class Processor:
    
    def _parse(self, entities):
        results = ProcessorResult(action="parse", entity="")
        
        if "prices" in entities:
            parser = PriceParser()
            results.append_result(parser.parse())
            
        return results
            

    def _process(self, entities):
        pass
    
    def _connect(self, entities):
        pass
    
    def _upload(self, entities):
        pass

    def process(self, actions, entities) -> ProcessorResult:
        result = ProcessorResult(llm_usage=LLMUsage(node_title="Processor"))
        if "parse" in actions:
            result.append_result(self._parse(entities))
            
        if "process" in actions:
            result.append_result(self._parse(entities))
            
        if "connect" in actions:
            result.append_result(self._parse(entities))
            
        if "upload" in actions:
            result.append_result(self._parse(entities))

