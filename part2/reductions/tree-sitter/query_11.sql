CREATE TABLE V ( BOOLEAN  , q );

INSERT INTO V SELECT * FROM (VALUES (( NULL), false), (NULL, NULL))   WHERE ((false <> true) <> (NOT true));
SELECT * FROM V   ;
