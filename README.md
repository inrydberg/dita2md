# DITA to Markdown Converter

A comprehensive toolset for converting DITA XML documentation to Markdown format, with special support for Docusaurus-compatible output.

## Features

- **DITA-OT 4.2.3 integration**: Professional-grade DITA processing with full specification support
- **Docusaurus support**: Automatic conversion of DITA notes to Docusaurus admonitions
- **Hierarchical processing**: Organize files for Docusaurus sidebar compatibility
- **MDX compatibility fixes**: Automatic escaping and formatting for Docusaurus compilation
- **Table conversion**: HTML tables to clean Markdown tables with list support
- **HTML entity handling**: Converts ``<arg>`` to `` `<arg>` `` for better readability
- **Batch processing**: Convert single files, entire DITA maps, or batch process folders
- **Image organization**: Automatic organization into proper `img/` subdirectories

## How It Works

The converter uses a multi-stage pipeline:

1. **DITA-OT Processing**: Industry-standard DITA-OT 4.2.3 converts DITA to GitHub-flavored Markdown
2. **Docusaurus Post-processing**: Custom script converts DITA notes to Docusaurus admonitions and fixes MDX issues
3. **Hierarchical Processing**: Optional step to organize files with numeric prefixes for Docusaurus sidebar
4. **MDX Fixes**: Automatic escaping of problematic characters and patterns for Docusaurus compatibility
5. **Image Organization**: Moves images to proper directories after file reorganization

## Installation

### Prerequisites

- Python 3.6+
- curl (for downloading DITA-OT)
- make

### Setup

1. Install DITA-OT (required for full functionality):
```bash
make install
```

This downloads and installs DITA-OT 4.2.3 locally.

## Usage

### Quick Start

#### Batch Processing (Recommended)
Place your DITA files in the `input/` folder and run:
```bash
make batch                    # Process all files in input/ folder
make convert-docusaurus       # Same as batch if no INPUT specified
```

**Optimization**: If no DITAMAP exists, the converter automatically generates one for efficient batch processing (single DITA-OT invocation instead of multiple).

Results will be in the `output/` folder.

#### Single File Processing
Convert a single DITA file to Docusaurus-compatible Markdown:
```bash
make convert-docusaurus INPUT=../examples/add_proxy.dita
```

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `make install` | Install DITA-OT | `make install` |
| `make batch` | Process all DITA files in input/ folder | `make batch` |
| `make convert` | Auto-detect and convert with DITA-OT | `make convert INPUT=file.dita` |
| `make convert-ot` | Use DITA-OT only (no post-processing) | `make convert-ot INPUT=file.dita FORMAT=markdown_github` |
| `make convert-docusaurus` | DITA-OT + Docusaurus post-processing (recommended) | `make convert-docusaurus INPUT=map.ditamap` |
| `make clean` | Remove generated output | `make clean` |
| `make uninstall` | Remove DITA-OT installation | `make uninstall` |

### Direct Script Usage

For direct conversion script usage:
```bash
# Using the main converter script
python3 convert.py -i input -o output -v

# With hierarchical processing
python3 hierarchical_processor.py output/
```

### Post-Processing Features

The `docusaurus_postprocess.py` script automatically:

1. **Converts DITA notes to Docusaurus admonitions**:
   - DITA note → `:::note`
   - DITA tip → `:::tip`
   - DITA info → `:::info`
   - DITA important → `:::warning`
   - DITA warning → `:::warning`
   - DITA caution/danger → `:::danger`

2. **Converts HTML tables to Markdown**:
   - Preserves table structure
   - Handles lists in cells using `<br/>` tags
   - Maintains cell content formatting

3. **Fixes HTML entities**:
   - ``<arg>`` → `` `<arg>` ``
   - Preserves readability while maintaining MDX compatibility

## Examples

### Convert a Single File
```bash
# Using DITA-OT with Docusaurus post-processing
make convert-docusaurus INPUT=../examples/add_proxy.dita

# Direct conversion without post-processing
make convert-ot INPUT=../examples/add_proxy.dita
```

### Convert a DITA Map
```bash
# Convert entire documentation set
make convert-docusaurus INPUT=/path/to/documentation.ditamap
```

### Batch Processing
```bash
# Process entire documentation set from input/ folder
make batch
```

