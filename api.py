"""Futárszolgálat REST API."""
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

if __package__:
    from . import adatbazis
    from .modellek import Felhasznalo, Futar, FutarPozicio, Rendeles, Termek
else:
    import adatbazis
    from modellek import Felhasznalo, Futar, FutarPozicio, Rendeles, Termek

app = FastAPI(title="Futárszolgálat API")


class FelhasznaloRequest(BaseModel):
    nev: str
    cim: str
    telszam: str
    email: str
    jelszo: str
    admin: bool = False


class BejelentkezesRequest(BaseModel):
    email: str
    jelszo: str


class FutarRequest(BaseModel):
    nev: str
    telszam: str
    jarmu: str
    hatosugar_km: int
    ember: int = 0
    allapot: str = "elerheto"


class FutarAllapotRequest(BaseModel):
    allapot: str


class FutarPozicioRequest(BaseModel):
    futar_id: int
    gps_x: float
    gps_y: float
    cim: str


class TermekRequest(BaseModel):
    nev: str
    fogas: str
    ar: int
    tipus: str = "etel"
    leiras: str | None = None
    elkeszitesi_ido: int | None = None
    prioritas: int = 0
    allergen_kodok: list[int] = Field(default_factory=list)


class RendelesRequest(BaseModel):
    felhasznalo_id: int
    futar_id: int
    cim: str
    fizetesi_mod: str
    szamla: int
    km: int
    tetelek: list[tuple[int, int]]
    ertekeles: int
    prioritas: int = 0
    jatt: int | None = None
    statusz: str = "új"


class RendelesStatuszRequest(BaseModel):
    statusz: str


def _vagy_404(ertek, uzenet: str = "Nem található"):
    if ertek is None:
        raise HTTPException(status_code=404, detail=uzenet)
    return ertek


def _adatbazis_utkozes() -> HTTPException:
    return HTTPException(
        status_code=409,
        detail="Az adatok ütköznek az adatbázis valamelyik korlátozásával.",
    )


def _felhasznalo_adat(felhasznalo: Felhasznalo) -> dict:
    return {
        "id": felhasznalo.id,
        "nev": felhasznalo.nev,
        "cim": felhasznalo.cim,
        "telszam": felhasznalo.telszam,
        "email": felhasznalo.email,
        "admin": felhasznalo.admin,
    }


def _futar_adat(futar: Futar) -> dict:
    return {
        "id": futar.id,
        "nev": futar.nev,
        "telszam": futar.telszam,
        "jarmu": futar.jarmu,
        "ember": futar.ember,
        "allapot": futar.allapot,
        "hatosugar_km": futar.hatosugar_km,
    }


def _pozicio_adat(pozicio: FutarPozicio) -> dict:
    return {
        "id": pozicio.id,
        "futar_id": pozicio.futar_id,
        "gps_x": pozicio.gps_x,
        "gps_y": pozicio.gps_y,
        "cim": pozicio.cim,
    }


def _termek_adat(termek: Termek) -> dict:
    return {
        "id": termek.id,
        "tipus": termek.tipus,
        "nev": termek.nev,
        "fogas": termek.fogas,
        "leiras": termek.leiras,
        "ar": termek.ar,
        "elkeszitesi_ido": termek.elkeszitesi_ido,
        "prioritas": termek.prioritas,
        "allergenek": [
            {"kod": allergen.kod, "nev": allergen.nev}
            for allergen in termek.allergenek
        ],
    }


def _rendeles_adat(rendeles: Rendeles) -> dict:
    return {
        "id": rendeles.id,
        "felhasznalo_id": rendeles.felhasznalo_id,
        "futar_id": rendeles.futar_id,
        "cim": rendeles.cim,
        "prioritas": rendeles.prioritas,
        "fizetesi_mod": rendeles.fizetesi_mod,
        "jatt": rendeles.jatt,
        "szamla": rendeles.szamla,
        "km": rendeles.km,
        "statusz": rendeles.statusz,
        "ertekeles": rendeles.ertekeles,
        "tetelek": [
            {
                "termek": _termek_adat(tetel.termek),
                "db": tetel.db,
                "osszeg": tetel.osszeg(),
            }
            for tetel in rendeles.tetelek
        ],
        "vegosszeg": rendeles.vegosszeg(),
    }


