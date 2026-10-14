"""Modellréteg a futárszolgálathoz.

Az osztályok az adatbázis tábláit képezik le, validálják az adatot (ugyanazok a
szabályok, mint az SQL CHECK-ek), és tartalmazzák az üzleti logikát.
Adatbázisba írás itt NINCS. Az id None, amíg az objektumot valaki el nem mentette.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

JARMUVEK = ("auto", "dron", "bicikli", "motor")
FUTAR_ALLAPOTOK = ("elerheto", "uton", "szunet")
TERMEK_TIPUSOK = ("etel", "ital")
FIZETESI_MODOK = ("keszpenz", "kartya")


class ValidacioHiba(ValueError):
    """Érvénytelen adat a modellben."""


def _ellenoriz(feltetel: bool, uzenet: str) -> None:
    if not feltetel:
        raise ValidacioHiba(uzenet)


# ---------------------------------------------------------------------------
@dataclass
class Allergen:
    nev: str
    kod: int | None = None

    @classmethod
    def sorbol(cls, sor) -> Allergen:
        """sor: sqlite3.Row vagy dict a 'allergen' táblából."""
        return cls(kod=sor["kod"], nev=sor["nev"])


_EMAIL_MINTA = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_JELSZO_HOSSZ = 8


@dataclass
class Felhasznalo:
    nev: str
    cim: str
    telszam: str
    email: str
    jelszo: str = field(repr=False)
    admin: bool = False                    # az SQL-ben: isAdmin
    id: int | None = None

    def __post_init__(self):
        for mezo in ("nev", "cim", "telszam"):
            _ellenoriz(bool(getattr(self, mezo).strip()), f"A(z) {mezo} nem lehet üres.")
        self.email = self.email.strip().lower()
        _ellenoriz(bool(_EMAIL_MINTA.match(self.email)), f"Érvénytelen email: {self.email}")

    @classmethod
    def regisztral(cls, nev: str, cim: str, telszam: str, email: str,
                   jelszo: str, admin: bool = False) -> Felhasznalo:
        """Új felhasználó létrehozása a dump szerinti jelszótárolással."""
        _ellenoriz(len(jelszo) >= MIN_JELSZO_HOSSZ,
                   f"A jelszó legalább {MIN_JELSZO_HOSSZ} karakter legyen.")
        return cls(nev, cim, telszam, email, jelszo, admin)

    def jelszo_helyes(self, jelszo: str) -> bool:
        return self.jelszo == jelszo

    def jelszo_csere(self, uj_jelszo: str) -> None:
        _ellenoriz(len(uj_jelszo) >= MIN_JELSZO_HOSSZ,
                   f"A jelszó legalább {MIN_JELSZO_HOSSZ} karakter legyen.")
        self.jelszo = uj_jelszo

    @classmethod
    def sorbol(cls, sor) -> Felhasznalo:
        return cls(id=sor["id"], nev=sor["nev"], cim=sor["cim"], telszam=sor["telszam"],
                   email=sor["email"], jelszo=sor["password"],
                   admin=bool(sor["isAdmin"]))


@dataclass
class Futar:
    nev: str
    telszam: str
    jarmu: str
    hatosugar_km: int
    ember: int = 0
    allapot: str = "elerheto"
    id: int | None = None

    def __post_init__(self):
        _ellenoriz(self.jarmu in JARMUVEK, f"Érvénytelen jármű: {self.jarmu}")
        _ellenoriz(self.allapot in FUTAR_ALLAPOTOK, f"Érvénytelen állapot: {self.allapot}")
        _ellenoriz(self.hatosugar_km > 0, "A hatósugár pozitív kell legyen.")
        _ellenoriz(self.jarmu != "dron" or self.ember == 0,
                   "Dróngyalogos futár nem lehet 'ember'.")

    # --- üzleti logika ---
    def elerheto(self) -> bool:
        return self.allapot == "elerheto"

    def kiszallithat(self, km: int) -> bool:
        """Elérhető és a hatósugarán belül van a cél."""
        return self.elerheto() and km <= self.hatosugar_km

    @classmethod
    def sorbol(cls, sor) -> Futar:
        return cls(id=sor["id"], nev=sor["nev"], telszam=sor["telszam"],
                   jarmu=sor["jarmu"], ember=sor["ember"], allapot=sor["allapot"],
                   hatosugar_km=sor["hatosugar_km"])


@dataclass
class FutarPozicio:
    futar_id: int      # az SQL-ben: futarID
    gps_x: float       # az SQL-ben REAL
    gps_y: float       # az SQL-ben INTEGER (érdemes REAL-ra egységesíteni)
    cim: str
    id: int | None = None

    @classmethod
    def sorbol(cls, sor) -> FutarPozicio:
        return cls(id=sor["id"], futar_id=sor["futarID"], gps_x=sor["gps_x"],
                   gps_y=sor["gps_y"], cim=sor["cim"])


@dataclass
class Termek:
    nev: str
    fogas: str
    ar: int
    tipus: str = "etel"
    leiras: str | None = None
    elkeszitesi_ido: int | None = None
    prioritas: int = 0
    allergenek: list[Allergen] = field(default_factory=list)
    id: int | None = None

    def __post_init__(self):
        _ellenoriz(self.tipus in TERMEK_TIPUSOK, f"Érvénytelen típus: {self.tipus}")
        _ellenoriz(self.ar >= 0, "Az ár nem lehet negatív.")

    @classmethod
    def sorbol(cls, sor, allergenek: list[Allergen] | None = None) -> Termek:
        return cls(id=sor["id"], tipus=sor["tipus"], nev=sor["nev"], fogas=sor["fogas"],
                   leiras=sor["leiras"], ar=sor["ar"],
                   elkeszitesi_ido=sor["elkeszitesi_ido"], prioritas=sor["prioritas"],
                   allergenek=allergenek or [])


@dataclass
class RendelesTetel:
    termek: Termek
    db: int = 1

    def __post_init__(self):
        _ellenoriz(self.db >= 1, "A darabszám legalább 1.")

    def osszeg(self) -> int:
        return self.termek.ar * self.db


@dataclass
class Rendeles:
    felhasznalo_id: int
    futar_id: int
    cim: str
    fizetesi_mod: str
    szamla: int
    km: int
    ertekeles: int | None = None  # Az API rendelésleadásakor kötelező.
    prioritas: int = 0
    jatt: int | None = None
    statusz: str = "új"
    tetelek: list[RendelesTetel] = field(default_factory=list)
    id: int | None = None

    def __post_init__(self):
        _ellenoriz(self.fizetesi_mod in FIZETESI_MODOK, f"Érvénytelen fizetési mód: {self.fizetesi_mod}")
        _ellenoriz(self.prioritas in (0, 1), "A prioritás 0 vagy 1.")
        _ellenoriz(self.szamla in (0, 1), "A számla 0 vagy 1.")
        _ellenoriz(self.km > 0, "A km pozitív kell legyen.")
        _ellenoriz(self.ertekeles is None or self.ertekeles in (1, 2, 3, 4, 5),
                   "Az értékelés 1 és 5 közötti.")
        _ellenoriz(
            self.fizetesi_mod == "kartya" and (self.jatt is None or self.jatt > 0),
            "A dump rendelési megszorítása csak kártyás fizetést enged.",
        )

    # --- üzleti logika ---
    def tetel_hozzaad(self, termek: Termek, db: int = 1) -> None:
        for t in self.tetelek:           # ugyanaz a termék: darabszám növelése
            if t.termek.id is not None and t.termek.id == termek.id:
                t.db += db
                return
        self.tetelek.append(RendelesTetel(termek, db))

    def vegosszeg(self) -> int:
        return sum(t.osszeg() for t in self.tetelek)

    def allergenek(self) -> set[str]:
        return {a.nev for t in self.tetelek for a in t.termek.allergenek}
