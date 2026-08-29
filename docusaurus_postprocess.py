#!/usr/bin/env python3
"""
Post-processor to convert DITA-OT markdown output to Docusaurus format
Converts:
1. Note/warning/tip formatting to Docusaurus admonitions
2. HTML tables to Markdown tables
3. Shortdesc to italic text
4. Code language hints normalization
"""

import re
import sys
import os
from pathlib import Path
import argparse
import xml.etree.ElementTree as ET
import html

def convert_html_table_to_markdown(html_table):
    """Convert a single HTML table to Markdown format"""
    # Clean up the HTML table first - normalize whitespace but preserve content
    # Remove excessive newlines and spaces while keeping necessary spacing
    html_table = re.sub(r'>\s+<', '><', html_table)  # Remove spaces between tags
    html_table = re.sub(r'\s*\n\s*', ' ', html_table)  # Replace newlines with single space

    # Extract rows
    rows = []

    # Find all tr elements - handle both with and without attributes
    tr_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL)
    for tr_match in tr_pattern.finditer(html_table):
        tr_content = tr_match.group(1)

        # Extract cells (th or td) - handle both with and without attributes
        cells = []
        cell_pattern = re.compile(r'<t[hd][^>]*>(.*?)</t[hd]>', re.DOTALL)
        for cell_match in cell_pattern.finditer(tr_content):
            cell_content = cell_match.group(1).strip()

            # Decode HTML entities (e.g., &lt; to <, &gt; to >)
            cell_content = html.unescape(cell_content)

            # Handle list items - convert bullet points to <br/> separated items
            if '-   ' in cell_content:
                # Split by list items
                items = re.split(r'\n*-\s+', cell_content)
                # Remove empty first item if exists
                items = [item.strip() for item in items if item.strip()]
                # Join with <br/> (self-closing) for MDX/Docusaurus compatibility
                cell_content = '<br/>'.join([f'• {item}' for item in items])
            else:
                # For non-list content, replace newlines with spaces
                cell_content = re.sub(r'\n+', ' ', cell_content)
                # Clean up extra spaces
                cell_content = re.sub(r'\s+', ' ', cell_content)

            cells.append(cell_content)
        
        if cells:
            rows.append(cells)
    
    if not rows:
        return html_table
    
    # Determine if first row is header (in thead)
    has_thead = '<thead>' in html_table
    
    if has_thead:
        # First rows are headers
        headers = []
        data_rows = []
        in_thead = True
        for i, row in enumerate(rows):
            if i == 0 or (in_thead and '<tbody>' not in html_table[:html_table.find('</tr>' * (i+1))]):
                headers = row
            else:
                data_rows.append(row)
                in_thead = False
    else:
        # No thead, use first row as headers
        headers = rows[0] if rows else []
        data_rows = rows[1:] if len(rows) > 1 else []
    
    if not headers:
        return html_table
    
    # Build markdown table
    lines = []
    
    # Header row
    lines.append('| ' + ' | '.join(headers) + ' |')
    
    # Separator row
    lines.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
    
    # Data rows
    for row in data_rows:
        # Ensure row has same number of cells as headers
        while len(row) < len(headers):
            row.append('')
        lines.append('| ' + ' | '.join(row[:len(headers)]) + ' |')
    
    return '\n'.join(lines)

