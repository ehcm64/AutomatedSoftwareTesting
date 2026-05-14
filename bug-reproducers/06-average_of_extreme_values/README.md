## Summary

The `AVG()` function on a column containing `INT64_MIN` and `INT64_MAX` returns `0.0` instead of the correct result.

## Minimized query

```sql
CREATE TABLE t1 (x INTEGER);
INSERT INTO t1 VALUES (-9223372036854775808);
INSERT INTO t1 VALUES (9223372036854775807);
SELECT AVG(x) FROM t1;
```

## Actual output

```sql
0.0
```

## Expectation

```sql
-0.5
```

The two values are `INT64_MIN` (`-9223372036854775808`) and `INT64_MAX` (`9223372036854775807`). Their correct integer sum is `-1`, giving an average of `AVG = -1 / 2 = -0.5`, but the patched binary returns `0.0`. The `SUM` function for the same numbers works fine, so it's likely a bug in the average function.