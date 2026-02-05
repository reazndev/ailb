import os
import time
from typing import List, Dict, Callable, Optional
from src.llm.client import LLMClient
from src.agent.prompts import SYSTEM_PROMPT, PLANNER_PROMPT, WORKER_PROMPT, QA_PROMPT
from src.utils.cost import count_tokens, calculate_cost

class Agent:
    def __init__(self, provider="openai", model="gpt-4o", cost_limit: float = 0.0):
        self.llm = LLMClient(provider=provider, model=model)
        self.model = model
        self.console = None  # Legacy CLI support
        
        # State tracking
        self.total_cost = 0.0
        self.cost_limit = cost_limit
        self.accumulated_tokens = {"input": 0, "output": 0}
        
        # Callbacks
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_update: Optional[Callable[[Dict], None]] = None # Generic state update

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
        
        self.accumulated_tokens["input"] += in_tok
        self.accumulated_tokens["output"] += out_tok
        self.total_cost += cost
        
        if self.on_update:
            self.on_update({
                "total_cost": self.total_cost,
                "tokens": self.accumulated_tokens
            })

    def _check_budget(self):
        if self.cost_limit > 0 and self.total_cost >= self.cost_limit:
            raise Exception(f"Cost limit reached! (${self.total_cost:.4f} >= ${self.cost_limit:.4f})")

    def run(self, hz_name: str, assignment_text: str, input_texts: Dict[str, str]) -> str:
        self.log(f"Starting process for {hz_name}...")
        self.log(f"Model: {self.model} | Budget Cap: ${self.cost_limit}")
        
        # 1. Prepare Context
        full_context = ""
        input_overview = ""
        for filename, text in input_texts.items():
            full_context += f"--- START FILE: {os.path.basename(filename)}---\n{text[:20000]}...\n--- END FILE ---\n\n"
            input_overview += f"- {os.path.basename(filename)}\n"

        # 2. Plan
        self._check_budget()
        self.log("Creating a plan...")
        
        planner_input = PLANNER_PROMPT.format(
            assignment_text=assignment_text,
            input_overview=input_overview
        )
        
        plan_response = self.llm.generate_text(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=planner_input
        )
        self._track_usage(SYSTEM_PROMPT + planner_input, plan_response)
        
        self.log(f"Plan generated:\n{plan_response}")

        # Parse plan
        tasks = [line.strip() for line in plan_response.split('\n') if line.strip() and (line[0].isdigit() or line.startswith('-'))]
        
        final_output = []

        # 3. Execute Tasks
        for i, task in enumerate(tasks):
            self._check_budget()
            self.log(f"Working on task {i+1}/{len(tasks)}: {task}")
            
            worker_input = WORKER_PROMPT.format(
                current_task=task,
                context_text=full_context,
                assignment_text=assignment_text
            )
            
            draft = self.llm.generate_text(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=worker_input
            )
            self._track_usage(SYSTEM_PROMPT + worker_input, draft)
            
            # 4. QA Loop (Self-Correction)
            self._check_budget()
            self.log("Reviewing draft (QA)...")
            
            qa_input = QA_PROMPT.format(
                assignment_text=assignment_text,
                generated_content=draft
            )
            
            review = self.llm.generate_text(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=qa_input
            )
            self._track_usage(SYSTEM_PROMPT + qa_input, review)

            if "PASS" in review:
                self.log("QA Passed.")
                final_output.append(f"## {task}\n\n{draft}")
            else:
                self.log("QA failed. Improving...")
                # Retry once with feedback
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
                
                final_output.append(f"## {task}\n\n{refined_draft}")

        return "\n\n".join(final_output)

