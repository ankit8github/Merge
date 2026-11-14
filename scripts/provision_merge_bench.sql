-- PROPOSAL ONLY. Requires separate owner approval. No existing DB/role adoption.
-- psql -X -h 127.0.0.1 -p 5432 -U postgres -d postgres -W -f scripts/provision_merge_bench.sql
\set ON_ERROR_STOP on
DO $$ BEGIN
  IF current_database()<>'postgres' OR current_user<>'postgres'
     OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1' OR inet_server_port() IS DISTINCT FROM 5432 THEN
    RAISE EXCEPTION 'Unexpected provisioning identity';
  END IF;
  IF EXISTS(SELECT 1 FROM pg_database WHERE datname='merge_bench')
     OR EXISTS(SELECT 1 FROM pg_roles WHERE rolname='merge_bench_app') THEN
    RAISE EXCEPTION 'Target namespace exists: stop, never adopt or delete';
  END IF;
END $$;
CREATE ROLE merge_bench_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
-- psql hidden prompt; no literal password, argv secret or credential output.
\password merge_bench_app
CREATE DATABASE merge_bench OWNER merge_bench_app TEMPLATE template0;
REVOKE ALL ON DATABASE merge_bench FROM PUBLIC;
\connect merge_bench postgres 127.0.0.1 5432
DO $$ BEGIN
  IF current_database()<>'merge_bench' OR current_user<>'postgres'
     OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1' OR inet_server_port() IS DISTINCT FROM 5432 THEN
    RAISE EXCEPTION 'Unexpected new database identity';
  END IF;
END $$;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE,CREATE ON SCHEMA public TO merge_bench_app;
