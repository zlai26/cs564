# AptFinder Web Server

This Flask app provides a small apartment-search interface for the CS564
database. It uses all 10 statements from `sql/checkpoint3_sql_queries.sql` for
the checkpoint query results panel and calls the stored procedures from
`sql/checkpoint3_stored_procedures.sql` for search, save, review, remove, and
price-update actions.

Run it from the repository root:

```bash
python webserver/app.py
```

At startup, enter the MySQL schema, user, and password. The schema defaults to
`cs564` and the user defaults to `root`. You can also set `MYSQL_DATABASE`,
`MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_HOST` environment variables.

Before using the app, make sure the base tables, imported data, app demo tables,
and stored procedures have been loaded:

```bash
mysql -u root -p cs564 < sql/create_tables.sql
python scripts/import_mysql_data.py
mysql -u root -p cs564 < sql/checkpoint3_app_tables_and_seed.sql
mysql -u root -p cs564 < sql/checkpoint3_stored_procedures.sql
```
