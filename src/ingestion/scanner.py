import os
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class HZData:
    name: str
    path: str
    input_files: List[str] = field(default_factory=list)
    assignment_files: List[str] = field(default_factory=list)
    solutions_files: List[str] = field(default_factory=list)

def scan_directory(base_path: str = "data") -> List[HZData]:
    """
    Scans the base_path for HZ folders (Handlungsziel).
    Expected structure:
    base_path/
      HZ_Name/
        Input/
        Assignments/
        Solutions/
    """
    hz_list = []
    
    if not os.path.exists(base_path):
        print(f"Base path '{base_path}' does not exist.")
        return []

    # Iterate over top-level directories in base_path
    for entry in os.scandir(base_path):
        if entry.is_dir():
            hz_name = entry.name
            hz_path = entry.path
            
            hz_data = HZData(name=hz_name, path=hz_path)
            
            # Check for Input folder
            input_dir = os.path.join(hz_path, "Input")
            if os.path.exists(input_dir):
                for root, _, files in os.walk(input_dir):
                    for file in files:
                        if not file.startswith("~") and not file.startswith("."): # Ignore temp/hidden files
                            hz_data.input_files.append(os.path.join(root, file))
            
            # Check for Assignments folder
            assignments_dir = os.path.join(hz_path, "Assignments")
            if os.path.exists(assignments_dir):
                for root, _, files in os.walk(assignments_dir):
                    for file in files:
                        if not file.startswith("~") and not file.startswith("."):
                            hz_data.assignment_files.append(os.path.join(root, file))
                            
            # Check for Solutions folder
            solutions_dir = os.path.join(hz_path, "Solutions")
            if os.path.exists(solutions_dir):
                for root, _, files in os.walk(solutions_dir):
                    for file in files:
                        if not file.startswith("~") and not file.startswith("."):
                            hz_data.solutions_files.append(os.path.join(root, file))
            
            # Always add the HZ if it's a directory in the data folder, 
            # assuming it's a valid project container.
            if os.path.exists(input_dir) or os.path.exists(assignments_dir) or os.path.exists(solutions_dir):
                hz_list.append(hz_data)
                
    return hz_list
