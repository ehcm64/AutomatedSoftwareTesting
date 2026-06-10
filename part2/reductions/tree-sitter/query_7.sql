CREATE TABLE t0 (c0, c1);

CREATE VIEW view1 AS VALUES ( (0x7067e3cec226b60e % 904.1747253662293) );
SELECT  ufulnp.c0  , ufulnp.c1   FROM ( t0 ) AS ufulnp WHERE FALSE;
;

;
SELECT * FROM ( view1 ) ;
