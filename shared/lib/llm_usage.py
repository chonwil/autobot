from dataclasses import dataclass, field
from typing import List, Set, Tuple, Optional

@dataclass
class LLMUsage:
    node_title: str = ""
    action: str = ""
    model_name: str = ""
    token_input: int = 0
    token_output: int = 0
    cost: float = 0.0
    time: float = 0.0
    usage: List['LLMUsage'] = field(default_factory=list)

    def add_usage(self, usage: 'LLMUsage') -> None:
        self.usage.append(usage)

    def summarize(self, model_name: Optional[str] = None, action: Optional[str] = None) -> Tuple[int, int, float, float, int]:
        if not self.usage:
            if (not model_name or model_name == self.model_name) and (not action or action == self.action):
                return (self.token_input, self.token_output, self.cost, self.time, 1)
            return (0, 0, 0.0, 0.0, 0)
        
        total_input, total_output, total_cost, total_time, total_calls = (0, 0, 0.0, 0.0, 0)
        for u in self.usage:
            input, output, cost, time, calls = u.summarize(model_name, action)
            total_input += input
            total_output += output
            total_cost += cost
            total_time += time
            total_calls += calls
        return (total_input, total_output, total_cost, total_time, total_calls)

    def get_summary(self, model_name: Optional[str] = None, action: Optional[str] = None, print_model: bool = True, print_action: bool = True) -> str:
        token_input, token_output, cost, time, count_calls = self.summarize(model_name, action)
        model_str = f"Model: {model_name}, " if model_name and print_model else ""
        action_str = f"Action: {action}, " if action and print_action else ""
        return f"{model_str}{action_str}Token input: {token_input}, Token output: {token_output}, Cost: ${cost:.3f}, Time: {time:.2f}s, Calls: {count_calls}"

    def get_distinct_models(self) -> Set[str]:
        if not self.usage:
            return {self.model_name}
        return set.union(*(u.get_distinct_models() for u in self.usage))

    def get_distinct_actions(self) -> Set[str]:
        if not self.usage:
            return {self.action}
        return set.union(*(u.get_distinct_actions() for u in self.usage))

    def print_summary_per_model(self) -> str:
        return "\n".join(self.get_summary(model_name=model, print_action=False) for model in self.get_distinct_models())

    def print_summary_per_action(self) -> str:
        return "\n".join(self.get_summary(action=action, print_model=False) for action in self.get_distinct_actions())

    def print_summary_per_model_action(self) -> str:
        result = [f"\nUsage of {self.node_title}\n{'=' * 40}"]
        for model in self.get_distinct_models():
            result.append(f"\nModel: {model}\n{'-' * 20}")
            for action in self.get_distinct_actions():
                result.append(self.get_summary(model_name=model, action=action, print_model=False))
            token_input, token_output, cost, time, count_calls = self.summarize(model_name=model)
            result.append(f"TOTAL: Token input: {token_input}, Token output: {token_output}, Cost: ${cost:.3f}, Time: {time:.2f}s, Calls: {count_calls}")
        return "\n".join(result)