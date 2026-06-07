CREATE TABLE artists (id INTEGER PRIMARY KEY);
INSERT INTO artists VALUES (1);
SELECT DISTINCT artists.* FROM artists FULL JOIN artists AS b WHERE artists.id <> 1;