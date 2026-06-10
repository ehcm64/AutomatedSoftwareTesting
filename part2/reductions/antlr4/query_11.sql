CREATE TABLE V (l   ,  BOOLEAN);
INSERT INTO V SELECT * FROM (VALUES ((NOT NULL), false), (NULL, NULL)) AS A WHERE ((false <> true) <> (NOT true));
SELECT * FROM V AS K WHERE (NOT (( + 52) < ( - ((18 * 82) / (+47)))));