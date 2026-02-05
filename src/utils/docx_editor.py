from docx import Document
import os

def append_solution_to_docx(original_path: str, output_path: str, solution_text: str):
    """
    Copies the original DOCX and appends the solution text to the end of it.
    """
    try:
        if os.path.exists(original_path):
             doc = Document(original_path)
        else:
             doc = Document()
        
        doc.add_page_break()
        doc.add_heading('AI Solution', level=1)
        doc.add_paragraph(solution_text)
        
        doc.save(output_path)
        return True
    except Exception as e:
        print(f"Error editing DOCX: {e}")
        return False
