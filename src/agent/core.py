import os
import time
import threading
import concurrent.futures
from typing import List, Dict, Callable, Optional
from src.llm.client import LLMClient
from src.agent.prompts import SYSTEM_PROMPT, PLANNER_PROMPT, WORKER_PROMPT, QA_PROMPT
from src.utils.cost import count_tokens, calculate_cost
from src.utils.docx_editor import append_solution_to_docx
from src.ingestion.loader import load_file_content
from src.utils.text_cleaner import replace_sz, clean_ai_artifacts

# Try to import Streamlit context helpers for thread safety
try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
except ImportError:
    add_script_run_ctx = None
    get_script_run_ctx = None

class Agent:
    def __init__(self, provider="openai", model="gpt-4o", cost_limit: float = 0.0, max_parallel: int = 5, skip_qa: bool = False, max_qa_retries: int = 1, min_qa_score: float = 9.0):
        self.llm = LLMClient(provider=provider, model=model)
        self.model = model
        self.max_parallel = max_parallel
        self.skip_qa = skip_qa
        self.max_qa_retries = max_qa_retries
        self.min_qa_score = min_qa_score
        self.console = None  # Legacy CLI support
        self.lock = threading.Lock() # For thread-safe stats updates
        
        # State tracking
        self.total_cost = 0.0
        self.cost_limit = cost_limit
        self.accumulated_tokens = {"input": 0, "output": 0}
        
        # Callbacks
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_update: Optional[Callable[[Dict], None]] = None # Generic state update
        self.on_section_start: Optional[Callable[[str, str, int, int], None]] = None # task_name, requirements, index, total
        self.on_draft: Optional[Callable[[str], None]] = None # draft_text
        self.on_qa_feedback: Optional[Callable[[str], None]] = None # feedback_text
        self.on_plan_generated: Optional[Callable[[List[str]], None]] = None # list of tasks

    def log(self, message: str):
        # Console output
        if self.console:
            self.console.print(f"[bold cyan]Agent:[/bold cyan] {message}")
        else:
            print(f"Agent: {message}")
            
        # GUI Callback
        if self.on_log:
            self.on_log(message)

    def _track_usage(self, prompt: str, response: str):
        in_tok = count_tokens(prompt, self.model)
        out_tok = count_tokens(response, self.model)
        
        cost = calculate_cost(self.model, in_tok, out_tok)
        
        with self.lock:
            self.accumulated_tokens["input"] += in_tok
            self.accumulated_tokens["output"] += out_tok
            self.total_cost += cost
            
            if self.on_update:
                self.on_update({
                    "total_cost": self.total_cost,
                    "tokens": self.accumulated_tokens
                })

    def _check_budget(self):
        with self.lock:
            if self.cost_limit > 0 and self.total_cost >= self.cost_limit:
                raise Exception(f"Cost limit reached! (${self.total_cost:.4f} >= ${self.cost_limit:.4f})")

    def _check_signal(self):
        if os.path.exists(".skip_signal"):
            self.log("User requested skip. Breaking current loop.")
            try:
                os.remove(".skip_signal")
            except:
                pass
            return True
        return False

    def process_assignment(self, ass_path: str, output_dir: str, full_context: str, input_overview: str, custom_prompt: str) -> str:
        ass_filename = os.path.basename(ass_path)
        self.log(f"Processing Assignment: {ass_filename}")
        
        assignment_text = load_file_content(ass_path)
        if not assignment_text:
            self.log(f"Skipping empty assignment: {ass_filename}")
            return ""
        
        self.log(f"[{ass_filename}] Loaded assignment text ({len(assignment_text)} chars).")

        # 2. Plan
        self._check_budget()
        self.log(f"[{ass_filename}] Creating a plan...")
        
        user_instructions = ""
        if custom_prompt:
            user_instructions = f"\nZUSÄTZLICHE BENUTZERANWEISUNGEN:\n{custom_prompt}\n"

        planner_input = PLANNER_PROMPT.format(
            assignment_text=assignment_text[:50000],
            input_overview=input_overview
        ) + user_instructions
        
        plan_response = self.llm.generate_text(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=planner_input
        )
        self._track_usage(SYSTEM_PROMPT + planner_input, plan_response)
        
        tasks = [line.strip() for line in plan_response.split('\n') if line.strip() and (line[0].isdigit() or line.startswith('-'))]
        
        if not tasks:
            self.log(f"[{ass_filename}] ⚠️ No specific tasks found. Defaulting.")
            tasks = ["Bearbeite die Aufgabenstellung vollständig."]
        
        if self.on_plan_generated:
            self.on_plan_generated(tasks)

        self.log(f"[{ass_filename}] Parsed {len(tasks)} tasks.")
        
        assignment_solution_parts = []

        # 3. Execute Tasks
        for i, task in enumerate(tasks):
            self._check_budget()
            self.log(f"[{ass_filename}] Task {i+1}/{len(tasks)}: {task}")
            
            if self.on_section_start:
                self.on_section_start(task, assignment_text, i, len(tasks))

            worker_input = WORKER_PROMPT.format(
                current_task=task,
                context_text=full_context,
                assignment_text=assignment_text
            ) + user_instructions
            
            draft = self.llm.generate_text(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=worker_input
            )
            self._track_usage(SYSTEM_PROMPT + worker_input, draft)
            
            if self.on_draft:
                self.on_draft(draft)
            
            # 4. QA Loop
            self._check_budget()
            
            if self.skip_qa:
                self.log(f"[{ass_filename}] Skipping QA Review.")
            else:
                self.log(f"[{ass_filename}] QA Review...")
                
                qa_attempts = 0
                while qa_attempts <= self.max_qa_retries:
                    if self._check_signal():
                        break

                    qa_input = QA_PROMPT.format(
                        assignment_text=assignment_text,
                        generated_content=draft,
                        min_score=self.min_qa_score
                    )
                    
                    review = self.llm.generate_text(
                        system_prompt=SYSTEM_PROMPT,
                        user_prompt=qa_input
                    )
                    self._track_usage(SYSTEM_PROMPT + qa_input, review)
                    
                    if self.on_qa_feedback:
                        self.on_qa_feedback(review)

                    if "PASS" in review:
                        self.log(f"[{ass_filename}] QA Passed.")
                        break
                    
                    qa_attempts += 1
                    if qa_attempts > self.max_qa_retries:
                        self.log(f"[{ass_filename}] QA failed max retries ({self.max_qa_retries}).")
                        break
                        
                    self.log(f"[{ass_filename}] QA failed (Attempt {qa_attempts}/{self.max_qa_retries}). Improving...")
                    self._check_budget()
                    
                    refinement_input = f"""
                    Der Professor hat folgendes Feedback gegeben:
                    {review}
                    
                    Bitte überarbeite den vorherigen Entwurf basierend auf diesem Feedback.
                    
                    Alter Entwurf:
                    {draft}
                    """
                    refined_draft = self.llm.generate_text(
                        system_prompt=SYSTEM_PROMPT,
                        user_prompt=refinement_input
                    )
                    self._track_usage(SYSTEM_PROMPT + refinement_input, refined_draft)
                    draft = refined_draft
                    
                    if self.on_draft:
                         self.on_draft(draft)
            
            cleaned_text = replace_sz(clean_ai_artifacts(draft))
            assignment_solution_parts.append(f"## {task}\n\n{cleaned_text}")
        
        full_solution_text = "\n\n".join(assignment_solution_parts)
        report_part = f"# Solution for {ass_filename}\n\n{full_solution_text}"
        
        if ass_path.lower().endswith(".docx"):
            out_path = os.path.join(output_dir, ass_filename)
            self.log(f"[{ass_filename}] Saving DOCX...")
            success = append_solution_to_docx(ass_path, out_path, full_solution_text)
            if not success:
                 self.log(f"[{ass_filename}] Failed to save DOCX.")
        else:
            out_path = os.path.join(output_dir, f"{ass_filename}_solution.md")
            with open(out_path, "w") as f:
                f.write(full_solution_text)
            self.log(f"[{ass_filename}] Saved MD.")

        return report_part

    def run(self, hz_name: str, assignment_paths: List[str], input_texts: Dict[str, str], custom_prompt: str = "") -> str:
        self.log(f"Starting process for {hz_name}...")
        self.log(f"Model: {self.model} | Budget Cap: ${self.cost_limit}")
        self.log(f"Selected Assignments: {len(assignment_paths)}")
        
        full_context = ""
        input_overview = ""
        for filename, text in input_texts.items():
            full_context += f"--- START FILE: {os.path.basename(filename)} ---\n{text[:20000]}...\n--- END FILE ---\n\n"
            input_overview += f"- {os.path.basename(filename)}\n"

        output_dir = os.path.join("output", hz_name)
        os.makedirs(output_dir, exist_ok=True)
        
        final_reports = []
        
        # Capture context if running in Streamlit
        ctx = get_script_run_ctx() if get_script_run_ctx else None

        def task_wrapper(*args, **kwargs):
            # Apply context to the worker thread
            if add_script_run_ctx and ctx:
                add_script_run_ctx(threading.current_thread(), ctx)
            return self.process_assignment(*args, **kwargs)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            futures = []
            for ass_path in assignment_paths:
                futures.append(
                    executor.submit(
                        task_wrapper, 
                        ass_path, 
                        output_dir, 
                        full_context, 
                        input_overview, 
                        custom_prompt
                    )
                )
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        final_reports.append(result)
                except Exception as e:
                    self.log(f"Error in assignment thread: {e}")

        return "\n\n---\n\n".join(final_reports)