def convert_to_docusaurus(content):
    """Convert DITA-OT markdown to Docusaurus format"""

    # Debug: Check for unescaped patterns before processing
    import os
    debug_file = os.getenv('DEBUG_FILE', '')
    if debug_file and debug_file in content[:500]:
        print(f"DEBUG: Processing file containing {debug_file}")
        if '<arg>' in content:
            print("DEBUG: Found <arg> in content BEFORE processing")

    # First convert HTML tables to Markdown with proper spacing
    table_pattern = re.compile(r'<table[^>]*>.*?</table>', re.DOTALL)
    content = table_pattern.sub(lambda m: '\n\n' + convert_html_table_to_markdown(m.group(0)) + '\n\n', content)

    # Fix image paths to use relative references with ./
    # Convert ![](image/file.png) to ![](./image/file.png)
    content = re.sub(r'!\[\]\((?!\./)([^/])', r'![](./' + r'\1', content)

    # Fix HTML entities that represent literal angle brackets (not HTML tags)
    # Convert &lt;anything&gt; to `<anything>` for better readability
    # This handles cases like &lt;arg&gt;, &lt;parameter&gt;, &lt;example&gt;, etc.
    content = re.sub(r'&lt;([^&]+?)&gt;', r'`<\1>`', content)

    # MDX Fix: Escape angle brackets that look like JSX/HTML tags but are plain text
    # This handles various cases that MDX would misinterpret as JSX
    # BUT: Don't escape if already in backticks or in a code block

    # First, protect code blocks from escaping
    # Split content by code blocks and only process non-code parts

    def clean_escaped_parentheses(text):
        """Clean up escaped parentheses from DITA-OT output"""
        text = text.replace('\\(', '(')
        text = text.replace('\\)', ')')
        return text

    def escape_mdx_tags(text):
        """Escape angle bracket patterns that MDX would misinterpret, but not if already escaped"""
        # Debug
        if debug_file and '<arg>' in text:
            print(f"DEBUG escape_mdx_tags: Found <arg> in text chunk")

        # DON'T skip the entire text just because some patterns are already escaped!
        # The negative lookbehind/lookahead in the regex patterns will handle
        # skipping already-escaped patterns individually

        # 1. Handle simple tags like <arg>, <param>, <value>
        text = re.sub(r'(?<!`)<([a-z_][a-z0-9_]*(?:\s+[^>]*)?)>(?!`)', r'`<\1>`', text)

        # 2. Handle self-closing variants like <arg/>
        text = re.sub(r'(?<!`)<([a-z_][a-z0-9_]*)\s*/>(?!`)', r'`<\1/>`', text)

        # 3. Handle uppercase tags like <IdName>, <DatabaseName>
        text = re.sub(r'(?<!`)<([A-Z][a-zA-Z0-9_]*)>(?!`)', r'`<\1>`', text)

        # 4. Handle special characters that look like tags: <;>, <,>, <host-server;host2-server2>
        text = re.sub(r'(?<!`)<([^>]*[;,\-][^>]*)>(?!`)', r'`<\1>`', text)

        # 5. Handle single special character "tags" like <;> or <,>
        text = re.sub(r'(?<!`)<([;,])>(?!`)', r'`<\1>`', text)

        # 6. Handle quotes inside angle brackets like <""> or <"value">
        text = re.sub(r'(?<!`)<("[^"]*")>(?!`)', r'`<\1>`', text)
        text = re.sub(r'(?<!`)<("")>(?!`)', r'`<"">`', text)

        # 7. Handle patterns with pipes and backslashes like <true \| false>, <block \| allow>
        text = re.sub(r'(?<!`)<([^>]*\\\|[^>]*)>(?!`)', r'`<\1>`', text)

        # 8. Handle patterns with backslashes first (most specific)
        text = re.sub(r'(?<!`)<([^>]*\\[^>]*)>(?!`)', r'`<\1>`', text)

        # 9. Handle any remaining patterns with pipes
        text = re.sub(r'(?<!`)<([^>]*\|[^>]*)>(?!`)', r'`<\1>`', text)

        # 10. Handle simple angle bracket patterns like <arg>, <application name>
        text = re.sub(r'(?<!`)<([^>]+)>(?!`)', r'`<\1>`', text)

        return text

    # Split by triple-backtick code blocks
    parts = re.split(r'(```[\s\S]*?```)', content)
    processed_parts = []

    for i, part in enumerate(parts):
        if i % 2 == 0:  # Not a code block
            processed_parts.append(escape_mdx_tags(part))
        else:  # Code block, keep as-is
            processed_parts.append(part)

    content = ''.join(processed_parts)

    # Debug: Check after processing
    if debug_file and debug_file in content[:500]:
        if '<arg>' in content:
            print("DEBUG: <arg> STILL in content AFTER processing")
            # Show a sample
            for line in content.split('\n'):
                if '<arg>' in line:
                    print(f"DEBUG: Line with <arg>: {line[:100]}")
                    break
        else:
            print("DEBUG: <arg> successfully escaped")

    # 7. Also escape standalone < and > that aren't part of markdown or real HTML
    # This handles cases like "value < 10" or "data > 5"
    # But we need to be careful not to break actual markdown/HTML
    # So we only do this in table cells (between pipes)
    content = re.sub(r'(\|[^|\n]*)\s+<\s+([^|\n]*\|)', r'\1 &lt; \2', content)
    content = re.sub(r'(\|[^|\n]*)\s+>\s+([^|\n]*\|)', r'\1 &gt; \2', content)
    
    # Format shortdesc as italic with separator line
    # Matches: # Title\n\nShortdesc text (one line only)\n\n
    content = re.sub(
        r'^(#+ [^\n]+)\n\n([^\n#*\-\[\|<>:]+)\n\n',
        r'\1\n\n*\2*\n\n---\n\n',
        content,
        count=1,  # Only format the first line after title as shortdesc
        flags=re.MULTILINE
    )
    
    # NOTE: Adding headers for prereq/context/result sections is not implemented
    # because DITA-OT doesn't preserve section markers in markdown output.
    # Without reliable markers, any heuristic approach would be fragile and
    # could incorrectly modify non-task documents.
    
    # Normalize code block language hints
    # Convert ```language-sql to ```sql for better compatibility
    content = re.sub(r'```language-(\w+)', r'```\1', content)

    # Convert DITA definition lists (rendered as bullet lists with bold terms)
    # Pattern: -   **Term**\n\n    Definition (but NOT platform lists like "For Windows")
    # Convert to: Term\n:   Definition
    dl_pattern = r'-\s+\*\*(?!For\s)(.*?)\*\*\n\n\s+(.*?)(?=\n-\s+\*\*|\n\n[^-\s]|\Z)'

    def convert_dl_entry(match):
        term = match.group(1)
        definition = match.group(2)
        # Remove extra indentation from definition
        definition = re.sub(r'^\s{4}', '', definition, flags=re.MULTILINE)
        return f"{term}\n:   {definition}\n"

    content = re.sub(dl_pattern, convert_dl_entry, content, flags=re.MULTILINE | re.DOTALL)

    # Fix broken bullet lists where DITA ul/li creates separate bullets and paragraphs
    # Pattern: -   **Header**\n\n\nParagraph -> -   **Header**\n    Paragraph
    content = re.sub(
        r'-\s+(\*\*[^*]+\*\*)\n\n\n([^\n-]+)',
        r'- \1\n  \2',
        content,
        flags=re.MULTILINE
    )

    # Pattern for inline note formatting like **Note:** or **Important:** 
    patterns = [
        # **Important:** text -> :::info[Important]\n\ntext\n\n:::
        (r'(\*\*Important:\*\*)\s*(.*?)(?=\n\n|\n$|\Z)', r'\n\n:::info[Important]\n\n\2\n\n:::', re.MULTILINE | re.DOTALL),
        
        # **Note:** text -> :::note\n\ntext\n\n:::
        (r'(\*\*Note:\*\*)\s*(.*?)(?=\n\n|\n$|\Z)', r'\n\n:::note\n\n\2\n\n:::', re.MULTILINE | re.DOTALL),
        
        # **Info:** text -> :::info\n\ntext\n\n:::
        (r'(\*\*Info:\*\*)\s*(.*?)(?=\n\n|\n$|\Z)', r'\n\n:::info\n\n\2\n\n:::', re.MULTILINE | re.DOTALL),
        
        # **Tip:** text -> :::tip\n\ntext\n\n:::
        (r'(\*\*Tip:\*\*)\s*(.*?)(?=\n\n|\n$|\Z)', r'\n\n:::tip\n\n\2\n\n:::', re.MULTILINE | re.DOTALL),
        
        # **Warning:** text -> :::warning\n\ntext\n\n:::
        (r'(\*\*Warning:\*\*)\s*(.*?)(?=\n\n|\n$|\Z)', r'\n\n:::warning\n\n\2\n\n:::', re.MULTILINE | re.DOTALL),
        
        # **Caution:** text -> :::danger\n\ntext\n\n:::
        (r'(\*\*Caution:\*\*)\s*(.*?)(?=\n\n|\n$|\Z)', r'\n\n:::danger\n\n\2\n\n:::', re.MULTILINE | re.DOTALL),
        
        # CAUTION: text (without bold) -> :::danger\n\ntext\n\n:::
        (r'^CAUTION:\s*\n+(.*?)(?=\n\n|\n$|\Z)', r'\n\n:::danger\n\n\1\n\n:::', re.MULTILINE | re.DOTALL),
        
        # **Danger:** text -> :::danger\n\ntext\n\n:::
        (r'(\*\*Danger:\*\*)\s*(.*?)(?=\n\n|\n$|\Z)', r'\n\n:::danger\n\n\2\n\n:::', re.MULTILINE | re.DOTALL),
        
        # **Restriction:** text -> :::warning[Restriction]\n\ntext\n\n:::
        (r'(\*\*Restriction:\*\*)\s*(.*?)(?=\n\n|\n$|\Z)', r'\n\n:::warning[Restriction]\n\n\2\n\n:::', re.MULTILINE | re.DOTALL),
        
        # **Attention:** text -> :::warning\n\ntext\n\n:::
        (r'(\*\*Attention:\*\*)\s*(.*?)(?=\n\n|\n$|\Z)', r'\n\n:::warning\n\n\2\n\n:::', re.MULTILINE | re.DOTALL),
    ]
    
    # Apply all patterns
    for pattern, replacement, flags in patterns:
        content = re.sub(pattern, replacement, content, flags=flags)

    # Remove Parent topic lines entirely for now
    # Pattern: **Parent topic:**[Text](path)
    content = re.sub(
        r'\*\*Parent topic:\*\*\[([^\]]+)\]\([^)]+\)\n*',
        '',
        content
    )

    # Clean up escaped parentheses from DITA-OT output
    content = clean_escaped_parentheses(content)

    return content