@app.post("/bejelentkezes")
def ep_bejelentkezes(body: BejelentkezesRequest):
    felhasznalo = adatbazis.bejelentkezes(body.email, body.jelszo)
    if felhasznalo is None:
        raise HTTPException(status_code=401, detail="Hibás e-mail-cím vagy jelszó.")
    return _felhasznalo_adat(felhasznalo)


@app.post("/felhasznalo", status_code=201)
def ep_felhasznalo_letrehoz(body: FelhasznaloRequest):
    try:
        felhasznalo = Felhasznalo.regisztral(
            body.nev, body.cim, body.telszam, body.email, body.jelszo, body.admin
        )
        return {"id": adatbazis.felhasznalo_letrehoz(felhasznalo)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except sqlite3.IntegrityError as e:
        raise _adatbazis_utkozes() from e


@app.get("/felhasznalo")
def ep_felhasznalok_szur(
    nev_tartalmaz: str | None = None,
    cim_tartalmaz: str | None = None,
    telszam: str | None = None,
    email: str | None = None,
    email_tartalmaz: str | None = None,
    admin: bool | None = None,
    rendezes: str | None = None,
    csokkeno: bool = False,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    try:
        return [
            _felhasznalo_adat(f)
            for f in adatbazis.felhasznalok_szur(
                nev_tartalmaz=nev_tartalmaz,
                cim_tartalmaz=cim_tartalmaz,
                telszam=telszam,
                email=email,
                email_tartalmaz=email_tartalmaz,
                admin=admin,
                rendezes=rendezes,
                csokkeno=csokkeno,
                limit=limit,
                offset=offset,
            )
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/felhasznalo/email/{email}")
def ep_felhasznalo_lekerdez_emailre(email: str):
    return _felhasznalo_adat(
        _vagy_404(
            adatbazis.felhasznalo_lekerdez_emailre(email),
            "Felhasználó nem található",
        )
    )


@app.get("/felhasznalo/{felhasznalo_id}")
def ep_felhasznalo_lekerdez(felhasznalo_id: int):
    return _felhasznalo_adat(
        _vagy_404(
            adatbazis.felhasznalo_lekerdez(felhasznalo_id),
            "Felhasználó nem található",
        )
    )


@app.put("/felhasznalo/{felhasznalo_id}")
def ep_felhasznalo_modosit(felhasznalo_id: int, body: FelhasznaloRequest):
    try:
        felhasznalo = Felhasznalo.regisztral(
            body.nev, body.cim, body.telszam, body.email, body.jelszo, body.admin
        )
        felhasznalo.id = felhasznalo_id
        if not adatbazis.felhasznalo_modosit(felhasznalo):
            raise HTTPException(status_code=404, detail="Felhasználó nem található")
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except sqlite3.IntegrityError as e:
        raise _adatbazis_utkozes() from e


@app.delete("/felhasznalo/{felhasznalo_id}")
def ep_felhasznalo_torol(felhasznalo_id: int):
    if not adatbazis.felhasznalo_torol(felhasznalo_id):
        raise HTTPException(status_code=404, detail="Felhasználó nem található")
    return {"ok": True}


@app.get("/felhasznalo/{felhasznalo_id}/rendelesek")
def ep_felhasznalo_rendelesei(felhasznalo_id: int):
    return [
        _rendeles_adat(r)
        for r in adatbazis.rendelesek_szur(felhasznalo_id=felhasznalo_id)
    ]


@app.post("/futar", status_code=201)
def ep_futar_letrehoz(body: FutarRequest):
    try:
        return {
            "id": adatbazis.futar_letrehoz(
                Futar(
                    nev=body.nev,
                    telszam=body.telszam,
                    jarmu=body.jarmu,
                    ember=body.ember,
                    allapot=body.allapot,
                    hatosugar_km=body.hatosugar_km,
                )
            )
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except sqlite3.IntegrityError as e:
        raise _adatbazis_utkozes() from e


@app.get("/futar")
def ep_futarok_szur(
    jarmu: list[str] | None = Query(default=None),
    allapot: list[str] | None = Query(default=None),
    ember: int | None = None,
    min_hatosugar_km: int | None = None,
    nev_tartalmaz: str | None = None,
    rendezes: str | None = None,
    csokkeno: bool = False,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    try:
        return [
            _futar_adat(f)
            for f in adatbazis.futarok_szur(
                jarmu=jarmu,
                allapot=allapot,
                ember=ember,
                min_hatosugar_km=min_hatosugar_km,
                nev_tartalmaz=nev_tartalmaz,
                rendezes=rendezes,
                csokkeno=csokkeno,
                limit=limit,
                offset=offset,
            )
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/futar/elerheto")
def ep_elerheto_futarok(jarmu: str | None = None):
    return [_futar_adat(f) for f in adatbazis.elerheto_futarok(jarmu)]


@app.get("/futar/{futar_id}")
def ep_futar_lekerdez(futar_id: int):
    return _futar_adat(
        _vagy_404(adatbazis.futar_lekerdez(futar_id), "Futár nem található")
    )


@app.patch("/futar/{futar_id}/allapot")
def ep_futar_allapot_modosit(futar_id: int, body: FutarAllapotRequest):
    try:
        if not adatbazis.futar_allapot_modosit(futar_id, body.allapot):
            raise HTTPException(status_code=404, detail="Futár nem található")
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/futar/{futar_id}/rendelesek")
def ep_futar_rendelesei(futar_id: int):
    return [
        _rendeles_adat(r)
        for r in adatbazis.rendelesek_szur(futar_id=futar_id)
    ]


@app.post("/futar/pozicio", status_code=201)
def ep_futar_pozicio_letrehoz(body: FutarPozicioRequest):
    try:
        pozicio = FutarPozicio(
            futar_id=body.futar_id,
            gps_x=body.gps_x,
            gps_y=body.gps_y,
            cim=body.cim,
        )
        return {"id": adatbazis.futar_pozicio_letrehoz(pozicio)}
    except sqlite3.IntegrityError as e:
        raise _adatbazis_utkozes() from e


@app.get("/futar/{futar_id}/poziciok")
def ep_futar_pozicioi(futar_id: int):
    return [
        _pozicio_adat(p)
        for p in adatbazis.futar_pozicio_lekerdez(futar_id)
    ]


@app.get("/allergen")
def ep_allergenek():
    return [{"kod": a.kod, "nev": a.nev} for a in adatbazis.allergenek_lekerdez()]


@app.post("/termek", status_code=201)
def ep_termek_letrehoz(body: TermekRequest):
    try:
        allergenek = {a.kod: a for a in adatbazis.allergenek_lekerdez()}
        hianyzo = sorted(set(body.allergen_kodok) - allergenek.keys())
        if hianyzo:
            raise HTTPException(
                status_code=404,
                detail=f"Nem található allergénkód: {', '.join(map(str, hianyzo))}",
            )
        termek = Termek(
            nev=body.nev,
            fogas=body.fogas,
            ar=body.ar,
            tipus=body.tipus,
            leiras=body.leiras,
            elkeszitesi_ido=body.elkeszitesi_ido,
            prioritas=body.prioritas,
            allergenek=[allergenek[kod] for kod in body.allergen_kodok],
        )
        return {"id": adatbazis.termek_letrehoz(termek)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except sqlite3.IntegrityError as e:
        raise _adatbazis_utkozes() from e


@app.get("/termek")
def ep_termekek_szur(
    tipus: str | None = None,
    fogas: list[str] | None = Query(default=None),
    ar_min: int | None = None,
    ar_max: int | None = None,
    nev_tartalmaz: str | None = None,
    max_elkeszitesi_ido: int | None = None,
    prioritas: int | None = None,
    nem_tartalmaz_allergen: list[int] | None = Query(default=None),
    rendezes: str | None = None,
    csokkeno: bool = False,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    try:
        return [
            _termek_adat(t)
            for t in adatbazis.termekek_szur(
                tipus=tipus,
                fogas=fogas,
                ar_min=ar_min,
                ar_max=ar_max,
                nev_tartalmaz=nev_tartalmaz,
                max_elkeszitesi_ido=max_elkeszitesi_ido,
                prioritas=prioritas,
                nem_tartalmaz_allergen=nem_tartalmaz_allergen,
                rendezes=rendezes,
                csokkeno=csokkeno,
                limit=limit,
                offset=offset,
            )
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/termek/{termek_id}")
def ep_termek_lekerdez(termek_id: int):
    return _termek_adat(
        _vagy_404(adatbazis.termek_lekerdez(termek_id), "Termék nem található")
    )


@app.post("/rendeles", status_code=201)
def ep_rendeles_letrehoz(body: RendelesRequest):
    try:
        if not body.tetelek:
            raise ValueError("Legalább egy tétel szükséges a rendeléshez.")
        rendeles = Rendeles(
            felhasznalo_id=body.felhasznalo_id,
            futar_id=body.futar_id,
            cim=body.cim,
            fizetesi_mod=body.fizetesi_mod,
            szamla=body.szamla,
            km=body.km,
            ertekeles=body.ertekeles,
            prioritas=body.prioritas,
            jatt=body.jatt,
            statusz=body.statusz,
        )
        for termek_id, darab in body.tetelek:
            termek = _vagy_404(
                adatbazis.termek_lekerdez(termek_id), "Termék nem található"
            )
            rendeles.tetel_hozzaad(termek, darab)
        return {"id": adatbazis.rendeles_letrehoz(rendeles)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except sqlite3.IntegrityError as e:
        raise _adatbazis_utkozes() from e


@app.get("/rendeles")
def ep_rendelesek_szur(
    felhasznalo_id: int | None = None,
    futar_id: int | None = None,
    statusz: list[str] | None = Query(default=None),
    fizetesi_mod: str | None = None,
    prioritas: int | None = None,
    szamla: int | None = None,
    km_min: int | None = None,
    km_max: int | None = None,
    ertekeles_min: int | None = None,
    ertekeles_max: int | None = None,
    van_jatt: bool | None = None,
    cim_tartalmaz: str | None = None,
    termek_id: int | None = None,
    rendezes: str | None = None,
    csokkeno: bool = False,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    try:
        return [
            _rendeles_adat(r)
            for r in adatbazis.rendelesek_szur(
                felhasznalo_id=felhasznalo_id,
                futar_id=futar_id,
                statusz=statusz,
                fizetesi_mod=fizetesi_mod,
                prioritas=prioritas,
                szamla=szamla,
                km_min=km_min,
                km_max=km_max,
                ertekeles_min=ertekeles_min,
                ertekeles_max=ertekeles_max,
                van_jatt=van_jatt,
                cim_tartalmaz=cim_tartalmaz,
                termek_id=termek_id,
                rendezes=rendezes,
                csokkeno=csokkeno,
                limit=limit,
                offset=offset,
            )
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/rendeles/{rendeles_id}")
def ep_rendeles_lekerdez(rendeles_id: int):
    return _rendeles_adat(
        _vagy_404(
            adatbazis.rendeles_lekerdez(rendeles_id),
            "Rendelés nem található",
        )
    )


@app.patch("/rendeles/{rendeles_id}/statusz")
def ep_rendeles_statusz_modosit(
    rendeles_id: int, body: RendelesStatuszRequest
):
    if not adatbazis.rendeles_statusz_modosit(rendeles_id, body.statusz):
        raise HTTPException(status_code=404, detail="Rendelés nem található")
    return {"ok": True}
