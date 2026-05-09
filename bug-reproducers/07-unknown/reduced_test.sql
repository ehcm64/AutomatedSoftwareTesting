CREATE TABLE t1(n int, log int);
SELECT log, count(*) FROM t1 HAVING count(*)>=4 ORDER BY log;