## Summary

The partial index `WHERE c0 NOT NULL` leads to an incorrect query result when the query predicate is `(t0.c0 IS FALSE) IS FALSE`.

## Minimized query

```sql
CREATE TABLE t0(c0);
INSERT INTO t0(c0) VALUES (NULL);
CREATE INDEX i0 ON t0(1) WHERE c0 NOT NULL;
SELECT 1 FROM t0 WHERE (t0.c0 IS FALSE) IS FALSE;
```

## Actual output

```sql
<empty result set>
```

## Expectation

```sql
1
```

The query should return one row since the single row has `c0 = NULL` and `(NULL IS FALSE) IS FALSE` evaluates to `TRUE`. The existence of the bug is confirmed by the fact that the removal of the partial index leads to a different result, and an index should not change the semantics of the query.