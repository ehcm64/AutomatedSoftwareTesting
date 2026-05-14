CREATE TABLE t1(n int);
SELECT count(*) FROM t1 HAVING count(*)>=4;