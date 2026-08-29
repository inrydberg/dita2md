#!/usr/bin/env python3
"""
Enhanced hierarchical processor for complex DITA structures.
Handles nested numbering with zero-padding, folder renaming, and proper hierarchical index generation.
"""

import os
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
import argparse

class HierarchicalProcessor:
    def __init__(self, output_dir, ditamap_path):
        self.output_dir = Path(output_dir)
        self.ditamap_path = Path(ditamap_path)
        self.input_dir = self.ditamap_path.parent
        self.file_mappings = {}  # Maps original file paths to new numbered names
        self.toc_structure = []  # Hierarchical TOC structure
        self.folder_mappings = {}  # Maps original folder names to new numbered names
        self.book_title = None  # Will be extracted from bookmap

    def parse_bookmap(self):
        """Parse the main bookmap/map and process all chapters/topics"""
        try:
            tree = ET.parse(self.ditamap_path)
            root = tree.getroot()

            # Check if this is a bookmap or a simple map
            is_bookmap = 'bookmap' in root.tag

            # Extract book/map title
            if is_bookmap:
                # Try to get title from bookmap
                booktitle_elem = root.find('.//mainbooktitle')
                if booktitle_elem is not None and booktitle_elem.text:
                    self.book_title = booktitle_elem.text.strip()
                else:
                    self.book_title = self.ditamap_path.stem.replace('_', ' ')
            else:
                # For simple maps, get title from title attribute
                self.book_title = root.get('title', self.ditamap_path.stem.replace('_', ' '))

            chapter_num = 1

            # Process chapters for bookmap or topicrefs for simple map
            if is_bookmap:
                for chapter in root.findall('.//chapter'):
                    href = chapter.get('href')
                    format_type = chapter.get('format', 'dita')

                    if format_type == 'ditamap' and href:
                        # Process sub-ditamap
                        sub_ditamap_path = self.input_dir / href
                        if sub_ditamap_path.exists():
                            # Use simple numbering (not zero-padded)
                            simple_num = str(chapter_num)
                            self.process_chapter(sub_ditamap_path, simple_num, chapter_num)
                            chapter_num += 1
                    elif format_type == 'dita' and href:
                        # Process single DITA file as chapter
                        simple_num = str(chapter_num)
                        self.process_single_file(href, simple_num, chapter_num)
                        chapter_num += 1
            else:
                # For simple maps, process topicrefs
                for topicref in root.findall('.//topicref'):
                    href = topicref.get('href')
                    if href and href.endswith('.dita'):
                        # Convert DITA file reference to markdown
                        md_file = href.replace('.dita', '.md')
                        navtitle = topicref.get('navtitle', '')

                        # Add to file mappings with numbering
                        self.file_mappings[md_file] = {
                            'numbering': str(chapter_num),
                            'navtitle': navtitle,
                            'subdirectory': '.',
                            'original_folder': '.',
                            'is_chapter_main': False
                        }
                        chapter_num += 1

        except Exception as e:
            print(f"Error parsing bookmap: {e}")
            return False

        return True

    def process_chapter(self, ditamap_path, chapter_num_padded, chapter_num_int):
        """Process a chapter ditamap"""
        try:
            tree = ET.parse(ditamap_path)
            root = tree.getroot()

            # Get chapter title from map
            chapter_title = root.get('title', 'Chapter')

            # Store folder mapping with simple numbering (not zero-padded)
            # We'll update this with the proper title later
            folder_name = ditamap_path.parent.name
            self.folder_mappings[folder_name] = f"{chapter_num_padded}_{folder_name}"

            # The FIRST topicref is the chapter's main content (e.g., introduction.dita)
            # Its CHILDREN are the actual sections (1.1, 1.2, etc.)
            first_topicref = root.find('./topicref')
            if first_topicref is not None:
                # Process the main chapter file (this becomes the chapter content)
                href = first_topicref.get('href')
                if href:
                    md_file = href.replace('.dita', '.md')
                    rel_dir = ditamap_path.parent.relative_to(self.input_dir) if ditamap_path.parent != self.input_dir else Path('.')
                    full_md_path = rel_dir / md_file if rel_dir != Path('.') else Path(md_file)

                    # This is the CHAPTER content (number it as just the chapter number)
                    self.file_mappings[str(full_md_path)] = {
                        'numbering': str(chapter_num_int),  # Just "1", "2", etc.
                        'navtitle': first_topicref.get('navtitle', ''),
                        'subdirectory': str(rel_dir),
                        'original_folder': ditamap_path.parent.name,
                        'is_chapter_main': True  # Mark this as main chapter content
                    }

                # Now process its CHILDREN as sections (1.1, 1.2, etc.)
                section_num = 1
                for child_topicref in first_topicref.findall('./topicref'):
                    self.process_topicref(child_topicref, f"{chapter_num_int}.{section_num}", ditamap_path.parent)
                    section_num += 1
            else:
                # Fallback if structure is different
                topic_num = 1
                for topicref in root.findall('./topicref'):
                    self.process_topicref(topicref, f"{chapter_num_int}.{topic_num}", ditamap_path.parent)
                    topic_num += 1

        except Exception as e:
            print(f"Error processing chapter {ditamap_path}: {e}")

    def process_topicref(self, element, numbering, base_dir):
        """Process a topicref element recursively"""
        href = element.get('href')
        navtitle = element.get('navtitle', '')

        if href:
            # Convert .dita to .md
            md_file = href.replace('.dita', '.md')

            # Calculate relative path from base input directory
            rel_dir = base_dir.relative_to(self.input_dir) if base_dir != self.input_dir else Path('.')
            full_md_path = rel_dir / md_file if rel_dir != Path('.') else Path(md_file)

            # Add to file mappings
            self.file_mappings[str(full_md_path)] = {
                'numbering': numbering,
                'navtitle': navtitle,
                'subdirectory': str(rel_dir),
                'original_folder': base_dir.name
            }

        # Process nested topicrefs
        nested = element.findall('./topicref')
        for i, child in enumerate(nested, 1):
            self.process_topicref(child, f"{numbering}.{i}", base_dir)

    def process_single_file(self, href, numbering_padded, numbering_int):
        """Process a single DITA file"""
        md_file = href.replace('.dita', '.md')
        self.file_mappings[md_file] = {
            'numbering': str(numbering_int),
            'navtitle': '',
            'subdirectory': '.',
            'original_folder': '.'
        }

    def rename_folders(self):
        """Rename all folders with hierarchical numbering"""
        print(f"\nRenaming {len(self.folder_mappings)} folders...")

        # Create a temporary directory to avoid conflicts
        temp_dir = self.output_dir / '_temp_rename'
        temp_dir.mkdir(exist_ok=True)

        # First, move all folders to temp with new names
        for old_name, new_name in sorted(self.folder_mappings.items()):
            old_path = self.output_dir / old_name
            if old_path.exists() and old_path.is_dir():
                temp_path = temp_dir / new_name
                print(f"  {old_name} -> {new_name}")
                shutil.move(str(old_path), str(temp_path))

        # Then move them back from temp to output
        for folder in temp_dir.iterdir():
            if folder.is_dir():
                shutil.move(str(folder), str(self.output_dir / folder.name))

        # Remove temp directory
        temp_dir.rmdir()

    def rename_folders_with_titles(self):
        """Rename folders using the updated mappings with meaningful titles"""
        print(f"\nRenaming folders with meaningful titles...")

        # Create a temporary directory to avoid conflicts
        temp_dir = self.output_dir / '_temp_rename'
        temp_dir.mkdir(exist_ok=True)

        # Find actual folders and map them to new names based on updated folder_mappings
        current_folders = {}
        for old_original_name, new_name in self.folder_mappings.items():
            # Find the current folder name (it should be numbered like "10_applications")
            for folder_path in self.output_dir.iterdir():
                if folder_path.is_dir() and folder_path.name != '_temp_rename':
                    # Check if this is the numbered version of the original folder
                    if folder_path.name.endswith(f"_{old_original_name}") or folder_path.name.startswith(f"{old_original_name}_") or folder_path.name.split('_', 1)[-1] == old_original_name:
                        current_folders[folder_path.name] = new_name
                        break

        # Rename found folders
        for current_name, new_name in current_folders.items():
            if current_name != new_name:  # Only rename if different
                old_path = self.output_dir / current_name
                if old_path.exists() and old_path.is_dir():
                    temp_path = temp_dir / new_name
                    print(f"  {current_name} -> {new_name}")
                    shutil.move(str(old_path), str(temp_path))

        # Then move them back from temp to output
        for folder in temp_dir.iterdir():
            if folder.is_dir():
                shutil.move(str(folder), str(self.output_dir / folder.name))

        # Remove temp directory
        temp_dir.rmdir()

    def extract_titles_and_rename_folders(self):
        """Extract chapter titles from generated index.md files and rename folders with meaningful names"""
        print(f"\nExtracting chapter titles and renaming folders...")

        # Extract chapter titles and update folder mappings
        for original_path, info in self.file_mappings.items():
            if info.get('is_chapter_main'):
                # This is a main chapter file, extract its title for folder naming
                original_folder = info.get('original_folder', '.')

                # The folder has already been renamed to basic numbered version
                current_folder_name = self.folder_mappings.get(original_folder, original_folder)

                # Look for index.md in the renamed folder (which should have the title)
                index_path = self.output_dir / current_folder_name / 'index.md'

                if index_path.exists():
                    try:
                        with open(index_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Extract title from the markdown file
                        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
                        if title_match:
                            chapter_title = title_match.group(1).strip()
                            # Remove existing numbering and clean the title
                            clean_title = re.sub(r'^[\d.]+\s*', '', chapter_title)
                            # Remove escaped parentheses and other markdown escapes
                            clean_title = clean_title.replace('\\(', '(').replace('\\)', ')').replace('\\', '')
                            # Create clean folder name preserving the full meaningful title
                            clean_folder_name = clean_title.lower().replace(' ', '_').replace('/', '_').replace(',', '').replace('(', '').replace(')', '').replace('.', '').replace(':', '').replace('-', '_')
                            # Remove multiple underscores and trim
                            clean_folder_name = re.sub(r'_+', '_', clean_folder_name).strip('_')
                            # Update folder mapping with proper title
                            chapter_num = info['numbering']
                            self.folder_mappings[original_folder] = f"{chapter_num}_{clean_folder_name}"
                    except Exception as e:
                        print(f"  Warning: Could not read chapter title from {index_path}: {e}")

        # Now rename the folders with the updated meaningful names
        self.rename_folders_with_titles()

    def update_files_and_build_toc(self):
        """Update all markdown files with numbering, rename them, and build TOC"""
        print(f"\nUpdating {len(self.file_mappings)} files with hierarchical numbering...")

        # Process all files with current folder mappings
        for original_path, info in self.file_mappings.items():
            numbering = info['numbering']
            subdirectory = info['subdirectory']
            original_folder = info.get('original_folder', '.')

            # Use new folder name if it was renamed
            if original_folder in self.folder_mappings:
                subdirectory = self.folder_mappings[original_folder]

            # Construct full path to the markdown file
            if subdirectory != '.':
                full_path = self.output_dir / subdirectory / Path(original_path).name
            else:
                full_path = self.output_dir / original_path

            if full_path.exists():
                # Read file content
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Fix image paths if folder was renamed
                    if original_folder in self.folder_mappings and original_folder != '.':
                        # Replace old folder name with just 'img/' in image paths
                        # Pattern: ./original_folder/img/ -> ./img/
                        old_pattern = f"./{original_folder}/img/"
                        new_pattern = "./img/"
                        content = content.replace(old_pattern, new_pattern)

                        # Also handle ../original_folder/img/ -> ./img/
                        old_pattern = f"../{original_folder}/img/"
                        content = content.replace(old_pattern, new_pattern)

                    # Fix MDX-specific issues to ensure Docusaurus compatibility
                    content = self.fix_mdx_issues(content)

                    # Update title with numbering
                    title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
                    if title_match:
                        current_title = title_match.group(1).strip()
                        # Remove existing numbering if present
                        clean_title = re.sub(r'^[\d.]+\s*', '', current_title)
                        # Remove escaped parentheses and other markdown escapes
                        clean_title = clean_title.replace('\\(', '(').replace('\\)', ')').replace('\\', '')
                        # Add dot after chapter number for main chapters (e.g. "1. Title" not "1.1 Title")
                        if '.' not in numbering:
                            new_title = f"{numbering}. {clean_title}"
                        else:
                            new_title = f"{numbering} {clean_title}"

                        content = re.sub(
                            r'^# .+$',
                            f'# {new_title}',
                            content,
                            count=1,
                            flags=re.MULTILINE
                        )

                        # Write back to file
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(content)

                        # Create new filename with numbering (clean, no padding)
                        clean_name = re.sub(r'[^\w\s-]', '', clean_title)
                        clean_name = re.sub(r'\s+', '_', clean_name)
                        # Use underscores for all numbering
                        number_prefix = numbering.replace('.', '_')
                        new_name = f"{number_prefix}_{clean_name}.md"

                        new_path = full_path.parent / new_name

                        # Rename file
                        if full_path != new_path:
                            print(f"  {full_path.name} -> {new_name}")
                            full_path.rename(new_path)

                        # Add to TOC with proper title and new path
                        rel_path = new_path.relative_to(self.output_dir)
                        self.toc_structure.append({
                            'numbering': numbering,
                            'title': clean_title,  # Use clean title without numbering
                            'file_path': rel_path,
                            'level': numbering.count('.')
                        })

                except Exception as e:
                    print(f"  Error processing {full_path}: {e}")
            else:
                print(f"  Warning: File not found: {full_path}")

    def generate_folder_indexes(self):
        """Generate index.md for each folder listing its contents"""
        print("\nGenerating folder indexes...")

        # Group files by folder
        folder_contents = {}
        for entry in self.toc_structure:
            file_path = entry['file_path']
            folder = file_path.parent
            if folder not in folder_contents:
                folder_contents[folder] = []
            folder_contents[folder].append(entry)

        # Generate index for each folder
        for folder_path, entries in folder_contents.items():
            # Skip if it's the root (.) folder
            if str(folder_path) == '.':
                continue

            folder_full_path = self.output_dir / folder_path
            index_path = folder_full_path / 'index.md'

            # Sort entries by numbering
            sorted_entries = sorted(entries, key=lambda x: [int(n) for n in x['numbering'].split('.')])

            # Find the main chapter file (just a single number, e.g., "1", "2", "3")
            main_chapter = None
            sub_sections = []

            for entry in sorted_entries:
                numbering = entry['numbering']
                # Check if this is the main chapter (e.g., just "1", "2", etc.)
                if re.match(r'^\d+$', numbering):
                    main_chapter = entry
                else:
                    sub_sections.append(entry)

            # If we have a main chapter file, read its content
            if main_chapter:
                main_file_path = folder_full_path / main_chapter['file_path'].name
                if main_file_path.exists():
                    with open(main_file_path, 'r', encoding='utf-8') as f:
                        main_content = f.read()

                    # Remove ONLY the DITA-OT generated TOC bullet list
                    # This targets a specific pattern: consecutive lines right after the title
                    # that are bullet points with bold links to ../something/*.md files
                    # Pattern: starts after title, has consecutive "- **[text](../path/file.md)**" lines
                    main_content = re.sub(
                        r'(^# [^\n]+\n\n?)((?:^-\s+\*\*\[[^\]]+\]\(\.\./[^\)]+\.md\)\*\*\s*\n)+)',
                        r'\1',
                        main_content,
                        flags=re.MULTILINE
                    )

                    # Remove the main chapter file since its content will be in index
                    main_file_path.unlink()
                    print(f"  Merged {main_chapter['file_path'].name} into index.md")
            else:
                # No main chapter file, use folder name for title
                folder_name = folder_path.name
                clean_folder_name = re.sub(r'^\d+_', '', folder_name)
                title = clean_folder_name.replace('_', ' ').title()
                main_content = f"# {title}\n\n"

            # Build the index with main content + TOC
            index_lines = [main_content.strip()]

            # Add TOC if there are sub-sections
            if sub_sections:
                index_lines.append("\n## Table of Contents\n")

                for entry in sub_sections:
                    numbering = entry['numbering']
                    file_title = entry['title']
                    file_name = entry['file_path'].name
                    # Remove .md extension for links
                    link_name = file_name.replace('.md', '')

                    # Use proper indentation for nested levels
                    level = numbering.count('.')
                    if level == 1:  # x.x pattern (e.g., 1.1, 1.2)
                        index_lines.append(f"- [{numbering} {file_title}]({link_name})")
                    elif level == 2:  # x.x.x pattern (e.g., 1.3.1, 1.3.2)
                        index_lines.append(f"  - [{numbering} {file_title}]({link_name})")

            # Write the folder index
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(index_lines))

            print(f"  Generated index for {folder_path} with main content and {len(sub_sections)} sub-sections")

    def generate_root_index(self):
        """Generate root index.md with proper nested table of contents"""
        print("\nGenerating root index with nested TOC...")

        index_path = self.output_dir / 'index.md'

        # Build root index with nested TOC
        # Use the extracted book title or default to a generic title
        title = self.book_title if self.book_title else "Documentation Guide"
        toc_lines = [f"# {title}", ""]

        # Group entries by chapter and build nested structure
        chapters = {}
        for entry in sorted(self.toc_structure, key=lambda x: [int(n) for n in x['numbering'].split('.')]):
            numbering_parts = entry['numbering'].split('.')
            chapter_num = numbering_parts[0]

            if chapter_num not in chapters:
                chapters[chapter_num] = {
                    'main': None,
                    'sections': [],
                    'folder_path': None
                }

            # Store folder path for linking
            if entry['file_path'].parent != Path('.'):
                chapters[chapter_num]['folder_path'] = entry['file_path'].parent

            if len(numbering_parts) == 1:
                # This is a main chapter file
                chapters[chapter_num]['main'] = entry
            else:
                # This is a section
                chapters[chapter_num]['sections'].append(entry)

        # Add table of contents header
        toc_lines.append("## Table of Contents")
        toc_lines.append("")

        # Generate nested TOC
        for chapter_num in sorted(chapters.keys(), key=int):
            chapter_info = chapters[chapter_num]

            # Get chapter title
            if chapter_info['main']:
                chapter_title = chapter_info['main']['title']
            else:
                # Fallback to folder name if no main file
                if chapter_info['folder_path']:
                    folder_name = chapter_info['folder_path'].name
                    chapter_title = re.sub(r'^\d+_', '', folder_name).replace('_', ' ').title()
                else:
                    chapter_title = f"Chapter {chapter_num}"

            # Add chapter link - use the actual current folder name
            if chapter_info['folder_path']:
                # Get the actual current folder name after renaming
                original_folder_name = str(chapter_info['folder_path'])
                # Look for the current folder that starts with the chapter number
                current_folders = [d for d in self.output_dir.iterdir() if d.is_dir() and d.name.startswith(f"{chapter_num}_")]
                if current_folders:
                    current_folder_name = current_folders[0].name
                    # Keep numeric prefix for Docusaurus URL (with numberPrefixParser: false)
                    # e.g., "1_overview" stays as "1_overview" in the URL
                    docusaurus_folder_name = current_folder_name
                else:
                    # Fallback to original if not found
                    current_folder_name = original_folder_name
                    docusaurus_folder_name = current_folder_name

                toc_lines.append(f"### [Chapter {chapter_num}: {chapter_title}]({docusaurus_folder_name}/)")
                toc_lines.append("")
            else:
                # Check if there's a standalone file for this chapter
                chapter_files = [f for f in self.output_dir.iterdir() if f.is_file() and f.name.startswith(f"{chapter_num}_") and f.name.endswith('.md')]
                if chapter_files:
                    # This is a standalone file chapter
                    chapter_file = chapter_files[0]
                    toc_lines.append(f"### [Chapter {chapter_num}: {chapter_title}]({chapter_file.name})")
                    toc_lines.append("")
                else:
                    # No folder and no file - just a plain heading
                    toc_lines.append(f"### Chapter {chapter_num}: {chapter_title}")
                    toc_lines.append("")

            # Add sections as nested list
            if chapter_info['sections']:
                # Group sections by level
                current_parent = None
                for section in chapter_info['sections']:
                    numbering = section['numbering']
                    title = section['title']
                    file_path = section['file_path']
                    level = numbering.count('.')

                    # Build the link path - use actual current folder name
                    if chapter_info['folder_path']:
                        # Get the actual current folder name after renaming
                        current_folders = [d for d in self.output_dir.iterdir() if d.is_dir() and d.name.startswith(f"{chapter_num}_")]
                        if current_folders:
                            current_folder_name = current_folders[0].name
                            # Keep numeric prefix for Docusaurus URL (with numberPrefixParser: false)
                            docusaurus_folder_name = current_folder_name
                            link_path = f"{docusaurus_folder_name}/{file_path.name}"
                        else:
                            link_path = f"{chapter_info['folder_path']}/{file_path.name}"
                    else:
                        link_path = str(file_path)

                    # Remove .md extension for cleaner links
                    link_path = link_path.replace('.md', '')

                    if level == 1:  # Direct section (e.g., 1.1, 1.2)
                        toc_lines.append(f"- {numbering} [{title}]({link_path})")
                        current_parent = numbering
                    elif level == 2:  # Sub-section (e.g., 1.1.1, 1.1.2)
                        toc_lines.append(f"  - {numbering} [{title}]({link_path})")
                    elif level == 3:  # Sub-sub-section (e.g., 1.1.1.1)
                        toc_lines.append(f"    - {numbering} [{title}]({link_path})")

                toc_lines.append("")  # Add spacing after sections

        # Write the index
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(toc_lines))

        print(f"  Root index generated with nested TOC for {len(chapters)} chapters")

    def fix_internal_links(self):
        """Fix internal markdown links to use the new numbered filenames"""
        print("\nSkipping internal markdown links fixing...")
        return

        # Build a mapping from old filename (without extension) to new filename (without extension)
        link_mappings = {}

        # Build mappings from the file_mappings which has all the original->new information
        for original_path, info in self.file_mappings.items():
            original_filename = Path(original_path).name.replace('.md', '')
            numbering = info['numbering']

            # Find the corresponding entry in TOC structure to get the new name
            for entry in self.toc_structure:
                if entry['numbering'] == numbering:
                    new_filename = entry['file_path'].name.replace('.md', '')
                    link_mappings[original_filename] = new_filename
                    break

        # Also add folder mappings for folder-relative links
        folder_link_mappings = {}
        for original_folder, new_folder in self.folder_mappings.items():
            folder_link_mappings[original_folder] = new_folder

        # Add special mappings for folder index files
        # When a link points to "periodic.md", it should point to the folder's index
        folder_index_mappings = {}
        for original_folder, new_folder in self.folder_mappings.items():
            folder_index_mappings[original_folder] = new_folder

        print(f"  Found {len(folder_index_mappings)} folder index mappings")
        print(f"  Folder index mappings: {list(folder_index_mappings.keys())}")

        print(f"  Found {len(link_mappings)} file link mappings")
        print(f"  Found {len(folder_link_mappings)} folder link mappings")

        # Now process all markdown files and update their internal links
        files_updated = 0

        # Process all markdown files in the output directory, not just those in toc_structure
        all_md_files = list(self.output_dir.rglob('*.md'))
        for file_path in all_md_files:
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    original_content = content

                    # Fix markdown links: [text](filename.md) -> [text](new_filename.md)
                    # Pattern: [text](path/to/file.md) or [text](file.md)
                    import re

                    def replace_link(match):
                        full_match = match.group(0)
                        link_text = match.group(1)
                        link_path = match.group(2)

                        # Extract fragment if present (e.g., .md# or .md#section)
                        fragment = ""
                        if '#' in link_path:
                            link_path, fragment = link_path.split('#', 1)
                            fragment = '#' + fragment

                        # Handle different link patterns
                        if '/' in link_path:
                            # Folder/file link like "repgen/add_operation_errors.md"
                            folder_part, file_part = link_path.rsplit('/', 1)
                            file_without_ext = file_part.replace('.md', '')

                            # Check if we have a mapping for this file
                            if file_without_ext in link_mappings:
                                new_file_name = link_mappings[file_without_ext]
                                # Check if folder needs updating too
                                if folder_part in folder_link_mappings:
                                    new_folder = folder_link_mappings[folder_part]
                                    new_link = f"[{link_text}]({new_folder}/{new_file_name}.md{fragment})"
                                else:
                                    new_link = f"[{link_text}]({folder_part}/{new_file_name}.md{fragment})"
                                return new_link
                        else:
                            # Simple file link like "file.md"
                            file_without_ext = link_path.replace('.md', '')

                            # Check if this is a folder index file (like "periodic.md" -> folder index)
                            if file_without_ext in folder_index_mappings:
                                # This links to a folder's index - determine relative path
                                current_file_path = relative_path

                                if current_file_path.parent.name.startswith(folder_index_mappings[file_without_ext].split('_')[0] + '_'):
                                    # We're inside the target folder, link to parent's index
                                    new_link = f"[{link_text}](../{fragment})" if fragment else f"[{link_text}](../)"
                                else:
                                    # We're outside, link to folder index
                                    new_folder = folder_index_mappings[file_without_ext]
                                    new_link = f"[{link_text}]({new_folder}/{fragment})" if fragment else f"[{link_text}]({new_folder}/)"
                                return new_link

                            # Regular file mapping
                            if file_without_ext in link_mappings:
                                new_file_name = link_mappings[file_without_ext]
                                new_link = f"[{link_text}]({new_file_name}.md{fragment})"
                                return new_link

                        # No mapping found, return original
                        return full_match

                    # Apply the link replacement (handle fragments like .md# and .md#section)
                    relative_path = file_path.relative_to(self.output_dir)
                    content = re.sub(r'\[([^\]]+)\]\(([^)]+\.md[^)]*)\)', replace_link, content)

                    # Write back if content changed
                    if content != original_content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        files_updated += 1
                        print(f"  Updated links in: {relative_path}")

                except Exception as e:
                    print(f"  Error updating links in {file_path}: {e}")

        print(f"  Updated internal links in {files_updated} files")

    def fix_mdx_issues(self, content):
        """Fix MDX-specific issues for Docusaurus compatibility"""
        import re

        # 1. Fix unclosed angle brackets in tables and text
        # Look for patterns like "enclosed in <>" or "use <placeholder>"
        content = re.sub(r'\bin\s+<>', 'in &lt;&gt;', content)
        content = re.sub(r'enclosed in <>', 'enclosed in &lt;&gt;', content)

        # 2. Fix SQL placeholders in code blocks
        # In code blocks, replace <PLACEHOLDER> with [PLACEHOLDER]
        def fix_sql_placeholders(match):
            lang = match.group(1) if match.group(1) else ''
            code = match.group(2)
            # Replace angle brackets with square brackets in SQL placeholders
            code = re.sub(r'<([A-Z_]+)>', r'[\1]', code)
            return f"```{lang}{code}```"

        # Process code blocks (with optional language specifier)
        content = re.sub(r'```(\w*\n)?(.*?)```', fix_sql_placeholders, content, flags=re.DOTALL)

        # 3. Fix DATABASE::, SCHEMA::, TABLE:: patterns outside code blocks
        patterns = [
            # Fix DATABASE::<database name> type patterns
            (r'(DATABASE::|SCHEMA::|TABLE::)\s*<([^>]+)>', r'\1[\2]'),
            # Fix <br/> tags - remove them
            (r'<br\s*/?>', ' '),
            # Fix backtick surrounded br tags
            (r'`<br\s*/?>`', ' '),
            # Fix <= and >= that might be parsed as tags
            (r'(?<!")<=(?!")', '&lt;='),
            (r'(?<!")>=(?!")', '&gt;='),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        # 4. Escape unmatched angle brackets that aren't valid HTML tags
        def escape_angle_brackets(match):
            tag = match.group(0)
            # List of valid HTML/MDX tags to preserve
            valid_tags = [
                'p', 'div', 'span', 'a', 'img', 'br', 'hr', 'code', 'pre',
                'table', 'tr', 'td', 'th', 'thead', 'tbody', 'strong', 'em',
                'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'blockquote', 'section', 'article', 'header', 'footer', 'b', 'i',
                'sup', 'sub', 'cite', 'details', 'summary', 'time', 'mark'
            ]

            # Extract tag name
            tag_content = tag[1:-1].strip()
            if tag_content.startswith('/'):
                tag_name = tag_content[1:].split()[0].lower()
            else:
                tag_name = tag_content.split()[0].lower()

            # Check if it's a valid tag
            if tag_name in valid_tags:
                return tag
            else:
                # Escape the angle brackets
                return tag.replace('<', '&lt;').replace('>', '&gt;')

        # Match opening and closing tags but not inside code blocks
        lines = content.split('\n')
        in_code_block = False
        processed_lines = []

        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                processed_lines.append(line)
            elif not in_code_block:
                # Only process tags outside of code blocks
                line = re.sub(r'</?[a-zA-Z_][^>]*>', escape_angle_brackets, line)
                processed_lines.append(line)
            else:
                processed_lines.append(line)

        content = '\n'.join(processed_lines)

        return content

    def process(self):
        """Main processing function"""
        print(f"Processing hierarchical structure from {self.ditamap_path}")

        # Parse the bookmap structure
        if not self.parse_bookmap():
            return False

        # Rename folders first
        self.rename_folders()

        # Update files with numbering and build TOC
        self.update_files_and_build_toc()

        # Generate folder indexes (this creates the index.md files we need)
        self.generate_folder_indexes()

        # Extract titles from generated index.md files and rename folders with meaningful names
        self.extract_titles_and_rename_folders()

        # Generate root index
        self.generate_root_index()

        # Fix internal markdown links to use new numbered filenames
        self.fix_internal_links()

        # Copy and organize images after folder renaming
        self.organize_all_images()

        print("\nHierarchical processing complete!")
        return True

    def organize_all_images(self):
        """Ensure all images are in the correct img/ subdirectories after folder renaming"""
        print("\nOrganizing images in renamed folders...")

        img_extensions = {'.png', '.PNG', '.jpg', '.JPG', '.jpeg', '.gif', '.svg', '.webp'}
        images_moved = 0

        # Process each renamed folder
        for folder in self.output_dir.iterdir():
            if not folder.is_dir():
                continue

            # Look for any image files that might need organizing
            images_to_move = []

            # Check for images in the folder root that should be in img/
            for item in folder.iterdir():
                if item.is_file() and item.suffix in img_extensions:
                    images_to_move.append((item, folder / 'img' / item.name))

            # Also check for images in subdirectories that aren't 'img'
            for subdir in folder.iterdir():
                if subdir.is_dir() and subdir.name != 'img':
                    for item in subdir.rglob('*'):
                        if item.is_file() and item.suffix in img_extensions:
                            # Move to folder/img/ preserving some path structure
                            dest = folder / 'img' / item.name
                            images_to_move.append((item, dest))

            # Move images if needed
            if images_to_move:
                img_dir = folder / 'img'
                img_dir.mkdir(exist_ok=True)

                for src, dest in images_to_move:
                    if not dest.exists():
                        print(f"  Moving {src.relative_to(self.output_dir)} -> {dest.relative_to(self.output_dir)}")
                        src.rename(dest)
                        images_moved += 1

        if images_moved > 0:
            print(f"  Moved {images_moved} images to proper img/ directories")
        else:
            print(f"  All images are already properly organized")


def main():
    parser = argparse.ArgumentParser(description='Process DITA output with hierarchical numbering')
    parser.add_argument('output_dir', help='Output directory with converted markdown files')
    parser.add_argument('ditamap', help='Path to main DITAMAP/bookmap file')

    args = parser.parse_args()

    processor = HierarchicalProcessor(args.output_dir, args.ditamap)
    processor.process()


if __name__ == '__main__':
    main()