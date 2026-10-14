# Futárszolgálat-adatbázis: repóáttekintés

## A projekt célja

A repó egy Python-alapú futárszolgálati mintaprojekt. A SQLite-adatbázisban
felhasználókat, futárokat, futárpozíciókat, termékeket és rendeléseket kezel.
Az üzleti objektumokat a modellréteg írja le, az adatbázis-műveleteket az
adatkezelő modul végzi, a HTTP-s felületet pedig egy FastAPI-alkalmazás adja.

## Fájlszerkezet

| Fájl | Szerep |
| --- | --- |
| `modellek.py` | Az üzleti objektumok, adatellenőrzések és néhány üzleti szabály. Jelszóhash-elés és -ellenőrzés is itt található. |
| `adatbazis.py` | SQLite-kapcsolat, séma-ellenőrzés és migrációk, valamint a modellek mentése, betöltése, módosítása, törlése és szűrése. |
| `schema.sql` | A táblák, nézetek, indexek, kulcsok, alapértékek és SQL-szintű megszorítások kezdeti definíciója. |
| `api.py` | FastAPI-alkalmazás, kérésmodellek és HTTP-végpontok. |
| `requirements.txt` | A futtatáshoz szükséges Python-csomagok verziótartományai: FastAPI és Uvicorn. |
| `render.yaml` | Render webszolgáltatás-konfiguráció; telepítéskor függőségeket telepít, majd Uvicornnal indítja az API-t. |
| `.gitignore` | Kizárja a Python gyorsítótárát, a virtuális környezetet és a `.env` fájlokat. |
| `futarszolgalat.db` | Az `etelrendelesvegleges.db.sql` dumpból betöltött SQLite-adatbázis, a dump adataival, nézeteivel és indexeivel. |
| `ATTEKINTES.md` | Ez a dokumentum. |

## Működési rétegek

### Modellek – `modellek.py`

Az `Allergen`, `Felhasznalo`, `Futar`, `FutarPozicio`, `Termek`,
`RendelesTetel` és `Rendeles` adat-osztályok az alkalmazás fogalmait képviselik.
Az objektumok konstruktorai többek között ellenőrzik a jármű- és rendelési
állapotokat, a fizetési módot, a hatótávot, az árat, a borravaló feltételeit
és a rendelt mennyiséget.

A `Felhasznalo.regisztral()` a legalább 8 karakteres jelszót véletlen sóval,
PBKDF2-HMAC-SHA256 algoritmussal hash-eli; a modell jelszó-ellenőrzése
konstans idejű összehasonlítást használ. A modellréteg nem végez adatbázisba
írást. Az objektumok a `sorbol()` metódusokkal alakíthatók SQLite-sorokból
modellpéldánnyá.

A rendelés tételeket fogad, kiszámítja azok összegét, és összegyűjti a
termékeihez tartozó allergéneket.

### Adatbázis – `adatbazis.py` és `schema.sql`

Az adatbázis helye az `adatbazis.py` fájl könyvtára melletti
`futarszolgalat.db`; nem a munkakönyvtártól függ. A `kapcsolat()` kontextuskezelő
bekapcsolja az idegen kulcsok ellenőrzését, sikeres művelet után commitol,
hiba esetén rollbackel, majd lezárja a kapcsolatot.

Az első kapcsolatkor az adatkezelő lefuttatja a `schema.sql`-t, ha még nincsenek
táblák. Meglévő adatbázisban szükség esetén kiegészíti a felhasználói
oszlopokat, illetve migrálja a rendelés borravaló-megszorítását. A külön
`migracio_felhasznalo()` a régi, még sima szövegként tárolt jelszavakat hash-eli,
és egyedi indexet hoz létre az e-mail-címre; ezt a függvényt külön kell
meghívni, nem fut le automatikusan minden kapcsolódáskor.

Az adatbázis-kezelő függvények a következő területeket fedik le:

- felhasználó létrehozása, lekérdezése, módosítása, törlése és bejelentkeztetése;
- futár létrehozása, lekérdezése és állapotának módosítása, valamint az
  elérhető futárok szűrése;
- futárpozíciók rögzítése és lekérdezése;
- termékek és allergénkapcsolataik mentése, illetve lekérdezése;
- rendelések és rendelési tételek tranzakciós mentése, betöltése és
  státuszmódosítása;
- felhasználók, futárok, termékek és rendelések több szempont szerinti
  szűrése, rendezése és lapozása.

A dinamikus szűrésnél az értékek paraméterezett SQL-paraméterként kerülnek a
lekérdezésbe; a rendezhető oszlopokat engedélyezett listák korlátozzák.

Az `schema.sql` fő táblái és kapcsolatai:

- `felhasznalo`: felhasználói adatok, kötelező e-mail és jelszóhash, valamint
  adminisztrátori jelző;
- `futar`: futár adatai, járműve, emberi vagy drón jellege, állapota és
  hatósugara;
- `futar_pozicio`: futárhoz tartozó GPS-koordináták és címek;
- `termek`: étel vagy ital neve, fogása, leírása, ára és elkészítési ideje;
- `allergen`: allergénkód és név;
- `termek_allergen`: termék és allergén közötti kapcsolótábla;
- `rendeles`: felhasználóhoz és futárhoz rendelt rendelés adatai;
- `rendeles_tetel`: rendelés és termék közötti kapcsolat, darabszámmal.

