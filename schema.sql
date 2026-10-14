CREATE TABLE IF NOT EXISTS allergen (
	kod INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	nev TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS felhasznalo (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	nev TEXT NOT NULL COLLATE NOCASE,
	cim TEXT NOT NULL,
	telszam TEXT NOT NULL,
	isAdmin INTEGER NOT NULL CHECK (isAdmin IN (0, 1)),
	email TEXT NOT NULL UNIQUE COLLATE NOCASE,
	password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS futar (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	nev TEXT NOT NULL COLLATE NOCASE,
	telszam TEXT NOT NULL DEFAULT +361235678,
	jarmu TEXT NOT NULL CHECK (jarmu IN ('auto', 'dron', 'bicikli', 'motor')),
	ember INTEGER NOT NULL DEFAULT 0 CHECK (jarmu != 'dron' OR ember = 0),
	allapot TEXT NOT NULL DEFAULT 'elerheto' CHECK (allapot IN ('elerheto', 'uton', 'szunet')),
	hatosugar_km INTEGER NOT NULL CHECK (hatosugar_km > 0)
);

CREATE TABLE IF NOT EXISTS futar_pozicio (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	futarID INTEGER NOT NULL,
	gps_x REAL NOT NULL,
	gps_y REAL NOT NULL,
	cim TEXT NOT NULL,
	FOREIGN KEY (futarID) REFERENCES futar(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS rendeles (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	felhasznalo_id INTEGER NOT NULL,
	futar_id INTEGER NOT NULL,
	cim TEXT NOT NULL,
	prioritas INTEGER NOT NULL DEFAULT 0 CHECK (prioritas IN (0, 1)),
	fizetesi_mod TEXT NOT NULL CHECK (fizetesi_mod IN ('keszpenz', 'kartya')),
	jatt INTEGER CHECK (jatt IS NULL OR (jatt > 0 AND fizetesi_mod = 'kartya')),
	szamla INTEGER NOT NULL CHECK (szamla IN (0, 1)),
	km INTEGER NOT NULL CHECK (km > 0),
	statusz TEXT NOT NULL DEFAULT 'új',
	ertekeles INTEGER CHECK (ertekeles IN (1, 2, 3, 4, 5)),
	FOREIGN KEY (felhasznalo_id) REFERENCES felhasznalo(id) ON DELETE CASCADE,
	FOREIGN KEY (futar_id) REFERENCES futar(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS termek (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	tipus TEXT NOT NULL DEFAULT 'etel' CHECK (tipus IN ('etel', 'ital')),
	nev TEXT NOT NULL COLLATE NOCASE,
	fogas TEXT NOT NULL,
	leiras TEXT,
	ar INTEGER NOT NULL CHECK (ar >= 0),
	elkeszitesi_ido INTEGER,
	prioritas INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rendeles_tetel (
	rendeles_id INTEGER NOT NULL,
	termek_id INTEGER NOT NULL,
	db INTEGER NOT NULL DEFAULT 1 CHECK (db >= 1),
	PRIMARY KEY (rendeles_id, termek_id),
	FOREIGN KEY (rendeles_id) REFERENCES rendeles(id) ON DELETE CASCADE,
	FOREIGN KEY (termek_id) REFERENCES termek(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS termek_allergen (
	termek_id INTEGER NOT NULL,
	allergen_kod INTEGER NOT NULL,
	PRIMARY KEY (termek_id, allergen_kod),
	FOREIGN KEY (allergen_kod) REFERENCES allergen(kod) ON DELETE CASCADE,
	FOREIGN KEY (termek_id) REFERENCES termek(id) ON DELETE CASCADE
);

CREATE VIEW IF NOT EXISTS v_allergenes_etelek AS
SELECT t.id AS termek_id, t.nev AS termek, t.ar,
       a.kod AS allergen_kod, a.nev AS allergen
FROM termek t
JOIN termek_allergen ta ON t.id = ta.termek_id
JOIN allergen a ON ta.allergen_kod = a.kod
WHERE t.tipus = 'etel';

CREATE VIEW IF NOT EXISTS v_elerheto_futarok AS
SELECT f.id, f.nev, f.telszam, f.jarmu, f.ember, f.hatosugar_km,
       fp.gps_x, fp.gps_y, fp.cim
FROM futar f
LEFT JOIN futar_pozicio fp ON f.id = fp.futarID
WHERE f.allapot = 'elerheto';

CREATE VIEW IF NOT EXISTS v_etelek AS
SELECT id, nev, fogas, leiras, ar, elkeszitesi_ido, prioritas
FROM termek
WHERE tipus = 'etel';

CREATE VIEW IF NOT EXISTS v_futar_poziciok AS
SELECT f.id AS futar_id, f.nev AS futar, f.jarmu, f.ember,
       f.allapot, f.hatosugar_km, fp.gps_x, fp.gps_y,
       fp.cim AS aktualis_cim
FROM futar f
LEFT JOIN futar_pozicio fp ON f.id = fp.futarID;

CREATE VIEW IF NOT EXISTS v_italok AS
SELECT id, nev, fogas, leiras, ar, prioritas
FROM termek
WHERE tipus = 'ital';

CREATE VIEW IF NOT EXISTS v_kosar AS
SELECT r.id AS rendeles_id, r.felhasznalo_id, rt.termek_id,
       t.nev AS termek, t.ar AS egysegar, rt.db,
       rt.db * t.ar AS osszeg
FROM rendeles r
JOIN rendeles_tetel rt ON r.id = rt.rendeles_id
JOIN termek t ON rt.termek_id = t.id
WHERE r.statusz = 'kosar';

CREATE VIEW IF NOT EXISTS v_prioritasos_rendelesek AS
SELECT r.id AS rendeles_id, f.nev AS felhasznalo, r.cim,
       fu.nev AS futar, fu.jarmu, r.km, r.statusz, r.fizetesi_mod
FROM rendeles r
JOIN felhasznalo f ON r.felhasznalo_id = f.id
JOIN futar fu ON r.futar_id = fu.id
WHERE r.prioritas = 1;

CREATE VIEW IF NOT EXISTS v_rendeles_osszeg AS
SELECT r.id AS rendeles_id, f.nev AS felhasznalo,
       r.cim AS szallitasi_cim, r.fizetesi_mod, r.jatt,
       SUM(rt.db * t.ar) AS termek_osszeg,
       COALESCE(r.jatt, 0) AS jatt_osszeg,
       SUM(rt.db * t.ar) + COALESCE(r.jatt, 0) AS vegosszeg,
       r.statusz
FROM rendeles r
JOIN felhasznalo f ON r.felhasznalo_id = f.id
JOIN rendeles_tetel rt ON r.id = rt.rendeles_id
JOIN termek t ON rt.termek_id = t.id
GROUP BY r.id;

CREATE VIEW IF NOT EXISTS v_rendeles_tetelek AS
SELECT r.id AS rendeles_id, f.nev AS felhasznalo,
       t.id AS termek_id, t.nev AS termek, t.tipus,
       rt.db AS darab, t.ar AS egysegar, rt.db * t.ar AS tetel_ertek
FROM rendeles r
JOIN felhasznalo f ON r.felhasznalo_id = f.id
JOIN rendeles_tetel rt ON r.id = rt.rendeles_id
JOIN termek t ON rt.termek_id = t.id;

CREATE VIEW IF NOT EXISTS v_rendelesek AS
SELECT r.id AS rendeles_id, f.nev AS felhasznalo,
       f.cim AS felhasznalo_cim, f.telszam AS felhasznalo_telefon,
       fu.nev AS futar, fu.jarmu, fu.allapot AS futar_allapot,
       r.cim AS szallitasi_cim, r.prioritas, r.fizetesi_mod,
       r.jatt, r.szamla, r.km, r.statusz, r.ertekeles
FROM rendeles r
JOIN felhasznalo f ON r.felhasznalo_id = f.id
JOIN futar fu ON r.futar_id = fu.id;

CREATE VIEW IF NOT EXISTS v_szamlas_rendelesek AS
SELECT r.id AS rendeles_id, f.nev AS felhasznalo, f.email,
       f.cim AS ugyfel_cim, r.cim AS szallitasi_cim,
       r.fizetesi_mod, r.statusz
FROM rendeles r
JOIN felhasznalo f ON r.felhasznalo_id = f.id
WHERE r.szamla = 1;

CREATE VIEW IF NOT EXISTS v_termek_allergen AS
SELECT t.id, t.nev AS termek_nev, t.tipus, t.fogas, t.ar,
       t.elkeszitesi_ido, GROUP_CONCAT(a.nev, ', ') AS allergenek
FROM termek t
LEFT JOIN termek_allergen ta ON t.id = ta.termek_id
LEFT JOIN allergen a ON ta.allergen_kod = a.kod
GROUP BY t.id;

CREATE VIEW IF NOT EXISTS v_termekek AS
SELECT id, tipus, nev, fogas, leiras, ar, elkeszitesi_ido, prioritas
FROM termek;

CREATE INDEX IF NOT EXISTS id_felhasznalo_nev
ON felhasznalo(nev COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS id_futar_allapot_jarmu
ON futar(allapot, jarmu);
CREATE INDEX IF NOT EXISTS id_futar_nev
ON futar(nev COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS id_futar_pozicio_futarID
ON futar_pozicio(futarID);
CREATE INDEX IF NOT EXISTS id_futar_pozicio_futarID_forditott
ON futar_pozicio(futarID);
CREATE INDEX IF NOT EXISTS id_rendeles_felhasznalo_id
ON rendeles(felhasznalo_id);
CREATE INDEX IF NOT EXISTS id_rendeles_felhasznalo_id_forditott
ON rendeles(felhasznalo_id);
CREATE INDEX IF NOT EXISTS id_rendeles_futar_id
ON rendeles(futar_id);
CREATE INDEX IF NOT EXISTS id_rendeles_futar_id_forditott
ON rendeles(futar_id);
CREATE INDEX IF NOT EXISTS id_rendeles_futar_statusz
ON rendeles(futar_id, statusz);
CREATE INDEX IF NOT EXISTS id_rendeles_statusz
ON rendeles(statusz);
CREATE INDEX IF NOT EXISTS id_rendeles_tetel_termek_id
ON rendeles_tetel(termek_id);
CREATE INDEX IF NOT EXISTS id_rendeles_tetel_termek_id_forditott
ON rendeles_tetel(termek_id);
CREATE INDEX IF NOT EXISTS id_termek_allergen_allergen_kod
ON termek_allergen(allergen_kod);
CREATE INDEX IF NOT EXISTS id_termek_allergen_allergen_kod_forditott
ON termek_allergen(allergen_kod);
CREATE INDEX IF NOT EXISTS id_termek_nev
ON termek(nev COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS id_termek_tipus
ON termek(tipus);