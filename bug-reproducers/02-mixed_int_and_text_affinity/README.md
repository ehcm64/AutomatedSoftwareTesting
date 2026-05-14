## Summary

The `JOIN` with `USING(id)` on a `UNION` view that mixes `INT` and `TEXT` affinity on `id` columns returns an incorrect row.

## Minimized query

```sql
CREATE TABLE map_integer (id INT, name);
INSERT INTO map_integer VALUES(1,'a');
CREATE TABLE map_text (id TEXT, name);
INSERT INTO map_text VALUES('4','e');
CREATE TABLE data (id TEXT, name);
INSERT INTO data VALUES(1,'abc');
INSERT INTO data VALUES('4','xyz');
CREATE VIEW idmap AS SELECT * FROM map_integer UNION SELECT * FROM map_text;
SELECT * FROM data JOIN idmap USING(id);
```

## Actual output

```sql
1|abc|a
```

## Expectation

```sql
4|xyz|e
```

The `data.id` column has `TEXT` affinity, so the value `1` is stored as the string `'1'`. On the other hand, the `idmap.id` keeps the affinity of the original tables, so the value `1` is stored as an integer. According to SQLite's type system rules, the comparison of `TEXT` and `INT` values doesn't lead to equality even if they represent the same number. Therefore, the query should not return the row `data.id = '1'`, but it should return instead the row `data.id = '4'`.