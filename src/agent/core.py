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

class Agent:
    def __init__(self, provider="openai", model="gpt-4o", cost_limit: float = 0.0, max_parallel: int = 5, skip_qa: bool = False, max_qa_retries: int = 1):
        self.llm = LLMClient(provider=provider, model=model)
        self.model = model
        self.max_parallel = max_parallel
        self.skip_qa = skip_qa
        self.max_qa_retries = max_qa_retries
        self.console = None  # Legacy CLI support
        self.lock = threading.Lock() # For thread-safe stats updates
...            # 4. QA Loop
            self._check_budget()
            
            if self.skip_qa:
                self.log(f"[{ass_filename}] Skipping QA Review.")
            else:
                self.log(f"[{ass_filename}] QA Review...")
                
                qa_attempts = 0
                while qa_attempts <= self.max_qa_retries:
                    qa_input = QA_PROMPT.format(
                        assignment_text=assignment_text,
                        generated_content=draft
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
                    
                    # QA Failed
                    qa_attempts += 1
                    if qa_attempts > self.max_qa_retries:
                        self.log(f"[{ass_filename}] QA failed max retries ({self.max_qa_retries}). Accepting current draft.")
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
        
        # Combine solution for this assignment
        full_solution_text = "\n\n".join(assignment_solution_parts)
        report_part = f"# Solution for {ass_filename}\n\n{full_solution_text}"
        
        # 5. Save to File
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
        
        # 1. Prepare Context
        full_context = ""
        input_overview = ""
        for filename, text in input_texts.items():
            full_context += f"--- START FILE: {os.path.basename(filename)} ---\n{text[:20000]}...\n--- END FILE ---\n\n"
            input_overview += f"- {os.path.basename(filename)}\n"

        # Ensure output dir exists
        output_dir = os.path.join("output", hz_name)
        os.makedirs(output_dir, exist_ok=True)
        
        final_reports = []
        
        # Parallel Execution
        # We use a ThreadPoolExecutor to run assignments in parallel
        # Note: UI callbacks might clash if multiple threads update same placeholders.
        # But for speed, this is necessary.
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            futures = []
            for ass_path in assignment_paths:
                futures.append(
                    executor.submit(
                        self.process_assignment, 
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

