#!/usr/bin/env python3
"""
Unified DITA to Markdown converter pipeline.
Handles the complete conversion process in the correct order.
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path
import re

class DitaConverter:
    def __init__(self, input_dir, output_dir, verbose=False):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        self.dita_ot_dir = Path("dita-ot-4.2.3")
        self.dita_cmd = self.dita_ot_dir / "bin" / "dita"

    def log(self, message, level="INFO"):
        """Print log messages"""
        if self.verbose or level == "ERROR":
            color = {"INFO": "\033[0;34m", "SUCCESS": "\033[0;32m", "ERROR": "\033[0;31m"}.get(level, "")
            reset = "\033[0m"
            print(f"{color}[{level}] {message}{reset}")

    def run_command(self, cmd, description=""):
        """Run shell command and capture output"""
        if description:
            self.log(description)

        if self.verbose:
            self.log(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}", "INFO")

        try:
            result = subprocess.run(
                cmd,
                shell=isinstance(cmd, str),
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e.stderr}", "ERROR")
            return None

    def fix_dita_paths(self):
        """Fix path references in DITA files"""
        self.log("Fixing DITA path references...")

        # Fix all ../src/ and ../ references in DITA files
        for pattern in ['*.dita', '*.ditamap']:
            for file_path in self.input_dir.rglob(pattern):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Fix path references
                new_content = re.sub(r'href="\.\./(src/)?', 'href="', content)
                new_content = re.sub(r'file://[^"]*?/src/', 'file://', new_content)

                if new_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    if self.verbose:
                        self.log(f"Fixed paths in: {file_path.relative_to(self.input_dir)}")

    def find_or_generate_ditamap(self):
        """Find existing ditamap or generate one"""
        # Look for existing ditamap
        ditamaps = list(self.input_dir.glob("*.ditamap"))

        if ditamaps:
            self.log(f"Found existing DITAMAP: {ditamaps[0].name}")
            return ditamaps[0]

        # Generate ditamap if none exists
        self.log("No DITAMAP found, generating one...")
        generated_ditamap = self.input_dir / "generated.ditamap"

        # Import and use the generate_ditamap function
        sys.path.insert(0, str(Path(__file__).parent))
        from generate_ditamap import generate_ditamap

        if generate_ditamap(str(self.input_dir), str(generated_ditamap)):
            return generated_ditamap
        else:
            self.log("Failed to generate DITAMAP", "ERROR")
            return None

    def run_dita_ot(self, ditamap_path):
        """Run DITA-OT conversion"""
        self.log("Running DITA-OT conversion...")

        # Check if DITA-OT is installed
        if not self.dita_ot_dir.exists():
            self.log("DITA-OT not installed. Run 'make install' first", "ERROR")
            return False

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Run DITA-OT
        cmd = [
            str(self.dita_cmd),
            "-i", str(ditamap_path),
            "-f", "markdown_github",
            "-o", str(self.output_dir)
        ]

        result = self.run_command(cmd, "Converting DITA to Markdown...")

        # Copy images
        self.log("Copying images...")
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg']:
            for img in self.input_dir.rglob(ext):
                rel_path = img.relative_to(self.input_dir)
                dest = self.output_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(img, dest)

        return result is not None

    def run_docusaurus_postprocessor(self):
        """Run Docusaurus post-processor on all markdown files"""
        self.log("Running Docusaurus post-processor...")

        # Import the postprocessor
        sys.path.insert(0, str(Path(__file__).parent))
        from docusaurus_postprocess import convert_to_docusaurus

        processed = 0
        for md_file in self.output_dir.rglob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Apply Docusaurus conversions
                new_content = convert_to_docusaurus(content)

                if new_content != content:
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    processed += 1
                    if self.verbose:
                        self.log(f"Processed: {md_file.relative_to(self.output_dir)}")
            except Exception as e:
                self.log(f"Error processing {md_file}: {e}", "ERROR")

        self.log(f"Processed {processed} files")
        return True

    def run_hierarchical_processor(self, ditamap_path):
        """Run hierarchical processor for numbering and organization"""
        self.log("Running hierarchical processor...")

        # Import and run the hierarchical processor
        sys.path.insert(0, str(Path(__file__).parent))
        from hierarchical_processor import HierarchicalProcessor

        processor = HierarchicalProcessor(str(self.output_dir), str(ditamap_path))
        processor.process()

        return True

    def convert(self, docusaurus=True, hierarchical=True):
        """Run the complete conversion pipeline"""
        self.log(f"Starting DITA to Markdown conversion")
        self.log(f"Input: {self.input_dir}")
        self.log(f"Output: {self.output_dir}")

        # Step 0: Fix DITA paths
        self.fix_dita_paths()

        # Step 1: Find or generate DITAMAP
        ditamap_path = self.find_or_generate_ditamap()
        if not ditamap_path:
            return False

        # Step 2: Run DITA-OT conversion
        if not self.run_dita_ot(ditamap_path):
            return False

        # Step 3: Run Docusaurus post-processor (if enabled)
        if docusaurus:
            if not self.run_docusaurus_postprocessor():
                return False

        # Step 4: Run hierarchical processor (if enabled)
        if hierarchical:
            if not self.run_hierarchical_processor(ditamap_path):
                return False

        # Clean up generated ditamap if we created one
        generated_ditamap = self.input_dir / "generated.ditamap"
        if generated_ditamap.exists():
            generated_ditamap.unlink()
            self.log("Cleaned up generated DITAMAP")

        self.log("Conversion complete!", "SUCCESS")
        return True

def main():
    parser = argparse.ArgumentParser(
        description='Unified DITA to Markdown converter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Convert input/ to output/ with all features
  %(prog)s -i docs -o markdown  # Convert docs/ to markdown/
  %(prog)s --no-docusaurus      # Skip Docusaurus formatting
  %(prog)s --no-hierarchical    # Skip hierarchical numbering
  %(prog)s -v                   # Verbose output
        """
    )

    parser.add_argument('-i', '--input',
                        default='input',
                        help='Input directory containing DITA files (default: input)')

    parser.add_argument('-o', '--output',
                        default='output',
                        help='Output directory for Markdown files (default: output)')

    parser.add_argument('-d', '--no-docusaurus',
                        action='store_true',
                        help='Skip Docusaurus post-processing')

    parser.add_argument('-n', '--no-hierarchical',
                        action='store_true',
                        help='Skip hierarchical numbering')

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Verbose output')

    parser.add_argument('-c', '--clean',
                        action='store_true',
                        help='Clean output directory before conversion')

    args = parser.parse_args()

    # Validate input directory
    if not Path(args.input).exists():
        print(f"Error: Input directory '{args.input}' does not exist")
        return 1

    # Clean output directory if requested
    if args.clean and Path(args.output).exists():
        print(f"Cleaning output directory: {args.output}")
        shutil.rmtree(args.output)

    # Run conversion
    converter = DitaConverter(args.input, args.output, verbose=args.verbose)
    success = converter.convert(
        docusaurus=not args.no_docusaurus,
        hierarchical=not args.no_hierarchical
    )

    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())