## Summary

The patched binary rejects a `HAVING` clause without a preceding `GROUP BY` with a parse error, even though this is valid SQL.

## Minimized query

```sql
CREATE TABLE t1(n int);
SELECT count(*) FROM t1 HAVING count(*)>=4;
```

## Actual output

```sql
Parse error near line 1: a GROUP BY clause is required before HAVING
```

## Expectation

```sql
<empty result set>
```

In SQL, `HAVING` without `GROUP BY` is valid. The query should treat the entire result set as one group. The query should execute and return an empty result since `count(*) >= 4` is `FALSE` on an empty table.