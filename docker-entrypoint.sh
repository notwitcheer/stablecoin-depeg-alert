#!/bin/bash
# Production Docker entrypoint for DepegAlert Bot

set -e

# Colors for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Health check function
check_health() {
    log_info "Performing health checks..."

    # Check database connection
    if python -c "from core.database import DatabaseManager; exit(0 if DatabaseManager.test_connection() else 1)" 2>/dev/null; then
        log_success "Database connection: OK"
    else
        log_error "Database connection: FAILED"
        return 1
    fi

    # Check required environment variables
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        log_error "TELEGRAM_BOT_TOKEN not set"
        return 1
    fi

    if [ -z "$ALERT_CHANNEL_ID" ]; then
        log_error "ALERT_CHANNEL_ID not set"
        return 1
    fi

    log_success "All health checks passed"
    return 0
}

# Database initialization
init_database() {
    log_info "Initializing database..."

    python -c "
from core.database import init_database
if init_database():
    print('✅ Database initialized successfully')
else:
    print('❌ Database initialization failed')
    exit(1)
"
}

# Wait for dependencies
wait_for_services() {
    log_info "Waiting for dependencies..."

    # Extract database host and port from DATABASE_URL
    if [ -n "$DATABASE_URL" ]; then
        DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
        DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

        if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
            log_info "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
            timeout 60 bash -c "until nc -z $DB_HOST $DB_PORT; do sleep 1; done" || {
                log_error "PostgreSQL not available after 60 seconds"
                exit 1
            }
            log_success "PostgreSQL is ready"
        fi
    fi

    # Wait for Redis if configured
    if [ -n "$REDIS_URL" ]; then
        REDIS_HOST=$(echo $REDIS_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
        REDIS_PORT=$(echo $REDIS_URL | sed -n 's/.*:\([0-9]*\)$/\1/p')

        if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
            log_info "Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."
            timeout 30 bash -c "until nc -z $REDIS_HOST $REDIS_PORT; do sleep 1; done" || {
                log_warn "Redis not available (optional service)"
            }
        fi
    fi
}

# Set up logging
setup_logging() {
    log_info "Setting up logging..."

    # Create log directory if it doesn't exist
    mkdir -p /app/logs

    # Set log level based on environment
    export LOG_LEVEL=${LOG_LEVEL:-INFO}
    log_info "Log level set to: $LOG_LEVEL"
}

# Startup banner
print_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                        DepegAlert Bot                          ║"
    echo "║                    Production Deployment                       ║"
    echo "║                                                                ║"
    echo "║  🚨 Real-time stablecoin monitoring and alerts                ║"
    echo "║  📊 Production-ready with monitoring & health checks          ║"
    echo "║  🔧 Built with resilience and scalability                     ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    log_info "Version: 2.0.0"
    log_info "Environment: Production"
    log_info "Build Date: $(date)"
    echo ""
}

# Main execution
main() {
    print_banner

    # Setup environment
    setup_logging

    # Wait for dependencies
    wait_for_services

    # Initialize database
    init_database

    # Perform health checks
    if ! check_health; then
        log_error "Health check failed, aborting startup"
        exit 1
    fi

    log_success "Startup checks completed successfully"

    # Start the appropriate service based on command
    case "${1:-bot}" in
        "bot")
            log_info "Starting Telegram Bot with monitoring..."
            exec python -c "
import asyncio
from bot.main import main as bot_main
from monitoring_server import MonitoringServer

async def run_services():
    # Start monitoring server
    monitoring_server = MonitoringServer()
    await monitoring_server.start()

    # Start bot
    await bot_main()

asyncio.run(run_services())
"
            ;;

        "monitoring")
            log_info "Starting monitoring server only..."
            exec python monitoring_server.py
            ;;

        "health-check")
            log_info "Performing health check..."
            check_health
            exit $?
            ;;

        "init-db")
            log_info "Initializing database only..."
            init_database
            exit $?
            ;;

        *)
            log_info "Starting with custom command: $@"
            exec "$@"
            ;;
    esac
}

# Handle signals gracefully
cleanup() {
    log_info "Received shutdown signal, cleaning up..."
    # Add any cleanup logic here
    exit 0
}

trap cleanup SIGTERM SIGINT

# Run main function
main "$@"