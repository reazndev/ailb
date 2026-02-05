# Detailed Model Pricing & Configuration
# Last Updated: 2026-02-05

MODEL_DATA = {
    "google_gemini": {
        "gemini-3-pro": {
            "name": "Gemini 3 Pro",
            "input_price": 2.00,
            "output_price": 12.00,
            "context": "2M"
        },
        "gemini-3-flash": {
            "name": "Gemini 3 Flash",
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
        "gemini-2.5-flash-lite": {
            "name": "Gemini 2.5 Flash-Lite",
            "input_price": 0.10,
            "output_price": 0.40,
            "context": "1M"
        }
    },
    "openai": {
        "gpt-5.2-pro": {
            "name": "GPT-5.2 Pro",
            "input_price": 21.00,
            "output_price": 168.00,
            "context": "400k"
        },
        "gpt-5.2": {
            "name": "GPT-5.2",
            "input_price": 1.75,
            "output_price": 14.00,
            "context": "400k"
        },
        "gpt-5-mini": {
            "name": "GPT-5 mini",
            "input_price": 0.25,
            "output_price": 2.00,
            "context": "128k"
        },
        "o3": {
            "name": "o3 (Reasoning)",
            "input_price": 2.00,
            "output_price": 8.00,
            "context": "200k"
        }
    },
    "anthropic_claude": {
        "claude-4.5-opus": {
            "name": "Claude 4.5 Opus",
            "input_price": 5.00,
            "output_price": 25.00,
            "context": "1M"
        },
        "claude-4.5-sonnet": {
            "name": "Claude 4.5 Sonnet",
            "input_price": 3.00,
            "output_price": 15.00,
            "context": "1M"
        },
        "claude-4.5-haiku": {
            "name": "Claude 4.5 Haiku",
            "input_price": 1.00,
            "output_price": 5.00,
            "context": "1M"
        }
    },
    "openrouter": {
        "deepseek-v3.2": {
            "name": "DeepSeek V3.2",
            "input_price": 0.25,
            "output_price": 0.38,
            "context": "128k"
        },
        "mistral-devstral-2": {
            "name": "Devstral 2 (Mistral)",
            "input_price": 0.05,
            "output_price": 0.22,
            "context": "256k"
        },
        "minimax-m2.1": {
            "name": "MiniMax M2.1",
            "input_price": 0.28,
            "output_price": 1.20,
            "context": "196k"
        },
        "xiaomi-mimo-v2": {
            "name": "MiMo-V2 (Xiaomi)",
            "input_price": 0.00,
            "output_price": 0.00,
            "context": "512k"
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