## Converter Capabilities and Limitations

### What the Converter CAN Do Well ✅

#### Core Conversion Features
- **DITA to Markdown conversion** with full DITA-OT 4.2.3 support
- **Hierarchical file organization** for Docusaurus sidebar compatibility
- **Batch processing** of entire documentation sets via DITAMAP
- **Automatic MDX compatibility fixes** for Docusaurus compilation
- **Image organization** into proper `img/` subdirectories

#### Specific Element Handling
- **All 7 DITA note types** converted to appropriate Docusaurus admonitions
- **Complex tables** with proper Markdown formatting
- **Code blocks** with language syntax preservation
- **Lists and nested lists** with correct numbering
- **Inline formatting** (`<b>`, `<i>`, `<codeph>`, `<uicontrol>`)
- **External links** with proper `scope="external"` attributes

#### MDX/Docusaurus Fixes
- Escapes unclosed angle brackets (`<>` → `&lt;&gt;`)
- Fixes SQL placeholders (`<PLACEHOLDER>` → `[PLACEHOLDER]`)
- Handles database patterns (`DATABASE::`, `SCHEMA::`, `TABLE::`)
- Smart HTML tag detection to avoid over-escaping

### Known Limitations and Caveats ⚠️

#### Image Path Issues
- **Some edge cases may fail** despite image organization logic
- Complex relative paths across multiple directory levels may break
- Non-standard image references might not be detected
- **Recommendation**: Manually verify critical images after conversion

#### Angle Bracket Handling
- **Regex-based detection has limits** due to the sheer variety of possible cases
- Some valid HTML might get incorrectly escaped
- Some unclosed brackets might be missed
- Edge cases in code blocks may behave unexpectedly
- **Recommendation**: Review MDX compilation errors and fix manually if needed

#### Internal Link Handling (Currently Disabled)
- **Internal link rewriting is DISABLED** due to complexity
- Cross-references between documents remain as-is from DITA
- Links may break after hierarchical file renaming
- **Why it's complex**:
  - Multiple link formats (relative, absolute, anchored)
  - Hierarchical numbering changes all file paths
  - Cross-guide references need special handling
  - DITA keyref resolution adds another layer
- **Recommendation**: Use a semi-manual or script-assisted approach for critical links

#### Other Limitations
- **Definition lists** (`<dl>`, `<dt>`, `<dd>`) not fully supported
- **Content references** (conref) may not resolve in all cases
- **Specialized DITA domains** might not convert perfectly
- **Large files** (>1000 lines) may have performance issues
- **Custom DITA specializations** require manual configuration

### Recommended Workflow

1. **Run the converter** with hierarchical processing
2. **Check MDX compilation** in Docusaurus for errors
3. **Manually fix**:
   - Critical broken images
   - Important internal links
   - Any MDX compilation errors
4. **Use scripts** for bulk link updates if needed
5. **Test thoroughly** in your target environment

### When to Use Manual Intervention

- **Complex cross-guide navigation** - Better handled with custom scripts
- **Critical image assets** - Verify paths manually
- **Important internal links** - Update after understanding new structure
- **Custom formatting needs** - Add post-processing steps
- **Validation errors** - Fix case-by-case based on MDX compiler feedback

## Output

By default, converted files are placed in `output/` directory. You can specify a custom output directory:

```bash
make convert-docusaurus INPUT=file.dita OUTPUT=custom-output
```

## Docusaurus Admonition Types

