# AI Student Agent

An autonomous AI agent designed to solve Computer Science school assignments. It reads input materials (PDF, PPTX, DOCX), understands the assignment, plans a solution, executes it, and performs self-qa.

## Features
- **Multi-Format Ingestion:** Supports `.docx`, `.pdf`, `.pptx`.
- **Autonomous Agent:** Plans, Executes, and Reviews its own work.
- **Multi-Provider:** Switch between OpenAI, Anthropic (Claude), Google (Gemini), DeepSeek, and OpenRouter.
- **German Output:** Optimized for German Computer Science curriculum.

## Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment:**
   Copy `.env.example` to `.env` and add your API keys.
   ```bash
   cp .env.example .env
   # Edit .env with your keys
   ```

3. **Prepare Data:**
   Place your files in the `data` directory following this structure:
   ```
   data/
   └── HZ_Name/
       ├── Input/          # Lecture slides, books (PDF, PPTX)
       └── Assignments/    # The task to solve (DOCX, TXT)
   ```

## Usage

Run the agent from the root directory:

```bash
# Default (OpenAI / GPT-4o)
PYTHONPATH=. python3 src/main.py

# specific provider
PYTHONPATH=. python3 src/main.py --provider anthropic --model claude-3-opus
PYTHONPATH=. python3 src/main.py --provider gemini --model gemini-1.5-pro
```

The results will be saved in `output/HZ_Name/solution.md`.
