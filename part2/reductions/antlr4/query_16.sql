CREATE TABLE t0 (
            c0 ,
            c1 ,
            c2 ,
            c3 
        );
        SELECT      subq10.c17 AS c13
         FROM (SELECT subq9.c8 AS c14,  TRUE AS c16, subq9.c10 AS c17
            FROM (SELECT t59.c3 AS c4,    t59.c2 AS c8,  t59.c0 AS c10   
               FROM t0 AS t59
                 LEFT OUTER JOIN t0 AS t60
               WHERE t59.c3 > t59.c2
               ORDER BY   c4) as subq9
            WHERE EXISTS (
             SELECT    t62.c0 AS c7
              FROM   t0 AS t62
              WHERE t62.c1 <> t62.c1
             )
            ORDER BY c16 ) as subq10
         WHERE 51 < subq10.c14 OR subq10.c17 =
          CASE subq10.c16 WHEN subq10.c16 IS NULL THEN subq10.c16
               ELSE subq10.c16
          END
          ;