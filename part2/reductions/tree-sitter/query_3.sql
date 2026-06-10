CREATE TABLE  table_2  (     BIGINT   ) ;
CREATE TABLE    table_3 (   INT, table_3_c1  ) ;
 
INSERT INTO table_3  VALUES (-2, NULL) ;
 
 SELECT  * FROM table_3, table_2 WHERE  ( SELECT  table_3_c1   LIMIT NULL ) ;