Docusaurus supports exactly 5 admonition types (as per [official documentation](https://docusaurus.io/docs/markdown-features/admonitions)):

- `:::note` - General notes and information
- `:::tip` - Helpful tips and best practices  
- `:::info` - Informational content
- `:::warning` - Important warnings and cautions
- `:::danger` - Critical warnings and dangerous operations



:::note

Docusaurus does NOT have `:::caution` or `:::important`. These DITA note types are mapped as follows:
- DITA `<note type="caution">` → `:::danger`
- DITA `<note type="important">` → `:::warning`

:::

## File Structure

```
dita2md/
├── Makefile                    # Build automation
├── convert.py                  # Main conversion entry point
├── docusaurus_postprocess.py   # Post-processor for Docusaurus
├── generate_ditamap.py         # Auto-generates DITAMAP for batch processing
├── hierarchical_processor.py   # Organizes converted output for Docusaurus
├── todo.txt                    # Future improvements
├── README.md                   # This file
├── input/                      # Place DITA files here for batch processing
└── output/                     # Default output directory (gitignored)
```

## DITA Elements Support

### Document Types
- `<concept>` - Conceptual documentation
- `<task>` - Step-by-step procedures
- `<reference>` - Reference documentation

### Block Elements
- `<p>` - Paragraphs
- `<section>` - Sections with titles
- `<ul>`, `<ol>` - Unordered and ordered lists
- `<table>` - Tables with headers and descriptions
- `<codeblock>` - Code blocks with language detection
- `<note>` - Notes, warnings, tips, important notices
- `<image>` - Images with alt text

### Inline Elements
- `<uicontrol>` - UI control names → `code`
- `<cmdname>` - Command names → `code`
- `<codeph>` - Code phrases → `code`
- `<b>`, `<bold>` - Bold text → `**bold**`
- `<i>`, `<italic>` - Italic text → `*italic*`
- `<xref>` - Cross-references → `[text](link)`

## Performance Optimization

### Batch Processing Performance
DITA-OT has significant JVM startup overhead (~5-10 seconds per invocation). To optimize batch processing:

1. **Always use DITAMAPs** - Processes all files in a single DITA-OT invocation
2. **Auto-generation** - If no DITAMAP exists, one is automatically generated
3. **Result**: ~20-30 seconds for entire documentation sets vs 10+ seconds per file

### Example Performance (7 DITA files)
- With DITAMAP: ~22 seconds total
- Without optimization: ~70+ seconds (10s per file)

## Limitations

- Complex nested structures in tables may be simplified
- Some DITA specializations may need custom handling
- Cross-references to other DITA files need manual adjustment

## Advanced Features

### Hierarchical Document Processing

The converter includes sophisticated hierarchical processing for DITA maps:

1. **Automatic Chapter Numbering**: Files and folders are numbered based on their position in the DITAMAP
2. **Intelligent Folder Naming**: Extracts meaningful titles from content instead of generic names
3. **Nested TOC Generation**: Creates hierarchical table of contents with proper nesting
4. **Docusaurus URL Compatibility**: Handles Docusaurus's automatic stripping of numeric prefixes from URLs

### MDX Compatibility

Full support for MDX (Markdown + JSX) used by Docusaurus:

1. **Angle Bracket Escaping**: Automatically escapes patterns like `<arg>`, `<true | false>`, etc.
2. **Smart Pattern Recognition**: Uses regex with negative lookbehind/lookahead to avoid double-escaping
3. **Table Content Processing**: Ensures MDX compatibility within table cells
4. **Preserves Existing Escaping**: Won't re-escape already backticked content

### Image Handling

Automatic image discovery and copying:

1. **Recursive Image Search**: Finds all referenced images in DITA content
2. **Path Preservation**: Maintains relative paths for images
3. **Format Support**: Handles PNG, JPG, GIF, SVG, and other common formats
4. **Automatic Copying**: Copies images to output directory maintaining structure

## Conversion Pipeline

The full conversion pipeline (`make convert`) consists of:

1. **DITA-OT Processing**: Converts DITA to base Markdown
2. **Hierarchical Processing**: Applies numbering and organization
3. **Folder Renaming**: Creates meaningful folder names from content
4. **MDX Post-processing**: Applies Docusaurus-specific formatting
5. **TOC Generation**: Creates navigation structure
6. **Image Migration**: Copies all referenced images

## Recent Enhancements

- **Fixed MDX compilation errors** in Docusaurus by properly escaping angle bracket patterns
- **Implemented intelligent folder naming** using chapter titles extracted from content
- **Added Docusaurus-aware TOC generation** that accounts for URL transformations
- **Enhanced escape pattern detection** to handle complex patterns like `<true \| false>`
- **Two-phase folder renaming** to avoid conflicts during batch processing
- **Comprehensive error handling** for malformed DITA content

## Future Improvements

See `todo.txt` for planned features including:
- mdformat integration for consistent formatting
- Enhanced DITA element support
- Performance optimizations
- Configuration file support

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
