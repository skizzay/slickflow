-- #111: run with psql -X -v ON_ERROR_STOP=1 as a trusted cluster administrator.
-- Fixed dedicated names; existing objects are validated, never reset/adopted.
\set ON_ERROR_STOP on
SELECT pg_advisory_lock(111, 108);
DO $$
DECLARE role_record record;
BEGIN
  FOR role_record IN SELECT unnest(ARRAY['slickflow_migrator','slickflow_runtime']) AS name LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_record.name) THEN
      EXECUTE format('CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS', role_record.name);
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_record.name AND
        (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)) THEN
      RAISE EXCEPTION 'Unexpected elevated SlickFlow role; reconcile manually';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_auth_members m JOIN pg_roles a ON a.oid=m.member
        JOIN pg_roles b ON b.oid=m.roleid WHERE a.rolname=role_record.name OR b.rolname=role_record.name) THEN
      RAISE EXCEPTION 'Unexpected SlickFlow role membership; reconcile manually';
    END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba
      WHERE d.datname='slickflow' AND r.rolname<>'slickflow_migrator') THEN
    RAISE EXCEPTION 'Existing slickflow database has another owner; refusing adoption';
  END IF;
END $$;
SELECT 'CREATE DATABASE slickflow OWNER slickflow_migrator'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='slickflow') \gexec
SELECT pg_advisory_unlock(111, 108);
\connect slickflow
BEGIN;
SELECT pg_advisory_xact_lock(111, 108);
REVOKE ALL ON DATABASE slickflow FROM PUBLIC;
GRANT CONNECT ON DATABASE slickflow TO slickflow_runtime;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
-- The migration executable creates/owns schemas and applies runtime grants.
COMMIT;
-- No login passwords, HBA edits, database resets or shared-service restart.
-- Trusted operators provision login secrets separately through their secret store.
