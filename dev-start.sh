#!/bin/bash
# Quick Development Startup Script for DepegAlert Bot

set -e

# Colors
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
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                    DepegAlert Development Setup                   ║"
    echo "║                                                                   ║"
    echo "║  🔧 Quick start for local development                            ║"
    echo "║  🐳 Docker Compose with PostgreSQL & Redis                       ║"
    echo "║  🔥 Hot reloading and debug mode enabled                         ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo ""
}

check_requirements() {
    log_info "Checking requirements..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check for .env file
    if [ ! -f ".env" ] && [ ! -f ".env.dev" ]; then
        log_warn "No .env file found. Creating one from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_success "Created .env file from .env.example"
            log_warn "Please edit .env file with your Telegram bot token and channel IDs"
        else
            log_error ".env.example not found. Cannot create .env file."
            exit 1
        fi
    fi

    log_success "All requirements met"
}

start_services() {
    log_info "Starting development services..."

    # Use docker compose (new) or docker-compose (legacy)
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi

    # Start infrastructure services first
    log_info "Starting PostgreSQL and Redis..."
    $COMPOSE_CMD -f docker-compose.dev.yml up -d postgres-dev redis-dev

    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 10

    # Run database migrations
    log_info "Running database migrations..."
    $COMPOSE_CMD -f docker-compose.dev.yml --profile migrate run --rm migrate-dev || {
        log_warn "Database migrations failed, continuing anyway..."
    }

    # Start the bot
    log_info "Starting DepegAlert Bot..."
    $COMPOSE_CMD -f docker-compose.dev.yml up bot-dev
}

start_with_admin() {
    log_info "Starting development services with admin tools..."

    # Use docker compose (new) or docker-compose (legacy)
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi

    # Start all services including admin tools
    log_info "Starting all services..."
    $COMPOSE_CMD -f docker-compose.dev.yml --profile admin up -d

    # Wait for services
    sleep 10

    # Run database migrations
    log_info "Running database migrations..."
    $COMPOSE_CMD -f docker-compose.dev.yml --profile migrate run --rm migrate-dev || {
        log_warn "Database migrations failed, continuing anyway..."
    }

    log_success "Services started successfully!"
    echo ""
    log_info "Available services:"
    echo "  • PostgreSQL: localhost:5433 (user: depeg_dev, password: dev_password_123)"
    echo "  • Redis: localhost:6380"
    echo "  • PgAdmin: http://localhost:5050 (admin@depegalert.dev / dev_admin_123)"
    echo "  • Redis Commander: http://localhost:8082"
    echo "  • Bot Monitoring: http://localhost:8081"
    echo ""
    log_info "To view logs: $COMPOSE_CMD -f docker-compose.dev.yml logs -f bot-dev"
    log_info "To stop services: $COMPOSE_CMD -f docker-compose.dev.yml down"
}

stop_services() {
    log_info "Stopping development services..."

    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi

    $COMPOSE_CMD -f docker-compose.dev.yml down
    log_success "Services stopped"
}

clean_services() {
    log_info "Stopping and cleaning up development services..."

    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi

    $COMPOSE_CMD -f docker-compose.dev.yml down -v
    docker system prune -f
    log_success "Cleanup complete"
}

show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start      Start development services (default)"
    echo "  admin      Start with admin tools (PgAdmin, Redis Commander)"
    echo "  stop       Stop all services"
    echo "  clean      Stop services and remove volumes"
    echo "  logs       Show bot logs"
    echo "  help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start      # Start basic development setup"
    echo "  $0 admin      # Start with database admin tools"
    echo "  $0 logs       # View bot logs"
}

show_logs() {
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi

    $COMPOSE_CMD -f docker-compose.dev.yml logs -f bot-dev
}

main() {
    print_banner

    case "${1:-start}" in
        "start")
            check_requirements
            start_services
            ;;
        "admin")
            check_requirements
            start_with_admin
            ;;
        "stop")
            stop_services
            ;;
        "clean")
            clean_services
            ;;
        "logs")
            show_logs
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