A séma idegen kulcsokat és megszorításokat alkalmaz. Például a jármű, fizetési
mód és prioritás megengedett értékei korlátozottak, a hatótávnak és a
rendelt darabszámnak pozitívnak kell lennie, a termék ára nem lehet negatív.
A törlési szabályok több kapcsolódó rekordra is kiterjednek (`ON DELETE
CASCADE`).

Az adatbázisban ezen felül 13 előre definiált nézet és 17 névvel ellátott
lekérdezési index található. A felhasználói e-mailre a jelszómigráció egy
külön egyedi indexet is létrehoz. A nézetek többek között allergénes ételeket,
elérhető futárokat, kosártartalmat, rendelési tételeket és számlaigényes
rendeléseket tesznek egyszerűbben lekérdezhetővé. Az indexek a neveken,
állapotokon és idegen kulcsokon végzett kereséseket segítik. Friss adatbázis
indításakor ezeket is létrehozza a `schema.sql`.

### HTTP API – `api.py`

Az alkalmazás neve `Futárszolgálat API`. A jelenlegi útvonalak:

| Metódus | Útvonal | Művelet |
| --- | --- | --- |
| `POST` | `/felhasznalo` | Felhasználó regisztrálása, `201` válasszal. |
| `GET` | `/felhasznalo/{felhasznalo_id}` | Felhasználó lekérdezése. |
| `GET` | `/felhasznalo/{felhasznalo_id}/rendelesek` | A felhasználó rendeléseinek listázása. |
| `GET` | `/futar/elerheto` | Elérhető futárok listázása, opcionális `jarmu` szűrővel. |
| `GET` | `/futar/{futar_id}` | Futár lekérdezése. |
| `PATCH` | `/futar/{futar_id}/allapot` | Futárállapot módosítása. |
| `GET` | `/futar/{futar_id}/rendelesek` | A futár rendeléseinek listázása. |
| `GET` | `/termek/{termek_id}` | Termék lekérdezése. |
| `POST` | `/rendeles` | Rendelés létrehozása a termékazonosítókból és darabszámokból. |
| `GET` | `/rendeles/{rendeles_id}` | Rendelés lekérdezése. |
| `PATCH` | `/rendeles/{rendeles_id}/statusz` | Rendelés státuszának módosítása. |

A felhasználó-válasz külön összeállított mezőlistát használ, ezért a
jelszóhash nem kerül bele. A nem található rekordoknál az API `404` választ,
az üzleti validációs hibáknál jellemzően `400` választ ad. A FastAPI
automatikus interaktív dokumentációja a futó alkalmazás `/docs` útvonalán
érhető el.

## Indítás és telepítés

Python 3.10 vagy újabb szükséges a kódban használt típusannotációkhoz.
Windows PowerShellben virtuális környezetből például így indítható:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn api:app --reload
```

Ezután az API alapértelmezés szerint a `http://127.0.0.1:8000` címen érhető
el, a dokumentáció pedig a `http://127.0.0.1:8000/docs` címen. A Render
konfiguráció ugyanezt az `api:app` ASGI-alkalmazást indítja, a szolgáltatás
által megadott porton.

## Fontos határok és megjegyzések

- Az adatbázisséma a felhasználóknál kötelezővé teszi az e-mail-címet és a
  jelszóhash-t. A modell régi, bejelentkezés nélküli rekordot is képes
  reprezentálni, de mentéskor az adatkezelő ezt egyértelmű validációs hibával
  elutasítja.
- Az adatbázisréteg több műveletet biztosít, mint amennyit a HTTP API
  jelenleg kitesz. Például a kódban van bejelentkeztetési függvény, de nincs
  hozzá API-végpont; a futárok, termékek és allergének létrehozására sincs
  jelenleg HTTP-végpont.
- Az API-rendeléskérés kötelező, 1–5 közötti `ertekeles` mezőt kér, és a
  `rendeles_letrehoz()` is elutasítja a `None` értéket. Az adatbázis oszlopa
  nullable, de a nem-NULL értékeket ugyanilyen tartományra korlátozza.
- A SQLite-adatbázis fájl útvonala az alkalmazáskód mellett van rögzítve; a
  repó nem állít be külön, környezeti változóból vezérelt adatbázis-helyet.
- A `adatbazis.py` közvetlen futtatásakor annak próbarészlete valódi
  adatbázis-műveleteket végez és tesztfelhasználót hoz létre.
- A végleges SQL-dump felhasználói jelszavait a
  `migracio_felhasznalo()` függvénnyel PBKDF2 hash-re kell migrálni, mielőtt
  ezek a rekordok a modellrétegen keresztül beolvashatók. A repó adatbázisában
  ez a migráció végrehajtásra került.
- A rendelés borravaló-megszorításának régi változatáról az adatkezelő
  automatikusan az újabb változatra migrál. A táblát újraépítő migráció a
  rendeléshez tartozó saját indexeket és triggereket is megőrzi.

## Adatbázis-betöltés és ellenőrzés

Az `etelrendelesvegleges.db.sql` dump bekerült a `futarszolgalat.db` adatbázisba.
Az importált adatbázis 14 allergént, 4 felhasználót, 1000 futárt, 1000
futárpozíciót, 1000 terméket, 1360 termék-allergén kapcsolatot, 1000 rendelést
és 1000 rendelési tételt tartalmaz. A SQLite integritásvizsgálata sikeres,
idegenkulcs-sértés nem volt.

Az import után a 4 régi jelszó PBKDF2-SHA256 hash-re migrálódott, így a
felhasználói rekordok már beolvashatók a modellrétegen keresztül. A
kompatibilitást az első felhasználó, futár, termék és rendelés betöltésével is
ellenőriztem.
