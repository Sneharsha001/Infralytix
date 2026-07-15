-- =============================================================================
-- Infralytix — MySQL Database Initialization Script
-- =============================================================================
-- This script runs ONCE when the MySQL container is first started.
-- It sets up the database with production-quality settings.
--
-- File: backend/scripts/init.sql
-- Executed by: Docker entrypoint (/docker-entrypoint-initdb.d/)
-- =============================================================================

-- Ensure we're using the correct database
CREATE DATABASE IF NOT EXISTS `infralytix_db`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `infralytix_db`;

-- =============================================================================
-- Grant permissions to the application user
-- =============================================================================
-- The root user creates this; the app never needs root access
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER, REFERENCES
    ON `infralytix_db`.*
    TO 'infralytix_user'@'%';

FLUSH PRIVILEGES;

-- =============================================================================
-- MySQL Performance & Character Set Settings
-- =============================================================================
-- These are applied at session level for this init script.
-- Production tuning is done via MySQL config (my.cnf or environment variables).

SET NAMES 'utf8mb4';
SET CHARACTER SET utf8mb4;

-- =============================================================================
-- Alembic Migration Tracking Table
-- =============================================================================
-- Alembic creates this automatically on first `alembic upgrade head`.
-- We don't create it here — this is informational only.
-- Table name: alembic_version

-- =============================================================================
-- Notes for Sprint 2+
-- =============================================================================
-- When Sprint 2 (Database Layer) is complete, Alembic will create:
--   - users
--   - projects
--   - agent_runs
--   - reports
--
-- Run migrations with:
--   docker compose exec backend alembic upgrade head
-- =============================================================================

SELECT 'Infralytix database initialization complete.' AS status;
