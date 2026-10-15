# Futárszolgálat-adatbázis: repóáttekintés

## A projekt célja

A repó egy Python-alapú futárszolgálati mintaprojekt. A SQLite-adatbázisban
felhasználókat, futárokat, futárpozíciókat, termékeket és rendeléseket kezel.
Az üzleti objektumokat a modellréteg írja le, az adatbázis-műveleteket az
adatkezelő modul végzi, a HTTP-s felületet pedig egy FastAPI-alkalmazás adja.

## Fájlszerkezet

| Fájl | Szerep |
| --- | --- |
| `modellek.py` | Az üzleti objektumok, adatellenőrzések és néhány üzleti szabály. |
| `adatbazis.py` | Kapcsolódás a meglévő SQLite-adatbázishoz, valamint a modellek mentése, betöltése, módosítása, törlése és szűrése. Nem hoz létre vagy migrál sémát. |
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

A `Felhasznalo.regisztral()` legalább 8 karakteres jelszót fogad el, és a
dumpnak megfelelően közvetlenül a `password` oszlopba írja; a bejelentkezés
közvetlen szöveges összehasonlítást használ. Ez a tárolási mód nem biztonságos,
jelszót valós felhasználói fiókokhoz vagy éles rendszerben nem szabad így
tárolni. A modellréteg nem végez adatbázisba írást. Az objektumok a `sorbol()`
metódusokkal alakíthatók SQLite-sorokból modellpéldánnyá.

A rendelés tételeket fogad, kiszámítja azok összegét, és összegyűjti a
termékeihez tartozó allergéneket.

### Adatbázis – `adatbazis.py` és `futarszolgalat.db`

Az adatbázis helye az `adatbazis.py` fájl könyvtára melletti
`futarszolgalat.db`; nem a munkakönyvtártól függ. A `kapcsolat()` csak már
létező adatbázist nyit meg, bekapcsolja az idegen kulcsok ellenőrzését,
sikeres művelet után commitol, hiba esetén rollbackel, majd lezárja a
kapcsolatot. Nem készít új adatbázist, nem futtat DDL-t, és nem változtatja meg
a táblák, oszlopok, kulcsok, nézetek vagy indexek szerkezetét. A futtatáshoz a
megadott adatbázisfájlnak és a várt tábláknak már létezniük kell.

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

Az adatbázis dumpjának fő táblái és kapcsolatai:

- `felhasznalo`: felhasználói adatok, kötelező e-mail és szöveges jelszó, valamint
  adminisztrátori jelző;
- `futar`: futár adatai, járműve, az `ember` mező, állapota és hatósugara;
- `futar_pozicio`: futárhoz tartozó GPS-koordináták és címek;
- `termek`: étel vagy ital neve, fogása, leírása, ára és elkészítési ideje;
- `allergen`: allergénkód és név;
- `termek_allergen`: termék és allergén közötti kapcsolótábla;
- `rendeles`: felhasználóhoz és futárhoz rendelt rendelés adatai;
- `rendeles_tetel`: rendelés és termék közötti kapcsolat, darabszámmal.

Az adatbázis saját idegen kulcsokat és megszorításokat alkalmaz; például a
jármű, fizetési mód és prioritás értékeit korlátozza. Az alkalmazás új
futároknál csak autót, biciklit és motort fogad el; az API sem az `ember`
mezőt, sem más járműtípust nem tesz elérhetővé. A rendelésmentés is csak
támogatott járműhöz enged rendelést társítani. Az `ember` mező az adatbázis
belső kezelése miatt változatlan marad. A futárpozíció idegen
kulcsánál a dump `ON DELETE RESTRICT` szabályt használ, a rendelésekhez és
kapcsolótáblákhoz több helyen `ON DELETE CASCADE` tartozik. Az adatbázisban 13
nézet és 17 névvel ellátott index található. Ezek részei a használt adatbázisnak,
de az alkalmazás nem hozza létre és nem módosítja őket.

### HTTP API – `api.py`

Az alkalmazás neve `Futárszolgálat API`. A jelenlegi útvonalak:

