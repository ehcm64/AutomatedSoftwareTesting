CREATE TABLE t0 (
    c1 
);
SELECT 
     subq1.c13 AS c18
FROM (SELECT FALSE AS c13
   FROM (SELECT      t1.c1 AS c12
      FROM t0 AS t1
      WHERE 89 > t1.c1
      LIMIT 2316622805712276698 ) as subq0
   WHERE true
   ) as subq1
WHERE subq1.c13 = 
 CASE subq1.c13 WHEN subq1.c13 = subq1.c13 THEN subq1.c13
      ELSE subq1.c13
 END OR subq1.c13 = NULLIF(subq1.c13, subq1.c13) OR subq1.c13 IS NOT NULL AND subq1.c13 = subq1.c13
;