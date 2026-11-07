\set ON_ERROR_STOP on
\pset pager off
BEGIN READ ONLY;
DO $$
BEGIN
    IF current_database() <> 'postgres'
       OR inet_server_addr() IS DISTINCT FROM '127.0.0.1'::inet
       OR inet_server_port() IS DISTINCT FROM 5432 THEN
        RAISE EXCEPTION 'Unexpected maintenance connection. Stop.';
    END IF;
    IF EXISTS (SELECT FROM pg_database WHERE datname = 'merge_test') THEN
        RAISE EXCEPTION 'merge_test already exists. Stop for owner review.';
    END IF;
END $$;
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
       rolreplication, rolbypassrls
FROM pg_roles WHERE rolname IN ('merge_owner', 'merge_app');
COMMIT;