| Metódus | Útvonal | Művelet |
| --- | --- | --- |
| `POST` | `/bejelentkezes` | E-mail és jelszó ellenőrzése; siker esetén a publikus felhasználói adatokat adja vissza. Munkamenetet vagy tokent nem hoz létre. |
| `POST` | `/felhasznalo` | Felhasználó regisztrálása. |
| `GET` | `/felhasznalo` | Felhasználók keresése és lapozása. |
| `GET` | `/felhasznalo/{felhasznalo_id}` | Felhasználó lekérdezése azonosító alapján. |
| `GET` | `/felhasznalo/email/{email}` | Felhasználó lekérdezése e-mail-cím alapján. |
| `PUT` | `/felhasznalo/{felhasznalo_id}` | Felhasználói adatok cseréje/módosítása. |
| `DELETE` | `/felhasznalo/{felhasznalo_id}` | Felhasználó törlése; az adatbázis a kapcsolódó rendeléseket is törölheti. |
| `GET` | `/felhasznalo/{felhasznalo_id}/rendelesek` | A felhasználó rendelései. |
| `POST` | `/futar` | Futár felvétele. |
| `GET` | `/futar` | Futárok keresése és lapozása. |
| `GET` | `/futar/elerheto` | Elérhető futárok listázása, opcionális járműszűrővel. |
| `GET` | `/futar/allapotok` | A három adatbázis által elfogadott futárállapot és megnevezése. |
| `GET` | `/futar/szallitasra-alkalmas?km=5` | Elérhető futárok, akiknek a hatósugara legalább a megadott távolság. |
| `GET` | `/futar/{futar_id}` | Futár lekérdezése. |
| `PATCH` | `/futar/{futar_id}/allapot` | Futár állapotának módosítása. |
| `GET` | `/futar/{futar_id}/rendelesek` | A futár rendelései. |
| `POST` | `/futar/pozicio` | Futárpozíció rögzítése. |
| `GET` | `/futar/{futar_id}/poziciok` | Futárpozíciók lekérdezése, legújabb elöl. |
| `GET` | `/allergen` | Allergének listázása. |
| `POST` | `/termek` | Termék felvétele allergénkódokkal. |
| `GET` | `/termek` | Termékek keresése/szűrése és lapozása, allergénekkel. |
| `GET` | `/termek/{termek_id}` | Termék lekérdezése. |
| `POST` | `/rendeles` | Rendelés létrehozása a termékazonosítókból és darabszámokból. |
| `GET` | `/rendeles` | Rendelések keresése/szűrése és lapozása. |
| `GET` | `/rendeles/{rendeles_id}` | Rendelés lekérdezése a tételeivel. |
| `GET` | `/rendeles/{rendeles_id}/allergenek` | Az adott rendelés termékeiben előforduló allergének egyedi listája. |
| `PATCH` | `/rendeles/{rendeles_id}/statusz` | Rendelés státuszának módosítása; `lemondva` csak a lemondási művelettel állítható be. |
| `POST` | `/rendeles/{rendeles_id}/lemondas` | Lemondja a rendelést, ha a státusza `új` vagy `elfogadva`. |

A felhasználó-válasz külön összeállított mezőlistát használ, ezért a
jelszó nem kerül bele. A nem található rekordoknál az API `404` választ,
az üzleti validációs hibáknál jellemzően `400`, az adatbázis egyedi vagy CHECK
korlátozásainak ütközésekor `409` választ ad. A lemondási végpont `404`-et ad,
ha a rendelés nem létezik, és `409`-et, ha a rendelés már nem `új` vagy
`elfogadva` státuszú. A státuszellenőrzés és a lemondás egyetlen feltételes
SQL-módosításban történik; a státusz-végpont és az új rendelés létrehozása
nem használható ennek megkerülésére. A FastAPI
automatikus interaktív dokumentációja a futó alkalmazás `/docs` útvonalán
érhető el.

#### Elérés Renderből és PHP-ből

Az API Renderen beállított alapcímét a Render Dashboard szolgáltatásoldalán
lehet megnézni. Ne rögzítsd a szolgáltatás konkrét URL-jét a repóban; a PHP
alkalmazás konfigurációjából add meg, például `FUTARSZOLGALAT_API_URL`
környezeti változóként (a Render URL önmagában publikus cím, nem hozzáférési
jelszó vagy API-kulcs).

- Interaktív API-dokumentáció: `<API-alapcím>/docs`
- Példa elérhető futárok lekérésére:
  `GET <API-alapcím>/futar/elerheto`
- Példa 5 km-re alkalmas futárok lekérésére:
  `GET <API-alapcím>/futar/szallitasra-alkalmas?km=5`

A PHP backend teljes URL-re küldött HTTP-kéréssel, JSON-adatcserével hívja az
API-t; nem kell közvetlenül csatlakoznia a Python alkalmazáshoz vagy az SQLite
fájlhoz. A PHP GET-kérés például cURL-lel, az alapcímet környezeti
változóból olvasva:

```php
$apiBase = rtrim(getenv('FUTARSZOLGALAT_API_URL'), '/');
$ch = curl_init($apiBase . '/futar/elerheto');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$json = curl_exec($ch);
if ($json === false) {
    throw new RuntimeException(curl_error($ch));
}
$status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($status < 200 || $status >= 300) {
    throw new RuntimeException("A futár API HTTP $status hibát adott.");
}
$futarok = json_decode($json, true, 512, JSON_THROW_ON_ERROR);
```

Az API gyökérútvonala (`/`) nem szolgál ki kezdőoldalt, ezért ott a `404 Not
Found` válasz normális; az API-dokumentáció és a végpontok ettől még a saját
útvonalaikon érhetők el. A PHP-szerverről indított HTTP-kéréshez a PHP cURL
kiterjesztésének engedélyezve kell lennie.

