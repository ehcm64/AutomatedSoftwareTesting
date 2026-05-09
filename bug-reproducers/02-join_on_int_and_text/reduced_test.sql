CREATE TABLE map_integer (id INT, name);
INSERT INTO map_integer VALUES(1,'a');
CREATE TABLE map_text (id TEXT, name);
INSERT INTO map_text VALUES('4','e');
CREATE TABLE data (id TEXT, name);
INSERT INTO data VALUES(1,'abc');
INSERT INTO data VALUES('4','xyz');
CREATE VIEW idmap as SELECT * FROM map_integer UNION SELECT * FROM map_text;
SELECT * FROM data JOIN idmap USING(id);