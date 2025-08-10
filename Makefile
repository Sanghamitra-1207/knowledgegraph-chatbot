.PHONY: install install-dev test lint format clean docs run-export run-build help

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install the package"
	@echo "  install-dev  - Install with development dependencies"
	@echo "  lint         - Run linting (ruff)"
	@echo "  format       - Format code (ruff)"
	@echo "  clean        - Clean up temporary files"
	@echo "  docs         - Build documentation"
	@echo "  run-export   - Run data export tool"
	@echo "  run-build    - Run graph build tool"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e .[dev]

# Code quality
format:
	ruff format

lint:
	ruff check

# Documentation
docs:
	@echo "Documentation build not configured yet"

# Tools
run-export:
	python tools/export.py

run-build:
	python tools/build_graph.py

# Development setup
setup-dev: install-dev
	pre-commit install
	@echo "Development environment setup complete!"

# Run all checks
check: format lint
	@echo "All checks passed!"
