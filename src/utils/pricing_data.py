# Detailed Model Pricing & Configuration
# Last Updated: 2026-02-05
# NOTE: Keys are mapped to AVAILABLE API Model IDs from your environment.

MODEL_DATA = {
    "google_gemini": {
        "gemini-3-pro-preview": {
            "name": "Gemini 3 Pro (Preview)",
            "input_price": 2.00,
            "output_price": 12.00,
            "context": "2M"
        },
        "gemini-3-flash-preview": {
            "name": "Gemini 3 Flash (Preview)",
            "input_price": 0.50,
            "output_price": 3.00,
            "context": "1M"
        },
        "gemini-2.5-pro": {
            "name": "Gemini 2.5 Pro",
            "input_price": 1.25,
            "output_price": 10.00,
            "context": "2M"
        },
        "gemini-2.5-flash": {
            "name": "Gemini 2.5 Flash",
            "input_price": 0.10,
            "output_price": 0.40,
            "context": "1M"
        },
         "gemini-2.0-flash": {
            "name": "Gemini 2.0 Flash",
            "input_price": 0.10,
            "output_price": 0.40,
            "context": "1M"
        }
    },
    "openai": {
        "gpt-4o": {
            "name": "GPT-4o (Styled as 5.2)",
            "input_price": 2.50,
            "output_price": 10.00,
            "context": "128k"
        },
        "gpt-4o-mini": {
            "name": "GPT-4o Mini",
            "input_price": 0.15,
            "output_price": 0.60,
            "context": "128k"
        },
        "o1-mini": {
            "name": "o1-mini (Reasoning)",
            "input_price": 3.00,
            "output_price": 12.00,
            "context": "128k"
        }
    },
    "anthropic_claude": {
        "claude-3-opus-20240229": {
            "name": "Claude 3 Opus",
            "input_price": 15.00,
            "output_price": 75.00,
            "context": "200k"
        },
        "claude-3-5-sonnet-20240620": {
            "name": "Claude 3.5 Sonnet",
            "input_price": 3.00,
            "output_price": 15.00,
            "context": "200k"
        },
        "claude-3-haiku-20240307": {
            "name": "Claude 3 Haiku",
            "input_price": 0.25,
            "output_price": 1.25,
            "context": "200k"
        }
    },
    "openrouter": {
        "deepseek/deepseek-chat": {
            "name": "DeepSeek V3",
            "input_price": 0.14,
            "output_price": 0.28,
            "context": "64k"
        },
        "mistralai/mistral-large-2407": {
            "name": "Mistral Large 2",
            "input_price": 3.00,
            "output_price": 9.00,
            "context": "128k"
        }
    },
    "deepseek": {
         "deepseek-reasoner": {
            "name": "DeepSeek Reasoner",
            "input_price": 0.55,
            "output_price": 2.19,
            "context": "64k"
        },
        "deepseek-chat": {
            "name": "DeepSeek Chat",
            "input_price": 0.14,
            "output_price": 0.28,
            "context": "64k"
        }
    }
}

# Flatten for easy lookup by ID
PRICING_REGISTRY = {}
for provider, models in MODEL_DATA.items():
    for model_id, data in models.items():
        PRICING_REGISTRY[model_id] = {
            "input": data["input_price"],
            "output": data["output_price"]
        }
