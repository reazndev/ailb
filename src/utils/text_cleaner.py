import re

def replace_sz(text: str) -> str:
    """
    Replaces the German 'ß' (Eszett) with 'ss' as requested.
    """
    if not text:
        return ""
    return text.replace("ß", "ss").replace("ẞ", "SS")

def restore_umlauts(text: str) -> str:
    """
    Replaces ae, oe, ue with ä, ö, ü where appropriate using a safe heuristic.
    Excludes common words where 'ue' etc. are NOT umlauts (e.g., manuelle, aktuell).
    """
    if not text:
        return ""
    
    # List of common German/Latin words where ue/ae/oe should NOT be converted
    # This list can be expanded as needed.
    exceptions = [
        "manuelle", "aktuell", "quelle", "eventuell", "individuell",
        "statuen", "neue", "abenteuer", "treue", "feuer", "steuer",
        "sequenz", "konsequenz", "frequenz", "eloquent",
        "virtuell", "visuell", "kontextuell", "sexuell", "intellektuell",
        "audio", "video", "duell", "flue", "qüe", "qüelle"
    ]
    
    # Simple replacement map
    mapping = {"ae": "ä", "oe": "ö", "ue": "ü", "Ae": "Ä", "Oe": "Ö", "Ue": "Ü"}
    
    # Better approach: split into words, check exceptions, then re-join
    words = re.split(r'(\W+)', text)
    processed_words = []
    
    for word in words:
        low_word = word.lower()
        # Skip if word is in exceptions or contains 'qu'
        is_exception = False
        if "qu" in low_word:
            is_exception = True
        else:
            for exc in exceptions:
                if exc in low_word:
                    is_exception = True
                    break
        
        if is_exception:
            processed_words.append(word)
        else:
            # Apply mapping
            new_word = word
            for old, new in mapping.items():
                new_word = new_word.replace(old, new)
            processed_words.append(new_word)
            
    return "".join(processed_words)

def clean_ai_artifacts(text: str) -> str:
    """
    Removes common AI writing artifacts.
    """
    if not text:
        return ""
    
    text = text.replace(" — ", " - ")
    text = text.replace("—", "-")
    
    text = text.strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
        
    return text.strip()
