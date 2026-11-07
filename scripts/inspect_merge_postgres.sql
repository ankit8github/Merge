\set ON_ERROR_STOP on
\pset pager off
-- Owner-run read-only preflight. No passwords or password hashes selected.
BEGIN READ ONLY;
SELECT current_database() AS connected_database,
       inet_server_addr() AS server_address,
       inet_server_port() AS server_port;
SELECT datname, pg_get_userbyid(datdba) AS owner
FROM pg_database WHERE datname = 'merge_dev';
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
       rolreplication, rolbypassrls
FROM pg_roles WHERE rolname IN ('merge_owner', 'merge_app');
SELECT member_role.rolname AS member, parent_role.rolname AS granted_role
FROM pg_auth_members AS membership
JOIN pg_roles AS member_role ON member_role.oid = membership.member
JOIN pg_roles AS parent_role ON parent_role.oid = membership.roleid
WHERE member_role.rolname IN ('merge_owner', 'merge_app');
COMMIT;
