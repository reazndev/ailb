def replace_sz(text: str) -> str:
    """
    Replaces the German 'ß' (Eszett) with 'ss' as requested.
    """
    if not text:
        return ""
    return text.replace("ß", "ss")

def clean_ai_artifacts(text: str) -> str:
    """
    Removes common AI writing artifacts like excessive em-dashes 
    or unnecessary surrounding quotes if they appear at the start/end of the block.
    """
    if not text:
        return ""
    
    # Replace em-dash with standard dash/space if it looks like AI-filler
    text = text.replace(" — ", " - ")
    text = text.replace("—", "-")
    
    # Strip leading/trailing quotes that LLMs sometimes add
    text = text.strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
        
    return text.strip()
