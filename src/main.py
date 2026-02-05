import os
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from src.ingestion.scanner import scan_directory
from src.ingestion.loader import load_file_content
from src.agent.core import Agent
from pathlib import Path

app = typer.Typer()
console = Console()

@app.command()
def start(
    data_dir: str = "data",
    provider: str = typer.Option("openai", help="LLM Provider: openai, anthropic, gemini, deepseek, openrouter"),
    model: str = typer.Option("gpt-4o", help="Model name (e.g. gpt-4o, claude-3-opus, gemini-pro)")
):
    """
    Starts the Autonomous AI Student Agent.
    """
    console.print(f"[bold green]Starting AI Student Agent using {provider} ({model})...[/bold green]")
    
    # 1. Scan
    hz_list = scan_directory(data_dir)
    if not hz_list:
        console.print("[red]No Handlungsziele (HZ) found in data directory.[/red]")
        return

    agent = Agent(provider=provider, model=model)
    agent.console = console

    for hz in hz_list:
        console.rule(f"[bold blue]Processing: {hz.name}[/bold blue]")
        
        # Load Inputs
        input_texts = {}
        for file_path in hz.input_files:
            console.print(f"Reading Input: {os.path.basename(file_path)}")
            content = load_file_content(file_path)
            if content:
                input_texts[file_path] = content

        # Load Assignments
        assignment_text = ""
        for file_path in hz.assignment_files:
            console.print(f"Reading Assignment: {os.path.basename(file_path)}")
            content = load_file_content(file_path)
            if content:
                assignment_text += f"\n\n--- ASSIGNMENT FILE: {os.path.basename(file_path)} ---\n{content}"

        if not assignment_text:
            console.print(f"[yellow]No assignment text found for {hz.name}. Skipping.[/yellow]")
            continue

        # Run Agent
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(description=f"Agent working on {hz.name}...", total=None)
            
            # We run the agent synchronously for now, but wrapped in logic
            # The agent has its own logs which might conflict with spinner if not careful,
            # so we assigned console to agent to print nicely.
            
            result = agent.run(hz.name, assignment_text, input_texts)

        # Save Output
        output_dir = os.path.join("output", hz.name)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "solution.md")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)
            
        console.print(f"[bold green]Finished {hz.name}. Saved to {output_file}[/bold green]")

if __name__ == "__main__":
    app()
