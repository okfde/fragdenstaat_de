import argparse
import graphlib
import itertools
import re
import sys
from collections import defaultdict

CONSTRAINTS_RE = re.compile(
    r'ALTER TABLE ONLY (?P<table>public\.\w+)\s+ADD CONSTRAINT (?P<constraint>["\w]+) FOREIGN KEY \((?P<fk>\w+)\) REFERENCES (?P<fk_table>public\.\w+)\((?P<field>\w+)\)(?P<tail>[^;]*);'
)
TABLE_RE = re.compile(r"CREATE TABLE (public\.\w+) ")
SEQUENCE_RE = re.compile(
    r"ALTER TABLE ONLY (?P<table>public\.\w+) ALTER COLUMN (?P<column>\w+) SET DEFAULT nextval\('(?P<sequence>public\.\w+)'::regclass\);"
)

SQL_TEMPLATE = """
ALTER TABLE ONLY {table}
    DROP CONSTRAINT {constraint};
ALTER TABLE ONLY {table}
    ADD CONSTRAINT {constraint}
    FOREIGN KEY ({fk}) REFERENCES {fk_table}({field}) {on_delete}{tail};
"""


def escape_quote(s):
    return s.replace('"', '\\"')


def get_fk_graph(schema_sql):
    self_references = set()
    graph = defaultdict(set)
    fk_sets = defaultdict(set)
    matches = CONSTRAINTS_RE.findall(schema_sql)
    for match in matches:
        table, constraint, fk, fk_table, field, tail = match
        if table == fk_table:
            self_references.add(table)
        else:
            fk_sets[(table, fk_table)].add(fk)
            graph[table].add(fk_table)

    ordered = None
    while True:
        try:
            ts = graphlib.TopologicalSorter(graph)
            ordered = list(ts.static_order())
            break
        except graphlib.CycleError as e:
            cycle = e.args[1]
            for table in cycle:
                if table in self_references:
                    continue
                for fk_table in graph[table]:
                    if fk_table in cycle:
                        graph[table].remove(fk_table)
                        break

    return ordered, graph, self_references, fk_sets


def is_fk_nullable(schema, table, field):
    match = re.search(
        r"CREATE TABLE %s \(\s+[^;]*?%s integer," % (table, field),
        schema,
        re.MULTILINE,
    )
    return match is not None


def get_join_list(table, schema, graph, filters, fk_sets):
    join_list = []
    for join_table in graph[table]:
        if not (table in filters and join_table in filters):
            fk_set_key = (table, join_table)
            fk_set = fk_sets[fk_set_key]
            non_nullable_fks = [
                fk for fk in fk_set if not is_fk_nullable(schema, table, fk)
            ]
            if not non_nullable_fks:
                continue

        if join_table in filters:
            join_list.append((table, join_table))

        further_joins = get_join_list(join_table, schema, graph, filters, fk_sets)
        if further_joins:
            join_list.extend(further_joins)
            join_list.append((table, join_table))
    return join_list


def get_copy_selects(schema, filters, safe_tables, safe_fks):
    restricted_tables = set(filters.keys())
    controlled_tables = restricted_tables | safe_tables

    ordered, graph, self_references, fk_sets = get_fk_graph(schema)
    no_constraints = controlled_tables - set(ordered)

    for table in itertools.chain(no_constraints, ordered):
        if table not in controlled_tables:
            continue
        joins = get_join_list(table, schema, graph, filters, fk_sets)
        filter_set = set()
        if joins:
            join_tables = set()
            for a, b in joins:
                join_tables.add(a)
                join_tables.add(b)
                filter_set |= {f"{b}.{f}" for f in filters.get(b, ())}
                filter_set |= {f"{a}.{f}" for f in filters.get(a, ())}
                for fk in fk_sets[(a, b)]:
                    if (a, fk) in safe_fks:
                        filter_set.add(f"({a}.{fk} = {b}.id OR {a}.{fk} IS NULL)")
                    else:
                        filter_set.add(f"{a}.{fk} = {b}.id")

            tables = list(join_tables | {table})
        else:
            if table in filters:
                filter_set |= {f"{table}.{f}" for f in filters[table]}
            tables = [table]

        where_clause = ""
        if filter_set:
            where_clause = " AND ".join(filter_set)
            where_clause = f" WHERE {where_clause}"
        sql = "SELECT DISTINCT {table}.* FROM {tables} {where}".format(
            table=table, tables=", ".join(tables), where=escape_quote(where_clause)
        )

        yield table, sql


