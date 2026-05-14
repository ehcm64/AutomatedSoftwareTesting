## Summary

The `FULL JOIN` followed by an `INNER JOIN` with an `IS NULL` condition on a join column produces incorrect rows.

## Minimized query

```sql
CREATE TABLE t1 (a INTEGER, b INTEGER);
CREATE TABLE t2 (c INTEGER, d INTEGER);
CREATE TABLE t3 (e TEXT, f TEXT);
INSERT INTO t1 VALUES (1, 1);
INSERT INTO t2 VALUES (1, 2);
INSERT INTO t3 VALUES ('abc', 'def');
SELECT * FROM t1 FULL JOIN t2 ON (t2.c = t1.a) INNER JOIN t3 ON (t2.d IS NULL);
```

## Actual output

```sql
1|1|||abc|def
||1|2|abc|def
```

## Expectation

```sql
<empty result set>
```

The row `t1.a = 1` matches the row `t2.c = 1`, so the `FULL JOIN` produces a single matched row `(1, 1, 1, 2)` with no unmatched rows on either side. The subsequent `INNER JOIN` with `t3` on `t2.d IS NULL` evaluates to `2 IS NULL = FALSE`, eliminating the row. Thus, the result should be empty. Instead of that, the binary produces two rows that resemble the unmatched sides of a FULL JOIN.