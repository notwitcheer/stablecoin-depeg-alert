#!/bin/bash
# Code Formatting and Linting Script for DepegAlert Bot

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                   Code Formatting & Linting                     ║"
    echo "║                                                                  ║"
    echo "║  🔧 Automated code quality and consistency checks               ║"
    echo "║  🎨 Formatting with Black and isort                             ║"
    echo "║  📋 Linting with Flake8, MyPy, and Bandit                      ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
}

check_tools() {
    log_info "Checking if development tools are installed..."

    # List of required tools
    tools=("black" "isort" "flake8" "mypy" "bandit")
    missing_tools=()

    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing tools: ${missing_tools[*]}"
        log_info "Install with: pip install -r requirements-dev.txt"
        exit 1
    fi

    log_success "All development tools are installed"
}

format_code() {
    log_info "Formatting code with Black and isort..."

    # Format with Black
    log_info "Running Black formatter..."
    if black --check --diff . 2>/dev/null; then
        log_success "Code is already formatted with Black"
    else
        log_info "Applying Black formatting..."
        black .
        log_success "Black formatting applied"
    fi

    # Sort imports with isort
    log_info "Running isort..."
    if isort --check-only --diff . 2>/dev/null; then
        log_success "Imports are already sorted"
    else
        log_info "Sorting imports..."
        isort .
        log_success "Import sorting applied"
    fi
}

lint_code() {
    log_info "Running code linting..."

    # Flake8 linting
    log_info "Running Flake8..."
    if flake8 .; then
        log_success "Flake8 checks passed"
    else
        log_error "Flake8 found issues"
        return 1
    fi

    # MyPy type checking
    log_info "Running MyPy type checking..."
    if mypy .; then
        log_success "MyPy type checks passed"
    else
        log_error "MyPy found type issues"
        return 1
    fi

    # Bandit security linting
    log_info "Running Bandit security checks..."
    if bandit -r . -f json -o /tmp/bandit-report.json 2>/dev/null; then
        log_success "Bandit security checks passed"
    else
        log_warn "Bandit found potential security issues"
        # Don't fail the script for security warnings, just warn
    fi
}

run_tests() {
    log_info "Running tests with coverage..."

    if python -m pytest; then
        log_success "All tests passed"
    else
        log_error "Some tests failed"
        return 1
    fi
}

check_dependencies() {
    log_info "Checking for dependency vulnerabilities..."

    if command -v safety &> /dev/null; then
        if safety check; then
            log_success "No known vulnerabilities found"
        else
            log_warn "Potential vulnerabilities found in dependencies"
        fi
    else
        log_warn "Safety not installed, skipping vulnerability check"
    fi
}

show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  format     Format code with Black and isort"
    echo "  lint       Run linting checks (Flake8, MyPy, Bandit)"
    echo "  test       Run tests with coverage"
    echo "  check      Check dependencies for vulnerabilities"
    echo "  all        Run all checks (format, lint, test, check) - default"
    echo "  ci         Run CI pipeline (lint and test only, no formatting)"
    echo "  help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 format    # Format code only"
    echo "  $0 lint      # Run linting only"
    echo "  $0 all       # Run everything"
    echo "  $0 ci        # Run CI checks"
}

run_ci() {
    log_info "Running CI pipeline (no formatting, checks only)..."

    # Check if code is properly formatted
    log_info "Checking code formatting..."
    if ! black --check --diff . ; then
        log_error "Code is not properly formatted. Run 'black .' to fix."
        return 1
    fi

    if ! isort --check-only --diff . ; then
        log_error "Imports are not sorted. Run 'isort .' to fix."
        return 1
    fi

    log_success "Code formatting is correct"

    # Run linting
    lint_code || return 1

    # Run tests
    run_tests || return 1

    # Check dependencies
    check_dependencies

    log_success "CI pipeline completed successfully"
}

run_all() {
    log_info "Running complete code quality pipeline..."

    # Format code
    format_code || return 1

    # Run linting
    lint_code || return 1

    # Run tests
    run_tests || return 1

    # Check dependencies
    check_dependencies

    log_success "All code quality checks completed successfully"
}

main() {
    print_banner

    case "${1:-all}" in
        "format")
            check_tools
            format_code
            ;;
        "lint")
            check_tools
            lint_code
            ;;
        "test")
            run_tests
            ;;
        "check")
            check_dependencies
            ;;
        "all")
            check_tools
            run_all
            ;;
        "ci")
            check_tools
            run_ci
            ;;
        "help")
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"