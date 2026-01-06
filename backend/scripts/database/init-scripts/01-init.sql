-- PostgreSQL Production Initialization Script
-- This script is executed when the PostgreSQL container starts for the first time
-- ============================================================================

-- Create replication user (for HA/backup setup)
-- Do not error if user already exists
DO
$$
BEGIN
    CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'replicator';
EXCEPTION WHEN duplicate_object THEN
    ALTER USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'replicator';
END
$$;

-- Grant replication permissions
GRANT CONNECT ON DATABASE postgres TO replicator;

-- Create extensions for enhanced functionality
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";
CREATE EXTENSION IF NOT EXISTS "hstore";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Performance settings
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';

-- Logging configuration
ALTER SYSTEM SET log_min_duration_statement = 5000;  -- Log queries slower than 5s
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = off;

-- WAL configuration
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 10;
ALTER SYSTEM SET max_replication_slots = 10;
ALTER SYSTEM SET wal_keep_size = '1GB';

-- Checkpoint configuration
ALTER SYSTEM SET checkpoint_timeout = '15min';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET max_wal_size = '4GB';
ALTER SYSTEM SET min_wal_size = '1GB';

-- Vacuum configuration
ALTER SYSTEM SET autovacuum = on;
ALTER SYSTEM SET autovacuum_max_workers = 4;
ALTER SYSTEM SET autovacuum_naptime = '1min';
ALTER SYSTEM SET autovacuum_vacuum_threshold = 50;
ALTER SYSTEM SET autovacuum_analyze_threshold = 50;
ALTER SYSTEM SET autovacuum_vacuum_cost_limit = 200;

-- Statistics
ALTER SYSTEM SET track_activities = on;
ALTER SYSTEM SET track_counts = on;
ALTER SYSTEM SET track_functions = 'all';
ALTER SYSTEM SET track_io_timing = on;

-- Replication slots
SELECT * FROM pg_create_physical_replication_slot('backup', false);

-- Create backup directory (if not exists)
-- Note: This requires SUPERUSER permissions
-- CREATE DIRECTORY is not a standard SQL command - use shell

-- End of initialization script
-- The actual database tables will be created by Django migrations
COMMIT;
