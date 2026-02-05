import tiktoken
from src.utils.pricing_data import PRICING_REGISTRY

def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """
    Counts tokens for a given text. 
    Uses tiktoken for OpenAI models. 
    For others, falls back to a rough character approximation (4 chars ~= 1 token) 
    or uses tiktoken as a proxy.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except KeyError:
        # Fallback for non-OpenAI models or unknown models
        # generic approximation
        return len(text) // 4

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculates cost in USD.
    """
    # Normalize model name slightly
    model_key = model.lower()
    
    # Check exact match or if it's in registry
    rates = PRICING_REGISTRY.get(model_key)
    
    if not rates:
        # Try finding a partial match if exact fails (e.g. "gpt-4o-2024..." matching "gpt-4o")
        # This is simple heuristics
        for key, val in PRICING_REGISTRY.items():
            if key in model_key:
                rates = val
                break
    
    if not rates:
        return 0.0
    
    input_cost = (input_tokens / 1_000_000) * rates["input"]
    output_cost = (output_tokens / 1_000_000) * rates["output"]
    
    return input_cost + output_cost
