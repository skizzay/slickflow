package ai.slickflow.controlplane;

import javax.sql.DataSource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.JdbcTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/** Deployment permissions, applied only by the standalone maintenance executable. */
final class DatabaseRuntimeGrants {
    private final DataSource source;
    private final DatabaseSchemas schemas;
    private final String runtimeRole;

    DatabaseRuntimeGrants(DataSource source, DatabaseSchemas schemas, String runtimeRole) {
        if (runtimeRole == null || !runtimeRole.matches("[a-z][a-z0-9_]{0,62}")) {
            throw new IllegalArgumentException("Use a dedicated lowercase runtime role identifier");
        }
        this.source = source;
        this.schemas = schemas;
        this.runtimeRole = runtimeRole;
    }

    void validate() {
        var jdbc = new JdbcTemplate(source);
        if (!Boolean.TRUE.equals(jdbc.queryForObject(
                "select exists(select 1 from pg_catalog.pg_roles where rolname=? "
                        + "and rolname<>current_user and not rolsuper and not rolcreatedb "
                        + "and not rolcreaterole and not rolreplication and not rolbypassrls)",
                Boolean.class, runtimeRole))) {
            throw new IllegalStateException("Runtime role must already exist and be distinct and unprivileged");
        }
        if (Boolean.TRUE.equals(jdbc.queryForObject(
                "select exists(select 1 from pg_catalog.pg_auth_members m "
                        + "join pg_catalog.pg_roles r on r.oid=m.member where r.rolname=?)",
                Boolean.class, runtimeRole))) {
            throw new IllegalStateException("Runtime role must not inherit other roles");
        }
        if (Boolean.TRUE.equals(jdbc.queryForObject(
                "select exists(select 1 from pg_catalog.pg_namespace n where n.nspname in (?,?) "
                        + "and pg_catalog.has_schema_privilege(?,n.oid,'CREATE'))",
                Boolean.class, schemas.domainSchema(), schemas.engineSchema(), runtimeRole))) {
            throw new IllegalStateException("Runtime role must not have schema CREATE privileges");
        }
        if (Boolean.TRUE.equals(jdbc.queryForObject(
                "select exists(select 1 from pg_catalog.pg_namespace n "
                        + "where n.nspname in (?,?) and n.nspowner <> "
                        + "(select oid from pg_catalog.pg_roles where rolname=current_user))",
                Boolean.class, schemas.domainSchema(), schemas.engineSchema()))) {
            throw new IllegalStateException("Migration identity must own the configured schemas");
        }
    }

    void apply() {
        new TransactionTemplate(new JdbcTransactionManager(source)).executeWithoutResult(status -> {
            validate();
            var jdbc = new JdbcTemplate(source);
            String role = '"' + runtimeRole + '"';
            for (String name : new String[] {schemas.domainSchema(), schemas.engineSchema()}) {
                String schema = '"' + name + '"';
                jdbc.execute("grant usage on schema " + schema + " to " + role);
                jdbc.execute("grant select,insert,update,delete on all tables in schema " + schema + " to " + role);
                jdbc.execute("grant usage,select on all sequences in schema " + schema + " to " + role);
                // Defaults apply to future objects created by the current migration identity.
                jdbc.execute("alter default privileges in schema " + schema
                        + " grant select,insert,update,delete on tables to " + role);
                jdbc.execute("alter default privileges in schema " + schema
                        + " grant usage,select on sequences to " + role);
            }
        });
    }
}