def extract_title_from_md(file_path):
    """Extract the title from a markdown file (first # heading)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('# '):
                    title = line[2:].strip()
                    # Remove existing numbering if present (e.g., "1. Title" -> "Title")
                    clean_title = re.sub(r'^\d+\.?\s*', '', title)
                    # Clean title for filename: remove special chars, spaces to underscores
                    clean_title = re.sub(r'[^\w\s-]', '', clean_title)
                    clean_title = re.sub(r'\s+', '_', clean_title)
                    return clean_title
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return None

def parse_ditamap(ditamap_path):
    """Parse DITAMAP file and return ordered list of (dita_file, navtitle)"""
    try:
        tree = ET.parse(ditamap_path)
        root = tree.getroot()

        # Find all topicref elements
        topicrefs = []
        for topicref in root.findall('.//topicref'):
            href = topicref.get('href')
            navtitle = topicref.get('navtitle')
            if href and href.endswith('.dita'):
                topicrefs.append((href, navtitle))

        return topicrefs
    except Exception as e:
        print(f"Error parsing DITAMAP {ditamap_path}: {e}")
        return []

def add_numbering_to_titles(output_dir, ditamap_path):
    """Add numbering to H1 titles in markdown files based on DITAMAP order"""
    if not ditamap_path or not os.path.exists(ditamap_path):
        print("No DITAMAP file found, skipping title numbering")
        return

    # Parse DITAMAP to get order
    topicrefs = parse_ditamap(ditamap_path)
    if not topicrefs:
        print("No topicrefs found in DITAMAP, skipping title numbering")
        return

    print(f"Adding numbering to titles based on DITAMAP order...")

    # Create mapping from DITA filename to order
    file_order = {}
    file_titles = {}
    for i, (dita_href, navtitle) in enumerate(topicrefs, 1):
        # Convert .dita to .md
        md_file = dita_href.replace('.dita', '.md')
        file_order[md_file] = i

    # Process files to add numbering to titles
    output_path = Path(output_dir)
    if not output_path.exists():
        print(f"Output directory {output_dir} does not exist")
        return

    # First pass: collect titles for index.md
    for md_file in output_path.glob('*.md'):
        if md_file.name == 'index.md':
            continue

        # Find the corresponding original filename
        original_name = None
        for orig_name in file_order.keys():
            if md_file.name.endswith(f"_{orig_name}") or md_file.name == orig_name:
                original_name = orig_name
                break

        if original_name and original_name in file_order:
            order_num = file_order[original_name]

            # Read file and extract current title
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Find first H1 title
                title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
                if title_match:
                    current_title = title_match.group(1).strip()
                    # Remove existing numbering if present
                    clean_title = re.sub(r'^\d+\.?\s*', '', current_title)
                    new_title = f"{order_num}. {clean_title}"

                    # Replace the title in content
                    new_content = re.sub(
                        r'^# .+$',
                        f'# {new_title}',
                        content,
                        count=1,
                        flags=re.MULTILINE
                    )

                    # Write back to file
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)

                    file_titles[order_num] = (clean_title, md_file.name)
                    print(f"  Updated title in {md_file.name}: {new_title}")

            except Exception as e:
                print(f"  Error processing {md_file.name}: {e}")

    # Second pass: update index.md with numbered table of contents
    index_file = output_path / 'index.md'
    if index_file.exists():
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Create numbered table of contents
            toc_lines = []
            for i in sorted(file_titles.keys()):
                title, filename = file_titles[i]
                # Create relative link to the file (with numeric prefix from renamed files)
                link_name = f"{i:02d}_{title.replace(' ', '_')}"
                toc_lines.append(f"{i}. [{title}]({link_name})")

            if toc_lines:
                toc_content = '\n'.join(toc_lines)

                # Replace everything after the title with the numbered TOC
                # Look for the pattern: # Title\n\n and replace everything after
                title_pattern = r'(# [^\n]+\n\n).*'
                if re.search(title_pattern, content, re.DOTALL):
                    new_content = re.sub(
                        title_pattern,
                        lambda m: m.group(1) + toc_content,
                        content,
                        flags=re.DOTALL
                    )
                else:
                    # Fallback: append to end
                    new_content = content + '\n\n' + toc_content

                with open(index_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                print(f"  Updated index.md with numbered table of contents")

        except Exception as e:
            print(f"  Error updating index.md: {e}")

def rename_files_by_ditamap(output_dir, ditamap_path):
    """Rename files in output_dir according to DITAMAP order"""
    if not ditamap_path or not os.path.exists(ditamap_path):
        print("No DITAMAP file found, skipping file renaming")
        return

    # Parse DITAMAP to get order
    topicrefs = parse_ditamap(ditamap_path)
    if not topicrefs:
        print("No topicrefs found in DITAMAP, skipping file renaming")
        return

    print(f"Renaming {len(topicrefs)} files according to DITAMAP order...")

    # Create mapping from DITA filename to order
    file_order = {}
    for i, (dita_href, navtitle) in enumerate(topicrefs, 1):
        # Convert .dita to .md
        md_file = dita_href.replace('.dita', '.md')
        file_order[md_file] = i

    # Rename files in output directory
    output_path = Path(output_dir)
    if not output_path.exists():
        print(f"Output directory {output_dir} does not exist")
        return

    renamed_files = []

    for md_file in output_path.glob('*.md'):
        filename = md_file.name

        if filename in file_order:
            order_num = file_order[filename]

            # Extract actual title from markdown file
            actual_title = extract_title_from_md(md_file)
            if actual_title:
                new_name = f"{order_num:02d}_{actual_title}.md"
            else:
                # Fallback to original filename
                clean_name = filename.replace('.md', '')
                new_name = f"{order_num:02d}_{clean_name}.md"

            new_path = md_file.parent / new_name

            # Only rename if different
            if md_file.name != new_name:
                print(f"  {md_file.name} -> {new_name}")
                md_file.rename(new_path)
                renamed_files.append((filename, new_name))
        else:
            print(f"  Warning: {filename} not found in DITAMAP, keeping original name")

    print(f"Renamed {len(renamed_files)} files according to DITAMAP order")

def process_file(input_path, output_path=None):
    """Process a single markdown file"""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    converted = convert_to_docusaurus(content)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(converted)
    else:
        # Overwrite the input file
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(converted)

    return converted

def process_directory(input_dir, output_dir=None, ditamap_path=None):
    """Process all markdown files in a directory"""
    input_path = Path(input_dir)

    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_path

    md_files = list(input_path.glob('**/*.md'))

    for md_file in md_files:
        relative_path = md_file.relative_to(input_path)

        if output_dir:
            output_file = output_path / relative_path
            output_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_file = md_file

        print(f"Processing {md_file} -> {output_file}")
        process_file(md_file, output_file)

    print(f"Processed {len(md_files)} files")

    # Add numbering and rename files according to DITAMAP order if provided
    if ditamap_path and (output_dir or input_dir):
        target_dir = output_dir if output_dir else input_dir

        # Check if it's a complex hierarchical structure
        is_hierarchical = False
        try:
            tree = ET.parse(ditamap_path)
            root = tree.getroot()

            # Check if it's a bookmap with chapters referencing other ditamaps
            if 'bookmap' in root.tag:
                for chapter in root.findall('.//chapter'):
                    if chapter.get('format') == 'ditamap':
                        is_hierarchical = True
                        break

            # Also check for deeply nested topicrefs (3+ levels)
            if not is_hierarchical:
                for topicref in root.findall('.//topicref/topicref/topicref'):
                    is_hierarchical = True
                    break
        except Exception as e:
            print(f"Warning: Could not check DITAMAP structure: {e}")

        if is_hierarchical:
            print("Detected hierarchical structure, using hierarchical processor...")
            from hierarchical_processor import HierarchicalProcessor
            hier_processor = HierarchicalProcessor(target_dir, ditamap_path)
            hier_processor.process()
        else:
            add_numbering_to_titles(target_dir, ditamap_path)
            rename_files_by_ditamap(target_dir, ditamap_path)

def main():
    parser = argparse.ArgumentParser(description='Convert DITA-OT markdown to Docusaurus format')
    parser.add_argument('input', help='Input file or directory')
    parser.add_argument('-o', '--output', help='Output file or directory (if not specified, modifies in place)')
    parser.add_argument('-r', '--recursive', action='store_true', help='Process directories recursively')
    parser.add_argument('-d', '--ditamap', help='DITAMAP file to use for file ordering and renaming')

    args = parser.parse_args()

    input_path = Path(args.input)

    if input_path.is_file():
        output_path = args.output if args.output else None
        process_file(input_path, output_path)
        print(f"Converted {input_path}")
    elif input_path.is_dir():
        process_directory(input_path, args.output, args.ditamap)
    else:
        print(f"Error: {input_path} is not a valid file or directory")
        sys.exit(1)

if __name__ == '__main__':
    main()