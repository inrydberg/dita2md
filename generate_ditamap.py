#!/usr/bin/env python3
"""Generate a simple DITAMAP from DITA files in a directory"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

def extract_title(dita_file):
    """Extract title from a DITA file"""
    try:
        tree = ET.parse(dita_file)
        root = tree.getroot()
        title_elem = root.find('.//title')
        if title_elem is not None and title_elem.text:
            return title_elem.text.strip()
    except:
        pass
    # Fallback to filename without extension
    return Path(dita_file).stem.replace('_', ' ')

def generate_ditamap(input_dir, output_file):
    """Generate a DITAMAP from all DITA files in input_dir"""
    
    dita_files = sorted(Path(input_dir).glob('*.dita'))
    
    if not dita_files:
        print("No DITA files found")
        return False
    
    # Create DITAMAP structure
    ditamap = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">
<map id="generated_map">
  <title>Generated Documentation Map</title>
'''
    
    for dita_file in dita_files:
        title = extract_title(dita_file)
        filename = dita_file.name
        ditamap += f'  <topicref href="{filename}" navtitle="{title}"/>\n'
    
    ditamap += '</map>'
    
    # Write DITAMAP
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(ditamap)
    
    print(f"Generated {output_file} with {len(dita_files)} topics")
    return True

if __name__ == '__main__':
    input_dir = sys.argv[1] if len(sys.argv) > 1 else 'input'
    output_file = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, 'generated.ditamap')
    
    if generate_ditamap(input_dir, output_file):
        sys.exit(0)
    else:
        sys.exit(1)
