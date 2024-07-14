from shared.lib.llm_usage import LLMUsage
from dataclasses import dataclass, field

@dataclass
class ProcessorResult:
    action: str = ""
    entity: str = ""
    items_processed: int = 0
    llm_usage: LLMUsage = field(default_factory=LLMUsage)
    
    def append_result(self, result: 'ProcessorResult') -> None:
        self.items_processed += result.items_processed
        self.llm_usage.add_usage(result.llm_usage)