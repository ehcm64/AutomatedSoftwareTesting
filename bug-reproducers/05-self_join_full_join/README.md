## Summary

The `SELECT DISTINCT` combined with a self-join `FULL JOIN` leads to an incorrect result.

## Minimized query

```sql
CREATE TABLE artists (id INTEGER PRIMARY KEY);
INSERT INTO artists VALUES (1);
SELECT DISTINCT artists.* FROM artists FULL JOIN artists AS b WHERE artists.id <> 1;
```

## Actual output

```sql
1
```

## Expectation

```sql
<empty result set>
```

The `artists` contains a single row with `id = 1`. The `WHERE artists.id <> 1` condition evaluates to `FALSE`, so no rows should be returned.