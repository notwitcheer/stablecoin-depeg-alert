-- Database initialization script for DepegAlert Bot
-- This script sets up the database with proper permissions and initial data

-- Ensure we're using the correct database
\c depeg_alert;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Set timezone to UTC
SET timezone = 'UTC';

-- Create indexes for performance (tables are created by SQLAlchemy)
-- These will be created after the application starts and creates tables

-- Insert initial system metrics
-- This will be handled by the application during startup

-- Grant necessary permissions to the application user
GRANT USAGE ON SCHEMA public TO depeg_user;
GRANT CREATE ON SCHEMA public TO depeg_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO depeg_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO depeg_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO depeg_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO depeg_user;

-- Optimize PostgreSQL settings for the application
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = on;
ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log slow queries

-- Create a function to clean old data (for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Clean up old price data (keep 30 days)
    DELETE FROM stablecoin_prices
    WHERE timestamp < NOW() - INTERVAL '30 days';

    -- Clean up old alert history (keep 90 days)
    DELETE FROM alert_history
    WHERE created_at < NOW() - INTERVAL '90 days';

    -- Clean up old system metrics (keep 7 days)
    DELETE FROM system_metrics
    WHERE timestamp < NOW() - INTERVAL '7 days';

    -- Clean up expired cooldowns
    DELETE FROM alert_cooldowns
    WHERE cooldown_until < NOW();

END;
$$ LANGUAGE plpgsql;

-- Create a scheduled job to run cleanup (requires pg_cron extension)
-- This is optional and requires superuser privileges
-- SELECT cron.schedule('cleanup-old-data', '0 2 * * *', 'SELECT cleanup_old_data();');

-- Log successful initialization
INSERT INTO system_metrics (metric_name, metric_value, metric_unit, timestamp)
VALUES ('database_initialized', 1, 'boolean', NOW())
ON CONFLICT DO NOTHING;