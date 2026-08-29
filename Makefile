# DITA to Markdown Conversion Tools Makefile

# Variables
DITA_OT_VERSION := 4.2.3
DITA_OT_DIR := dita-ot-$(DITA_OT_VERSION)
DITA_OT_ZIP := $(DITA_OT_DIR).zip
DITA_OT_URL := https://github.com/dita-ot/dita-ot/releases/download/$(DITA_OT_VERSION)/$(DITA_OT_ZIP)
DITA_CMD := $(DITA_OT_DIR)/bin/dita
PYTHON := python3

# Output directories
OUTPUT_DIR := output

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
BLUE := \033[0;34m
YELLOW := \033[0;33m
NC := \033[0m # No Color

# Default target
all: help

# Install DITA-OT
install: $(DITA_OT_DIR)

$(DITA_OT_DIR):
	@echo "$(BLUE)Installing DITA-OT $(DITA_OT_VERSION)...$(NC)"
	@curl -LO $(DITA_OT_URL)
	@echo "Extracting $(DITA_OT_ZIP)..."
	@$(PYTHON) -m zipfile -e $(DITA_OT_ZIP) .
	@rm $(DITA_OT_ZIP)
	@chmod +x $(DITA_CMD)
	@echo "$(GREEN)DITA-OT $(DITA_OT_VERSION) installed successfully!$(NC)"

# Check if DITA-OT is installed
check-ot:
	@if [ ! -d "$(DITA_OT_DIR)" ]; then \
		echo "$(RED)DITA-OT not installed. Run 'make install' first$(NC)"; \
		exit 1; \
	fi

# New unified converter (recommended)
convert: check-ot
	@$(PYTHON) convert.py $(CONVERT_ARGS)

# Convert single DITA file with DITA-OT (legacy)
convert-single: check-ot
	@if [ -z "$(INPUT)" ]; then \
		echo "$(RED)Error: INPUT not specified$(NC)"; \
		echo "Usage: make convert-single INPUT=file.dita [OUTPUT=dir]"; \
		exit 1; \
	fi
	@echo "$(BLUE)Converting with DITA-OT...$(NC)"
	@mkdir -p $(if $(OUTPUT),$(OUTPUT),$(OUTPUT_DIR))
	@$(DITA_CMD) -i $(INPUT) -f markdown_github -o $(if $(OUTPUT),$(OUTPUT),$(OUTPUT_DIR))
	@echo "$(GREEN)Conversion complete!$(NC)"

# Convert with DITA-OT and apply Docusaurus post-processing (legacy)
convert-docusaurus-legacy: check-ot clean
	@if [ -z "$(INPUT)" ] && [ -d "input" ] && ls input/*.dita 1> /dev/null 2>&1; then \
		echo "$(BLUE)Auto-scanning input/ folder...$(NC)"; \
		$(MAKE) batch; \
		ditamap=$$(ls input/*.ditamap 2>/dev/null | head -1); \
		if [ -n "$$ditamap" ]; then \
			echo "$(BLUE)Applying Docusaurus formatting with DITAMAP ordering...$(NC)"; \
			$(PYTHON) docusaurus_postprocess.py $(OUTPUT_DIR) -d "$$ditamap"; \
		else \
			echo "$(BLUE)Applying Docusaurus formatting...$(NC)"; \
			$(PYTHON) docusaurus_postprocess.py $(OUTPUT_DIR); \
		fi; \
	elif [ -n "$(INPUT)" ]; then \
		echo "$(BLUE)Converting with DITA-OT...$(NC)"; \
		mkdir -p $(if $(OUTPUT),$(OUTPUT),$(OUTPUT_DIR)); \
		$(DITA_CMD) -i $(INPUT) -f markdown_github -o $(if $(OUTPUT),$(OUTPUT),$(OUTPUT_DIR)); \
		echo "$(BLUE)Applying Docusaurus formatting...$(NC)"; \
		if [ -z "$(OUTPUT)" ]; then \
			$(PYTHON) docusaurus_postprocess.py $(OUTPUT_DIR); \
		else \
			$(PYTHON) docusaurus_postprocess.py $(OUTPUT); \
		fi; \
	else \
		echo "$(RED)Error: INPUT not specified and no DITA files in input/ folder$(NC)"; \
		echo "Usage: make convert-docusaurus INPUT=file.dita [OUTPUT=dir]"; \
		exit 1; \
	fi
	@echo "$(GREEN)Conversion and Docusaurus formatting complete!$(NC)"

# Batch convert all DITA files in input/ folder
batch: check-ot
	@$(PYTHON) convert.py -v
	@echo "$(GREEN)Batch conversion complete! Files saved to $(OUTPUT_DIR)/$(NC)"

# Show available output formats
formats: check-ot
	@echo "$(BLUE)Available DITA-OT output formats:$(NC)"
	@$(DITA_CMD) --transtypes

# Clean output directory
clean:
	@echo "$(BLUE)Cleaning output directory...$(NC)"
	@rm -rf $(OUTPUT_DIR)/*
	@echo "$(GREEN)Clean complete!$(NC)"

# Uninstall DITA-OT
uninstall:
	@echo "$(BLUE)Removing DITA-OT...$(NC)"
	@rm -rf $(DITA_OT_DIR)
	@echo "$(GREEN)DITA-OT removed!$(NC)"

# Reinstall DITA-OT
reinstall: uninstall install

# Show version
version: check-ot
	@$(DITA_CMD) --version

# Run unit tests for the post-processor
test:
	@echo "$(BLUE)Running unit tests...$(NC)"
	@$(PYTHON) test_postprocessor.py

# Test conversion with sample file
test-convert: check-ot
	@echo "$(BLUE)Running test conversion...$(NC)"
	@if [ -f "../examples/comprehensive_test.dita" ]; then \
		$(MAKE) convert-docusaurus INPUT=../examples/comprehensive_test.dita OUTPUT=test-output; \
		echo "$(GREEN)Test complete! Check test-output/ directory$(NC)"; \
	else \
		echo "$(RED)Test file not found: ../examples/comprehensive_test.dita$(NC)"; \
	fi

# Help
help:
	@echo "$(BLUE)DITA to Markdown Conversion Tools$(NC)"
	@echo ""
	@echo "$(GREEN)Recommended targets:$(NC)"
	@echo "  $(GREEN)make install$(NC)           - Install DITA-OT $(DITA_OT_VERSION)"
	@echo "  $(GREEN)make convert$(NC)           - Run complete conversion pipeline (input/ → output/)"
	@echo "  $(GREEN)make batch$(NC)             - Same as convert with verbose output"
	@echo "  $(GREEN)make clean$(NC)             - Remove generated output"
	@echo ""
	@echo "$(YELLOW)Advanced options:$(NC)"
	@echo "  $(GREEN)make convert CONVERT_ARGS=\"-i docs -o markdown\"$(NC)  # Custom directories"
	@echo "  $(GREEN)make convert CONVERT_ARGS=\"--no-docusaurus\"$(NC)      # Skip Docusaurus"
	@echo "  $(GREEN)make convert CONVERT_ARGS=\"--no-hierarchical\"$(NC)    # Skip numbering"
	@echo "  $(GREEN)make convert CONVERT_ARGS=\"-v\"$(NC)                   # Verbose output"
	@echo "  $(GREEN)make convert CONVERT_ARGS=\"-c\"$(NC)                   # Clean before convert"
	@echo ""
	@echo "$(YELLOW)Other targets:$(NC)"
	@echo "  $(GREEN)make formats$(NC)           - List available DITA-OT output formats"
	@echo "  $(GREEN)make test$(NC)              - Run unit tests"
	@echo "  $(GREEN)make uninstall$(NC)         - Remove DITA-OT installation"
	@echo ""
	@echo "Examples:"
	@echo "  make convert                    # Full pipeline with all features"
	@echo "  make convert CONVERT_ARGS=\"-v\" # Verbose conversion"
	@echo "  python3 convert.py --help      # See all converter options"

# Declare phony targets
.PHONY: all install check-ot convert convert-docusaurus batch formats \
        test test-convert clean uninstall reinstall version help