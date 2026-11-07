\set ON_ERROR_STOP on
\pset pager off
-- OWNER REVIEW REQUIRED. Run once through psql -X -W, never with a password argument.
-- No role/password changes. Any failure: stop; never automatically rerun.
DO $$
BEGIN
    IF current_database() <> 'postgres' OR current_user <> 'postgres'
       OR inet_server_addr() IS DISTINCT FROM '127.0.0.1'::inet
       OR inet_server_port() IS DISTINCT FROM 5432 THEN
        RAISE EXCEPTION 'Unexpected administrator connection. Stop.';
    END IF;
    IF EXISTS (SELECT FROM pg_database WHERE datname = 'merge_test') THEN
        RAISE EXCEPTION 'merge_test exists. Stop; never replace it.';
    END IF;
    IF (SELECT count(*) FROM pg_roles WHERE rolname IN ('merge_owner','merge_app')) <> 2
       OR EXISTS (SELECT FROM pg_roles WHERE rolname IN ('merge_owner','merge_app')
          AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls
               OR rolcanlogin <> (rolname = 'merge_app')))
       OR EXISTS (SELECT FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
                  WHERE r.rolname IN ('merge_owner','merge_app')) THEN
        RAISE EXCEPTION 'Existing Merge roles conflict with approved setup. Stop.';
    END IF;
END $$;
-- CREATE DATABASE is not transactional. Creation itself fails if the name races.
-- ACL hardening follows creation immediately; a failure can leave partial setup.
CREATE DATABASE merge_test OWNER merge_owner TEMPLATE template0;
REVOKE ALL ON DATABASE merge_test FROM PUBLIC;
GRANT CONNECT ON DATABASE merge_test TO merge_app;
\connect merge_test postgres 127.0.0.1 5432
BEGIN;
DO $$
BEGIN
    IF current_database() <> 'merge_test' OR current_user <> 'postgres'
       OR inet_server_addr() IS DISTINCT FROM '127.0.0.1'::inet
       OR inet_server_port() IS DISTINCT FROM 5432
       OR pg_get_userbyid((SELECT datdba FROM pg_database
                         WHERE datname=current_database())) <> 'merge_owner' THEN
        RAISE EXCEPTION 'Unexpected test database identity/owner. Stop.';
    END IF;
    IF EXISTS (SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
               WHERE n.nspname='public') THEN
        RAISE EXCEPTION 'Unexpected public objects. Stop.';
    END IF;
END $$;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO merge_app;
COMMIT;
SELECT current_database() AS database,
       has_database_privilege('merge_app', current_database(), 'CONNECT') AS can_connect,
       has_schema_privilege('merge_app','public','USAGE') AS can_use_schema,
       has_schema_privilege('merge_app','public','CREATE') AS can_migrate;
