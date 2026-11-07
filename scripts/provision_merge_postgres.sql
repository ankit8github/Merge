\set ON_ERROR_STOP on
\pset pager off
-- Run locally as postgres. Stop on any error; never rerun partial provisioning.
-- Password is entered via psql's hidden prompt, never supplied as SQL text.
BEGIN;
DO $$
BEGIN
    IF current_database() IS DISTINCT FROM 'postgres'
       OR inet_server_addr() IS DISTINCT FROM '127.0.0.1'::inet
       OR inet_server_port() IS DISTINCT FROM 5432
       OR current_user IS DISTINCT FROM 'postgres' THEN
        RAISE EXCEPTION 'Unexpected connection identity. Stop.';
    END IF;
    IF EXISTS (SELECT FROM pg_database WHERE datname = 'merge_dev')
       OR EXISTS (SELECT FROM pg_roles WHERE rolname IN ('merge_owner', 'merge_app')) THEN
        RAISE EXCEPTION 'Merge object already exists. Stop; do not replace or retry.';
    END IF;
END $$;
-- Non-login owner separates database ownership from application access.
CREATE ROLE merge_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE merge_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
SET LOCAL password_encryption = 'scram-sha-256';
\password merge_app
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_authid WHERE rolname = 'merge_app' AND rolpassword IS NOT NULL) THEN
        RAISE EXCEPTION 'Application password was not set. Stop.';
    END IF;
END $$;
COMMIT;
-- CREATE DATABASE must run outside a transaction. Failure leaves partial setup;
-- stop and inspect it rather than retrying or dropping anything.
CREATE DATABASE merge_dev OWNER merge_owner;
REVOKE ALL ON DATABASE merge_dev FROM PUBLIC;
GRANT CONNECT ON DATABASE merge_dev TO merge_app;
\connect merge_dev
BEGIN;
DO $$
BEGIN
    IF current_database() <> 'merge_dev'
       OR pg_get_userbyid((SELECT datdba FROM pg_database WHERE datname = current_database())) <> 'merge_owner' THEN
        RAISE EXCEPTION 'Unexpected database/owner. Stop.';
    END IF;
END $$;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO merge_app;
COMMIT;
SELECT current_database() AS database,
       has_database_privilege('merge_app', 'merge_dev', 'CONNECT') AS can_connect,
       has_schema_privilege('merge_app', 'public', 'USAGE') AS can_use_schema,
       has_schema_privilege('merge_app', 'public', 'CREATE') AS can_migrate;
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls
FROM pg_roles WHERE rolname IN ('merge_owner', 'merge_app');
