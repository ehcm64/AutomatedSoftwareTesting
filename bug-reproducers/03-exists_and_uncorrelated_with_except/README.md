## Summary

The correlated `EXISTS(... EXCEPT ...)` subquery returns an empty result when it should return rows. The bug was present in SQLite 3.51.1, but not in SQLite 3.53.1.

## Minimized query

```sql
CREATE TABLE photo (pk INTEGER PRIMARY KEY);
CREATE TABLE tag (pk INTEGER PRIMARY KEY, fk INTEGER);
INSERT INTO photo VALUES (1);
INSERT INTO tag VALUES (21, 1);
SELECT P.pk FROM PHOTO AS P
WHERE EXISTS(
    SELECT T2.pk FROM TAG AS T2 WHERE T2.fk = P.pk
    EXCEPT
    SELECT T3.pk FROM TAG AS T3 WHERE T3.fk = P.pk
);
```

## Actual output

```sql
1
```

## Expectation

```sql
<empty result set>
```

The subquery inside `EXISTS` uses `EXCEPT` to compute the difference between two identical sets. The expected result would be an empty set, since both sides of the `EXCEPT` are the same. Therefore, the `EXISTS` condition should evaluate to `FALSE`.

What's interesting is that the provided patched version actually returns the expected result, while the provided unmodified SQLite 3.51.1 returns the wrong result. To gather more insights, we tested the query on the official SQLite 3.53.1 version, which also returns the expected result, making us belive that the bug already existed in SQLite 3.51.1 and was fixed in a later version.