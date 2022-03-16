import re
import sys


ACCOUNT_CONSTRAINTS = re.compile(
    r'ALTER TABLE ONLY (?P<table>public\.\w+)\s+ADD CONSTRAINT (?P<constraint>["\w]+) FOREIGN KEY \((?P<fk>\w+)\) REFERENCES (?P<fk_table>public\.\w+)\((?P<field>\w+)\)(?P<tail>[^;]*);'
)
TABLE_RE = re.compile(r"CREATE TABLE public\.(\w+) ")

SQL_TEMPLATE = """
ALTER TABLE ONLY {table}
    DROP CONSTRAINT {constraint};
ALTER TABLE ONLY {table}
    ADD CONSTRAINT {constraint}
    FOREIGN KEY ({fk}) REFERENCES {fk_table}({field}) {on_delete}{tail};
"""


def get_constraints(schema_sql, on_delete):
    matches = ACCOUNT_CONSTRAINTS.findall(schema_sql)

    for match in matches:
        table, constraint, fk, fk_table, field, tail = match
        yield SQL_TEMPLATE.format(
            table=table,
            constraint=constraint,
            fk=fk,
            fk_table=fk_table,
            field=field,
            on_delete=on_delete,
            tail=tail,
        )


def generate_sql(schema, all_tables, safe_tables):
    for constraint in get_constraints(schema, "ON DELETE CASCADE "):
        print(constraint)

    PARTIAL_TABLES = [
        (
            "account_user",
            "email NOT LIKE '%@okfn.de' OR private = TRUE OR email IS NULL; UPDATE account_user SET password='';",
        ),
        ("document_document", "user_id IS NULL;"),
        (
            "document_document",
            "id NOT IN (SELECT id FROM document_document ORDER BY id DESC LIMIT 500);",
        ),
        ("document_documentcollection", "user_id IS NULL;"),
        ("fds_donation_donor", "user_id IS NULL;"),
        ("fds_donation_donation", "donor_id IS NULL;"),
        ("foirequest_foirequest", "public = FALSE;"),
        ("foirequest_foiproject", "public = FALSE;"),
        ("fds_blog_article", "start_publication IS NULL;"),
    ]
    PARTIAL_SAFE = set([x[0] for x in PARTIAL_TABLES])

    all_safe_tables = safe_tables | PARTIAL_SAFE

    for table, sql in PARTIAL_TABLES:
        # yes, allow sql injection here for update clause on account_user
        print("DELETE FROM %s WHERE %s" % (table, sql))

    for table in all_tables:
        if table not in all_safe_tables:
            print("DELETE FROM %s;" % table)

    for constraint in get_constraints(schema, ""):
        print(constraint)

    print("VACUUM FULL ANALYZE;")


def show_unsafe(all_tables, safe_tables):
    all_tables = set(all_tables)
    for table in sorted(all_tables - safe_tables):
        print('"{}",'.format(table))


def main(action="generate"):

    # 1. pg_dump fragdenstaat_de --schema-only > schema.sql
    # 2. DROP old fragdenstaat_de_light:
    # psql -U postgres -c "DROP DATABASE IF EXISTS fragdenstaat_de_light;"
    # 3. Copy database:
    # psql -U postgres -c "CREATE DATABASE fragdenstaat_de_light WITH TEMPLATE fragdenstaat_de OWNER fragdenstaat_de;"
    # 4. python create_light_sql.py > make_light.sql
    # 5. psql fragdenstaat_de_light < make_light.sql
    # 6. pg_dump fragdenstaat_de_light | gzip -c > fragdenstaat_light.sql.gz

    with open("safe_tables.txt") as f:
        safe_tables = set([x.strip() for x in f.readlines() if x.strip()])

    with open("schema.sql") as f:
        schema = f.read()

    all_tables = TABLE_RE.findall(schema)

    if action == "compare":
        show_unsafe(all_tables, safe_tables)
    else:
        generate_sql(schema, all_tables, safe_tables)


if __name__ == "__main__":
    main(*sys.argv[1:])
