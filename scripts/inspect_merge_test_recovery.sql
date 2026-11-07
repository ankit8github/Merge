\set ON_ERROR_STOP on
\pset pager off
-- Metadata-only recovery inspection; never repair or rerun provisioning here.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '5s';
SET LOCAL search_path = pg_catalog, pg_temp;
DO $$
BEGIN
    IF current_database() IS DISTINCT FROM 'merge_test'
       OR current_user IS DISTINCT FROM 'postgres'
       OR session_user IS DISTINCT FROM 'postgres'
       OR inet_server_addr() IS DISTINCT FROM '127.0.0.1'::inet
       OR inet_server_port() IS DISTINCT FROM 5432 THEN
        RAISE EXCEPTION 'Unexpected recovery connection identity. Stop.';
    END IF;
END $$;

SELECT current_database() AS database, current_user AS effective_role,
       session_user AS authenticated_role, inet_server_addr() AS server_address,
       inet_server_port() AS server_port,
       current_setting('transaction_read_only') AS transaction_read_only;

SELECT datname, pg_get_userbyid(datdba) AS database_owner,
       datacl::text AS database_acl
FROM pg_database WHERE datname = current_database();

SELECT nspname AS schema, pg_get_userbyid(nspowner) AS schema_owner,
       nspacl::text AS schema_acl
FROM pg_namespace WHERE nspname = 'public';

-- OID-based checks report NULL if the expected role/schema is missing.
SELECT r.rolname,
       has_database_privilege(r.oid, d.oid, 'CONNECT') AS app_connect,
       has_schema_privilege(r.oid, n.oid, 'USAGE') AS app_usage,
       has_schema_privilege(r.oid, n.oid, 'CREATE') AS app_create
FROM pg_database d
LEFT JOIN pg_roles r ON r.rolname = 'merge_app'
LEFT JOIN pg_namespace n ON n.nspname = 'public'
WHERE d.datname = current_database();

SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
       rolreplication, rolbypassrls, rolinherit
FROM pg_roles WHERE rolname IN ('merge_owner', 'merge_app') ORDER BY rolname;

-- Show memberships in either direction, including grants of these roles to others.
SELECT member_role.rolname AS member, parent_role.rolname AS granted_role,
       membership.admin_option
FROM pg_auth_members membership
JOIN pg_roles member_role ON member_role.oid = membership.member
JOIN pg_roles parent_role ON parent_role.oid = membership.roleid
WHERE member_role.rolname IN ('merge_owner', 'merge_app')
   OR parent_role.rolname IN ('merge_owner', 'merge_app')
ORDER BY member_role.rolname, parent_role.rolname;

-- Relation metadata only: includes tables, views, sequences and indexes.
SELECT n.nspname AS schema, c.relname AS object, c.relkind AS kind,
       pg_get_userbyid(c.relowner) AS owner
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' ORDER BY c.relname;

-- Signatures, not routine bodies or application rows.
SELECT n.nspname AS schema, p.proname AS routine, p.prokind AS kind,
       pg_get_function_identity_arguments(p.oid) AS arguments,
       pg_get_userbyid(p.proowner) AS owner
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' ORDER BY p.proname, p.oid;

SELECT n.nspname AS schema, t.typname AS type, t.typtype AS kind,
       pg_get_userbyid(t.typowner) AS owner
FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'public' ORDER BY t.typname;

-- psql conditionals prevent parsing a query against an absent version table.
SELECT to_regclass('public.alembic_version') IS NOT NULL AS version_exists \gset recovery_
\if :recovery_version_exists
SELECT version_num AS alembic_revision FROM public.alembic_version;
\else
\echo 'Alembic version table absent; no revision recorded.'
\endif
COMMIT;
