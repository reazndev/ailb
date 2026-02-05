from docx import Document
from docxcompose.composer import Composer
import os

def append_solution_to_docx(original_path: str, output_path: str, solution_text: str):
    """
    Appends solution_text to the end of original_path DOCX using docxcompose.
    Saves to output_path.
    """
    print(f"DEBUG: Appending using docxcompose. Orig: {original_path}, Out: {output_path}")
    temp_solution_path = "temp_solution.docx"
    
    try:
        # 1. Create a temporary DOCX with the solution
        doc_solution = Document()
        doc_solution.add_heading('AI Solution', level=1)
        doc_solution.add_paragraph(solution_text)
        doc_solution.save(temp_solution_path)
        
        # 2. Open Original
        if os.path.exists(original_path):
            doc_original = Document(original_path)
            
            # 3. Compose
            # We must append the solution TO the original (master)
            composer = Composer(doc_original)
            
            # Load the solution doc again to be safe/clean
            doc_to_append = Document(temp_solution_path)
            composer.append(doc_to_append)
            
            # 4. Save
            directory = os.path.dirname(output_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
                
            composer.save(output_path)
            print(f"DEBUG: Successfully composed and saved to {output_path}")
            
        else:
            # Fallback if original doesn't exist: just save the solution
            print("DEBUG: Original not found, saving solution only.")
            directory = os.path.dirname(output_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            doc_solution.save(output_path)

        return True

    except Exception as e:
        print(f"Error editing DOCX with docxcompose: {e}")
        # Last resort fallback: try basic python-docx again just for the solution
        try:
            print("DEBUG: Attempting last resort fallback...")
            doc = Document()
            doc.add_paragraph("Error merging documents. Here is the solution:")
            doc.add_paragraph(solution_text)
            doc.save(output_path)
            return True
        except:
            return False
            
    finally:
        if os.path.exists(temp_solution_path):
            try:
                os.remove(temp_solution_path)
            except:
                pass