Az `adatbazis.py` minden alkalmazási szintű adatfüggvényéhez tartozik
HTTP-végpont: létrehozás, lekérdezés, módosítás/törlés, bejelentkezés és a
négy szűrőfüggvény is elérhető. A futárállapotok értékei az adatbázis CHECK
megszorítását követik: `elerheto`, `uton`, `szunet`; az állapotmódosító
végpont csak ezeket fogadja el. A szállításra alkalmas futárok lekérdezése az
`elerheto` állapotot és a `hatosugar_km >= km` feltételt alkalmazza. A
rendelési allergénlista a termékek allergénneveit egyedileg, rendezve adja
vissza. A kapcsolatkezelő és a belső, aláhúzással kezdődő segédfüggvények nem
külön végpontok. Az API listavégpontjai
alapértelmezésben 100 rekordot adnak, legfeljebb 1000-es lapmérettel.

### Az ERD üzleti folyamatai

Az `erd.drawio.png` az elvárt weboldali logikát vázolja fel:

- felhasználói regisztráció, bejelentkezés, profil és rendelési előzmények;
- étel/ital kínálat fogás, ár, prioritás és allergén szerinti böngészése;
- kosár tételeinek kezelése, majd a kosár rendelésként való leadása;
- rendelési cím, távolság, díjazás, fizetés/számlázás és rendelési státusz;
- futárállapotok és GPS-pozíciók, futárhoz rendelés, kiszállítás követése;
- adminisztrátori termék-, allergén-, futár- és rendeléskezelés, valamint
  kimutatások.

Az API az adatbázisban ténylegesen rendelkezésre álló függvényeket teszi
hívhatóvá. Az ERD néhány folyamata további, jelenleg nem létező üzleti logikát
igényel: nincs külön kosár/ideiglenes rendelés-életciklus, térképes
legközelebbi-futár vagy távolság-/díjszámítás, online fizetési szolgáltató,
számlakibocsátás, rendelés elfogadási/visszautasítási folyamat, illetve
riportfüggvény az adatbázisrétegben. Ezeket a meglévő CRUD- és szűrőfüggvények
önmagukban nem valósítják meg. A dump megszorítása miatt a jelenlegi
rendeléslétrehozás kártyás fizetést követel meg.

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

- A dump `felhasznalo` táblájában az e-mail és a jelszó kötelező. A jelszavak
  sima szövegként tárolódnak, ez a dump formátumának következménye, és nem
  biztonságos megoldás.
- Az adatbázisréteg több műveletet biztosít, mint amennyit a HTTP API
  üzleti folyamatként lefed: az adatbázisfüggvények mind elérhetők, de az ERD
  külső fizetési, kosár-, távolságszámítási és riportfolyamatai nem részei a
  jelenlegi adatkezelőnek.
- Az API-rendeléskérés kötelező, 1–5 közötti `ertekeles` mezőt kér, és a
  `rendeles_letrehoz()` is elutasítja a `None` értéket. Az adatbázis oszlopa
  nullable, de a nem-NULL értékeket ugyanilyen tartományra korlátozza.
- Jelszómódosítási funkció nincs, az ERD folyamatainak megfelelően a modellből
  is kikerült.
- A SQLite-adatbázis fájl útvonala az alkalmazáskód mellett van rögzítve; a
  repó nem állít be külön, környezeti változóból vezérelt adatbázis-helyet.
- Az alkalmazás adatokat olvas és módosít, de a tábla-, index- és nézetstruktúrát
  változatlanul hagyja. Az adatbázisfájl törlése vagy hiánya esetén nem
  inicializál helyette üres adatbázist.
- A dump `rendeles` táblájának `jatt` CHECK feltétele készpénzes rendelést nem
  enged menteni; ezt a modell már adatbázis-művelet előtt validálja.
- Jelenleg nincs API-kulcs, felhasználói munkamenet vagy szerepkör-alapú
  jogosultság-ellenőrzés. A végpontok a kérésnek megfelelően védelem nélkül
  érhetők el; internetes Render-telepítés előtt ezt külön rendezni kell.

## Adatbázis-betöltés és ellenőrzés

Az `etelrendelesvegleges.db.sql` dump állítja vissza a repó
`futarszolgalat.db` adatbázisát. Az eredeti dump 14 allergént, 4 felhasználót,
1000 futárt, 1000 futárpozíciót, 1000 terméket, 1360 termék-allergén
kapcsolatot, 1000 rendelést és 1000 rendelési tételt tartalmazott. A drónos
kiszállítások kivezetésekor 89 drónos futárt, 89 hozzájuk tartozó pozíciót,
valamint 86 rendelést és a hozzájuk tartozó rendelési tételeket töröltük. A
jelenlegi adatbázisban 911 futár, 911 futárpozíció, 914 rendelés és 914
rendelési tétel maradt; az adatbázis szerkezete nem változott, a megmaradt
futárok `ember` értékeit nem módosítottuk. A drónos rekordok törlése kizárólag
az adatokat érintette: a dump eredeti táblái, nézetei, indexei és
séma-megszorításai változatlanok maradtak. Az alkalmazásban nincs
séma-inicializáló SQL-fájl.