def generate_copy_script(
    outfile,
    source_db="fragdenstaat_de",
    target_db="fragdenstaat_de_light",
    source_connection="",
    source_password="",
    target_connection="",
    target_owner="fragdenstaat_de",
    safe_tables="safe_tables.txt",
    safe_fks="safe_fks.txt",
    schema_file="schema.sql",
):
    FILTERS = dict(
        [
            (
                "public.account_user",
                (
                    "email COLLATE \"und-x-icu\" LIKE '%@okfn.de'",
                    "is_staff = TRUE",
                    "private = FALSE",
                ),
            ),
            (
                "public.document_document",
                (
                    "id IN ((SELECT id FROM document_document WHERE portal_id IS NULL AND user_id IS NOT NULL ORDER BY id DESC LIMIT 500) UNION (SELECT id FROM document_document WHERE portal_id IS NOT NULL ORDER BY id DESC LIMIT 500))",
                ),
            ),
            ("public.document_documentcollection", ("user_id IS NOT NULL",)),
            ("public.fds_donation_donor", ("user_id IS NOT NULL",)),
            ("public.fds_donation_donation", ("donor_id IS NOT NULL",)),
            ("public.foirequest_foirequest", ("public = TRUE",)),
            ("public.foirequest_foiproject", ("public = TRUE",)),
            ("public.fds_blog_article", ("start_publication IS NOT NULL",)),
            ("public.django_amenities_amenity", ("city = 'Berlin'",)),
        ]
    )

    with open(safe_tables) as f:
        safe_tables = set(
            ["public.{}".format(x.strip()) for x in f.readlines() if x.strip()]
        )

    with open(safe_fks) as f:
        safe_fks = set(
            [
                ("public.{}".format(x.split()[0].strip()), x.split()[1].strip())
                for x in f.readlines()
                if x.strip()
            ]
        )

    with open(schema_file) as f:
        schema = f.read()
    all_tables = set(TABLE_RE.findall(schema))
    safe_tables &= all_tables

    table_setup = []
    constraints = []
    for line in schema.splitlines():
        if constraints or "SET DEFAULT nextval(" in line:
            constraints.append(line)
        else:
            table_setup.append(line)

    with open("table_setup.sql", "w") as f:
        for line in table_setup:
            f.write(line + "\n")

    with open("constraints.sql", "w") as f:
        for line in constraints:
            f.write(line + "\n")

    outfile.write("#!/bin/bash\nset -ex\n")

    outfile.write(
        f'psql -c "DROP DATABASE IF EXISTS {target_db};" {target_connection} postgres\n'
    )
    outfile.write(
        f'psql -c "CREATE DATABASE {target_db} OWNER {target_owner};" {target_connection} postgres\n'
    )
    outfile.write(f"psql {target_connection} {target_db} < table_setup.sql\n")

    outfile.write(f"export PGPASSWORD='{source_password}'\n")
    for table, select in get_copy_selects(schema, FILTERS, safe_tables, safe_fks):
        outfile.write(f'echo "Copying {table}"\n')
        cmd = f"""psql -c "COPY ({select}) TO STDOUT;" {source_connection} {source_db} | psql -c "COPY {table} FROM STDIN;" {target_connection} {target_db}\n"""
        outfile.write(cmd)
    outfile.write("unset PGPASSWORD\n")

    EXTRA_SQL = [
        "UPDATE account_user SET password = ''",
        "UPDATE public.publicbody_publicbody SET _created_by_id = NULL",
        "UPDATE public.publicbody_publicbody SET _updated_by_id = NULL",
    ]
    for sql in EXTRA_SQL:
        outfile.write(
            f"""psql -c "{escape_quote(sql)}" {target_connection} {target_db}\n"""
        )

    outfile.write(f"psql {target_connection} {target_db} < constraints.sql\n")

    matches = SEQUENCE_RE.findall(schema)
    for match in matches:
        table, column, sequence = match
        sql = f"""SELECT SETVAL('{sequence}', COALESCE(MAX({column}), 1) ) FROM {table};"""
        outfile.write(
            f"""psql -c "{escape_quote(sql)}" {target_connection} {target_db}\n"""
        )


def show_unsafe(safe_tables="safe_tables.txt", schema_file="schema.sql"):
    with open(schema_file) as f:
        schema = f.read()

    all_tables = set(TABLE_RE.findall(schema))
    with open(safe_tables) as f:
        safe_tables = set(
            ["public.{}".format(x.strip()) for x in f.readlines() if x.strip()]
        )

    for table in sorted(all_tables - safe_tables):
        print("{}".format(table))


def main():
    parser = argparse.ArgumentParser(
        prog="fragdenstaat_light creator",
        description="Creates a light version of the fragdenstaat_de database",
    )
    parser.add_argument("action", choices=["generate", "compare"])
    parser.add_argument("--schema_file", help="schema file", default="schema.sql")
    parser.add_argument(
        "--safe_tables", help="safe tables file", default="safe_tables.txt"
    )
    parser.add_argument("--safe_fks", help="safe fks file", default="safe_fks.txt")
    parser.add_argument(
        "--source_db",
        help="Postgres target connection details",
        default="fragdenstaat_de",
    )
    parser.add_argument(
        "--source_connection", help="Postgres source connection details", default=""
    )
    parser.add_argument(
        "--source_password", help="Postgres source password", default=""
    )
    parser.add_argument(
        "--target_connection", help="Postgres target connection details", default=""
    )
    parser.add_argument(
        "--target_db",
        help="Postgres target connection details",
        default="fragdenstaat_de_light",
    )

    args = parser.parse_args()
    if args.action == "generate":
        generate_copy_script(
            sys.stdout,
            safe_tables=args.safe_tables,
            safe_fks=args.safe_fks,
            schema_file=args.schema_file,
            source_connection=args.source_connection,
            target_connection=args.target_connection,
            source_password=args.source_password,
            target_db=args.target_db,
            source_db=args.source_db,
        )
    elif args.action == "compare":
        show_unsafe(safe_tables=args.safe_tables, schema_file=args.schema_file)


if __name__ == "__main__":
    main()
