CREATE TABLE artists (id INTEGER PRIMARY KEY, name TEXT(255));
CREATE TABLE albums (id INTEGER PRIMARY KEY, name TEXT(255), artist_id INTEGER);
INSERT INTO artists (name) VALUES ('Ar');
INSERT INTO albums (name, artist_id) VALUES ('Al', 1);
SELECT DISTINCT artists.* FROM artists FULL JOIN artists AS b ON artists.id = artists.id WHERE (NOT artists.id IN (SELECT albums.artist_id FROM albums WHERE ((name = 'Al') AND (NOT albums.artist_id IS NULL) AND (albums.id IN (SELECT id FROM (SELECT albums.id, ROW_NUMBER() OVER (PARTITION BY albums.artist_id ORDER BY name) AS x FROM albums WHERE (name = 'Al')) AS t1 WHERE (x = 1))) AND (albums.id IN (1, 2)))));