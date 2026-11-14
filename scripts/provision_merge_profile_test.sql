-- PROPOSAL ONLY. Requires separate owner approval; never run against retained DBs.
-- psql -X -h 127.0.0.1 -p 5432 -U postgres -d postgres -W -f scripts/provision_merge_profile_test.sql
\set ON_ERROR_STOP on
DO $$ BEGIN
  IF current_database()<>'postgres' OR current_user<>'postgres'
     OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1' OR inet_server_port() IS DISTINCT FROM 5432 THEN
    RAISE EXCEPTION 'Unexpected provisioning identity';
  END IF;
  IF EXISTS(SELECT 1 FROM pg_database WHERE datname='merge_profile_test') THEN
    RAISE EXCEPTION 'Target exists: stop, never adopt or delete';
  END IF;
  IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='merge_app' AND rolcanlogin
      AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
     OR EXISTS(SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname='merge_app')) THEN
    RAISE EXCEPTION 'Existing unprivileged merge_app required; no role alterations';
  END IF;
END $$;
CREATE DATABASE merge_profile_test OWNER merge_app TEMPLATE template0;
REVOKE ALL ON DATABASE merge_profile_test FROM PUBLIC;
\connect merge_profile_test postgres 127.0.0.1 5432
DO $$ BEGIN
  IF current_database()<>'merge_profile_test' OR current_user<>'postgres'
     OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1' OR inet_server_port() IS DISTINCT FROM 5432 THEN
    RAISE EXCEPTION 'Unexpected new database identity';
  END IF;
END $$;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE,CREATE ON SCHEMA public TO merge_app;
