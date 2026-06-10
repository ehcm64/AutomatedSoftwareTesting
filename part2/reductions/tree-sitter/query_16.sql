CREATE TABLE t0 (
            c0 ,
            c1 ,
            c2 ,
            c3 
        );
        WITH cte0 AS (
        SELECT   c4, (NULL,FALSE)  ,   c6, t5.c0  ,   c8, t9.c0  ,   c10, t11.c3  ,
            c12, t10.c0  ,   c14, t9.c0  ,   c16
         
        ), cte1 AS (
        SELECT t12.c3  ,   c9,
          CASE WHEN t12.c2 < t12.c2 THEN 
                subq0.c5
          END  ,   c11, t12.c2  ,   c13, t12.c3  ,   c15, t12.c1  
          
              
              
              
             
         
          
         ,  NOCASE
        ), cte2 AS (
        SELECT   c4,   c5,   c6,   c7,   c8,   c9,
            c6,   c7
         
        ), cte3 AS (
        SELECT t26.  c4, t26.  c5, subq1.  c6, subq2.  c7, subq1.  c8
         
        ), cte4 AS (
        SELECT   c4
         
        ), cte5 AS (
        SELECT subq3.c4  ,   c6
         
        ), cte6 AS (
        SELECT changes()  
         
        ), cte7 AS (
        SELECT   c10, X'8ae13f1c'  ,   c12, subq5.c8  
         
        ), cte8 AS (
        SELECT   c6, subq6.c4  
         
        ), cte9 AS (
        SELECT   c4, t39.c0  
         
        ), cte10 AS (
        SELECT
            c12,
            c13,   c14,   c15,   c16,   c17,   c18,
            c19,   c20,   c21,   c22,   c23
         
        ), cte11 AS (
        SELECT subq8.c5  ,   c5,   c6
            
            
           
         
        ), cte12 AS (
        SELECT   c4
         
        )SELECT subq10.c17  , subq10.c16  , subq10.c15  , subq10.c16  , subq10.c14  , subq10.c17  
         FROM (SELECT subq9.c8  c14, subq9.c11  c15, TRUE  c16, subq9.c10  c17
            FROM (SELECT t59.c3  c4, t60.c0  , t59.c3  c6, t59.c0  , t59.c2  c8, t60.c0  , t59.c0  c10, t60.c1  c11, t59.c3  c12, t59.c1  
               FROM t0  t59
                   JOIN t0  t60
                  ON (   NULL)
               
               ORDER BY c12 , c6 , c4)  subq9
            
            ORDER BY c16 )  subq10
         WHERE 51 < subq10.c14 OR subq10.c17 =
          CASE subq10.c16 WHEN subq10.c16 IS NULL THEN subq10.c16
               ELSE subq10.c16
          END
          
          ;
