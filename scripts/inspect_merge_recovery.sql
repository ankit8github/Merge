\set ON_ERROR_STOP on
\pset pager off
-- Read-only recovery audit. Connect directly to merge_dev as postgres.
-- No passwords, hashes, row contents or function definitions are selected.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
DO $$
BEGIN
    IF current_database() IS DISTINCT FROM 'merge_dev'
       OR inet_server_addr() IS DISTINCT FROM '127.0.0.1'::inet
       OR inet_server_port() IS DISTINCT FROM 5432 THEN
        RAISE EXCEPTION 'Unexpected server or database. Stop.';
    END IF;
END $$;

SELECT current_database() AS database, current_user AS inspecting_role,
       inet_server_addr() AS server_address, inet_server_port() AS server_port,
       current_setting('transaction_read_only') AS transaction_read_only;

SELECT datname, pg_get_userbyid(datdba) AS database_owner,
       has_database_privilege('merge_app', oid, 'CONNECT') AS app_connect,
       datacl::text AS database_acl
FROM pg_database WHERE datname = current_database();

SELECT nspname AS schema, pg_get_userbyid(nspowner) AS schema_owner,
       has_schema_privilege('merge_app', oid, 'USAGE') AS app_usage,
       has_schema_privilege('merge_app', oid, 'CREATE') AS app_create,
       nspacl::text AS schema_acl
FROM pg_namespace WHERE nspname = 'public';

-- Exact PUBLIC schema grants, separate from merge_app's effective privileges.
SELECT acl.privilege_type AS public_schema_privilege, acl.is_grantable
FROM pg_namespace AS schema
CROSS JOIN LATERAL aclexplode(COALESCE(schema.nspacl, acldefault('n', schema.nspowner))) AS acl
WHERE schema.nspname = 'public' AND acl.grantee = 0
ORDER BY acl.privilege_type;

SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
       rolreplication, rolbypassrls
FROM pg_roles WHERE rolname IN ('merge_owner', 'merge_app') ORDER BY rolname;

SELECT member_role.rolname AS member, parent_role.rolname AS granted_role
FROM pg_auth_members AS membership
JOIN pg_roles AS member_role ON member_role.oid = membership.member
JOIN pg_roles AS parent_role ON parent_role.oid = membership.roleid
WHERE member_role.rolname IN ('merge_owner', 'merge_app');

-- User schema ownership; public may normally be owned by pg_database_owner.
SELECT nspname AS schema, pg_get_userbyid(nspowner) AS owner
FROM pg_namespace
WHERE nspname <> 'information_schema' AND nspname !~ '^pg_'
ORDER BY nspname;

-- Tables, partitioned tables, sequences, views, indexes and other relations.
SELECT schema.nspname AS schema, relation.relname AS object,
       relation.relkind AS kind, pg_get_userbyid(relation.relowner) AS owner
FROM pg_class AS relation
JOIN pg_namespace AS schema ON schema.oid = relation.relnamespace
WHERE schema.nspname <> 'information_schema' AND schema.nspname !~ '^pg_'
ORDER BY schema.nspname, relation.relname;

-- Routines and types are listed by metadata only, without their contents.
SELECT schema.nspname AS schema, routine.proname AS routine,
       pg_get_function_identity_arguments(routine.oid) AS arguments,
       pg_get_userbyid(routine.proowner) AS owner
FROM pg_proc AS routine
JOIN pg_namespace AS schema ON schema.oid = routine.pronamespace
WHERE schema.nspname <> 'information_schema' AND schema.nspname !~ '^pg_'
ORDER BY schema.nspname, routine.proname, routine.oid;

SELECT schema.nspname AS schema, datatype.typname AS type,
       datatype.typtype AS kind, pg_get_userbyid(datatype.typowner) AS owner
FROM pg_type AS datatype
JOIN pg_namespace AS schema ON schema.oid = datatype.typnamespace
WHERE schema.nspname <> 'information_schema' AND schema.nspname !~ '^pg_'
ORDER BY schema.nspname, datatype.typname;

SELECT extname AS extension, extversion AS version,
       pg_get_userbyid(extowner) AS owner
FROM pg_extension ORDER BY extname;
COMMIT;
