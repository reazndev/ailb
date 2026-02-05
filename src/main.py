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
        # We don't need to read them all into one string anymore, just pass paths
        if not hz.assignment_files:
            console.print(f"[yellow]No assignment files found for {hz.name}. Skipping.[/yellow]")
            continue
            
        for f in hz.assignment_files:
             console.print(f"Found Assignment: {os.path.basename(f)}")

        # Run Agent
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(description=f"Agent working on {hz.name}...", total=None)
            
            # Run with list of paths
            result = agent.run(
                hz_name=hz.name, 
                assignment_paths=hz.assignment_files, 
                input_texts=input_texts,
                custom_prompt=""
            )

        # Save Output (Summary Report)
        output_dir = os.path.join("output", hz.name)
        # Note: Individual DOCX files are already saved by agent.run
        # We also save the summary markdown
        output_file = os.path.join(output_dir, "summary_report.md")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)
            
        console.print(f"[bold green]Finished {hz.name}. Summary saved to {output_file}[/bold green]")

if __name__ == "__main__":
    app()
