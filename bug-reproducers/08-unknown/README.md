## Summary

The `LOG2()` function returns a result off by a few decimals for certain inputs.

## Minimized query

```sql
SELECT LOG2(100);
```

## Actual output

```sql
6.64385618977473
```

## Expectation

```sql
6.64385618977472
```

The true value of `LOG2(100)` is `6.643856189774724...`, which rounds to `6.64385618977472`. The pathced binary returns `6.64385618977473`. There were likely some floating-point operations reordered which led to a reduction in precision.