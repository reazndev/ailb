from docx import Document
from docx.shared import RGBColor
import os
import re
from typing import List, Dict

DARK_BLUE = RGBColor(0x00, 0x00, 0x8B)

def integrate_solution_to_docx(original_path: str, output_path: str, task_results: List[Dict[str, str]]):
    """
    Robustly integrates AI solutions into the original DOCX.
    Uses strict matching for 'Teilaufgabe X' and placeholders.
    """
    print(f"DEBUG: Integrating {len(task_results)} tasks into {original_path}")
    
    try:
        if not os.path.exists(original_path):
            return False
            
        doc = Document(original_path)
        
        def get_task_number(title):
            match = re.search(r'(\d+)', title)
            return match.group(1) if match else None

        used_tasks = set()

        # 1. Stricter Table Integration
        for table in doc.tables:
            for row in table.rows:
                for i, cell in enumerate(row.cells):
                    ctext = cell.text.strip().lower()
                    for idx, res in enumerate(task_results):
                        if idx in used_tasks: continue
                        num = get_task_number(res['task'])
                        
                        patterns = [f"teilaufgabe {num}", f"aufgabe {num}", f"{num}.", f"auftrag {num}"]
                        if num and any(p == ctext or p in ctext for p in patterns if len(ctext) < 20):
                            for j in range(i + 1, len(row.cells)):
                                target = row.cells[j]
                                t_text = target.text.lower()
                                if not t_text.strip() or "lösung" in t_text or "..." in t_text:
                                    target.text = "" 
                                    p = target.paragraphs[0]
                                    run = p.add_run(res['content'])
                                    run.font.color.rgb = DARK_BLUE
                                    used_tasks.add(idx)
                                    break
                        if idx in used_tasks: break

        # 2. Strict Paragraph Integration
        for idx, res in enumerate(task_results):
            if idx in used_tasks: continue
            num = get_task_number(res['task'])
            if not num: continue

            target_p_idx = -1
            for p_idx, p in enumerate(doc.paragraphs):
                p_text = p.text.strip().lower()
                if p_text.startswith(f"teilaufgabe {num}") or p_text.startswith(f"aufgabe {num}"):
                    target_p_idx = p_idx
                    for look_ahead in range(p_idx + 1, min(p_idx + 10, len(doc.paragraphs))):
                        ahead_text = doc.paragraphs[look_ahead].text.strip().lower()
                        if "lösung" in ahead_text or "antwort" in ahead_text or ahead_text == "...":
                            target_p_idx = look_ahead
                            break
                        next_num = str(int(num) + 1)
                        if ahead_text.startswith(f"teilaufgabe {next_num}") or ahead_text.startswith(f"aufgabe {next_num}"):
                            target_p_idx = look_ahead - 1
                            break
                    break
            
            if target_p_idx != -1:
                anchor_p = doc.paragraphs[target_p_idx]
                new_p = doc.add_paragraph()
                anchor_p._element.addnext(new_p._element)
                run = new_p.add_run(res['content'])
                run.font.color.rgb = DARK_BLUE
                used_tasks.add(idx)

        # 3. Fallback: Append remaining tasks at the end
        remaining = [res for i, res in enumerate(task_results) if i not in used_tasks]
        if remaining:
            # We no longer add a special section header
            for res in remaining:
                p = doc.add_paragraph()
                p.add_run(f"**{res['task']}**\n").bold = True
                run = p.add_run(res['content'])
                run.font.color.rgb = DARK_BLUE
                doc.add_paragraph("")

        directory = os.path.dirname(output_path)
        if directory: os.makedirs(directory, exist_ok=True)
        doc.save(output_path)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def verify_docx_integration(file_path: str, task_results: List[Dict[str, str]]) -> List[int]:
    """
    Checks if each task's content is present in the DOCX file.
    Returns a list of indices of MISSING tasks.
    """
    if not os.path.exists(file_path):
        return list(range(len(task_results)))
    
    try:
        doc = Document(file_path)
        # Combine all text from paragraphs and tables
        full_text = ""
        for p in doc.paragraphs:
            full_text += p.text + "\n"
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    full_text += cell.text + " "
        
        missing_indices = []
        for i, res in enumerate(task_results):
            # Check for a unique snippet of the content (first 50 chars)
            snippet = res['content'][:50].strip()
            if snippet and snippet not in full_text:
                missing_indices.append(i)
        
        return missing_indices
    except:
        return list(range(len(task_results)))

def force_append_all_tasks(file_path: str, task_results: List[Dict[str, str]]):
    """
    Simplest possible append to ensure content is there.
    """
    try:
        doc = Document(file_path)
        for res in task_results:
            p = doc.add_paragraph()
            p.add_run(f"{res['task']}\n").bold = True
            run = p.add_run(res['content'])
            run.font.color.rgb = DARK_BLUE
        doc.save(file_path)
        return True
    except:
        return False

def append_solution_to_docx(original_path: str, output_path: str, task_results: List[Dict[str, str]]):
    return integrate_solution_to_docx(original_path, output_path, task_results)