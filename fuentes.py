"""Código común: rutas, códigos de series, llamadas a las API del INE y Eurostat,
lectura/escritura de los datos intermedios (datos/auxiliar/) y validaciones."""

import unicodedata
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Rutas -------------------------------------------------------------------

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "datos"
AUX = DATOS / "auxiliar"  # no "aux": es un nombre reservado en Windows y Git no lo admite

AUX_NACIONAL = AUX / "epa_nacional.csv"
AUX_CCAA = AUX / "epa_ccaa.csv"
AUX_EUROPA = AUX / "eurostat_paro.csv"
AUX_EUROPA_JUVENIL = AUX / "eurostat_paro_juvenil.csv"

# --- INE (API Tempus, EPA) -----------------------------------------------------

INE_URL = "https://servicios.ine.es/wstempus/js/ES/"
PRIMER_TRIMESTRE = pd.Period("2002Q1", freq="Q")
TRIMESTRES_ACTUALIZAR = 4  # se vuelven a descargar en cada actualización (revisiones)
TRIMESTRES_CCAA = 8

# Columna en datos/auxiliar/epa_nacional.csv -> código de serie
SERIES_NACIONAL = {
    "parados_miles": "EPA387800",   # 65218 Total Nacional. Ambos sexos. Total. Parados. Valor absoluto.
    "ocupados_miles": "EPA387796",  # 65109 Total Nacional. Ambos sexos. Total. Ocupados. Valor absoluto.
    "tasa_paro": "EPA423474",       # 65219 Total Nacional. Tasa de paro. Ambos sexos. Total.
    "tasa_hombres": "EPA423488",    # 65219 Total Nacional. Tasa de paro. Hombres. Total.
    "tasa_mujeres": "EPA423501",    # 65219 Total Nacional. Tasa de paro. Mujeres. Total.
    "tasa_menores25": "EPA452436",  # 65334 Tasa de paro. Ambos sexos. Total Nacional. Menores de 25 años.
}

# Tabla 65334, "Tasa de paro de la población. Ambos sexos. <territorio>. Total."
SERIES_CCAA = {
    "España": "EPA452434",
    "Andalucía": "EPA452440",
    "Aragón": "EPA452448",
    "Principado de Asturias": "EPA452456",
    "Illes Balears": "EPA452464",
    "Canarias": "EPA452472",
    "Cantabria": "EPA452480",
    "Castilla y León": "EPA452488",
    "Castilla-La Mancha": "EPA452496",
    "Cataluña": "EPA452504",
    "Comunitat Valenciana": "EPA452512",
    "Extremadura": "EPA452520",
    "Galicia": "EPA452528",
    "Comunidad de Madrid": "EPA452536",
    "Región de Murcia": "EPA452544",
    "Comunidad Foral de Navarra": "EPA452552",
    "País Vasco": "EPA452560",
    "La Rioja": "EPA452568",
    "Ceuta": "EPA452576",
    "Melilla": "EPA452584",
}

# Claves de los mapas de Datawrapper: nombre en "Spain » Autonomous Communities" (spain-ac,
# clave dw_esp) y código en "Spain » NUTS2 (2021)". España no está en los mapas.
DATAWRAPPER_CCAA = {
    "Andalucía": ("Andalucía", "ES61"),
    "Aragón": ("Aragón", "ES24"),
    "Principado de Asturias": ("Principado de Asturias", "ES12"),
    "Illes Balears": ("Islas Baleares", "ES53"),
    "Canarias": ("Canarias", "ES70"),
    "Cantabria": ("Cantabria", "ES13"),
    "Castilla y León": ("Castilla y León", "ES41"),
    "Castilla-La Mancha": ("Castilla-La Mancha", "ES42"),
    "Cataluña": ("Cataluña", "ES51"),
    "Comunitat Valenciana": ("Comunidad Valenciana", "ES52"),
    "Extremadura": ("Extremadura", "ES43"),
    "Galicia": ("Galicia", "ES11"),
    "Comunidad de Madrid": ("Comunidad de Madrid", "ES30"),
    "Región de Murcia": ("Región de Murcia", "ES62"),
    "Comunidad Foral de Navarra": ("Comunidad Foral de Navarra", "ES22"),
    "País Vasco": ("País Vasco", "ES21"),
    "La Rioja": ("La Rioja", "ES23"),
    "Ceuta": ("Ceuta", "ES63"),
    "Melilla": ("Melilla", "ES64"),
}

# --- Eurostat (une_rt_m, JSON-stat 2.0) ------------------------------------------

EUROSTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/une_rt_m"
MESES_EUROPA = 18
MESES_EUROPA_JUVENIL = 12  # ventana para buscar el último dato no vacío de cada país

PAISES = {
    "EU27_2020": "UE-27",
    "BE": "Bélgica", "BG": "Bulgaria", "CZ": "Chequia", "DK": "Dinamarca",
    "DE": "Alemania", "EE": "Estonia", "IE": "Irlanda", "EL": "Grecia",
    "ES": "España", "FR": "Francia", "HR": "Croacia", "IT": "Italia",
    "CY": "Chipre", "LV": "Letonia", "LT": "Lituania", "LU": "Luxemburgo",
    "HU": "Hungría", "MT": "Malta", "NL": "Países Bajos", "AT": "Austria",
    "PL": "Polonia", "PT": "Portugal", "RO": "Rumanía", "SI": "Eslovenia",
    "SK": "Eslovaquia", "FI": "Finlandia", "SE": "Suecia",
}

# Los mapas de Europa de Datawrapper solo tienen nombres en inglés/alemán y códigos ISO-2.
# Eurostat usa EL para Grecia; la UE-27 no está en los mapas.
ISO_DATAWRAPPER = {geo: geo for geo in PAISES if geo != "EU27_2020"} | {"EL": "GR"}


def _sesion():
    s = requests.Session()
    reintentos = Retry(total=4, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=reintentos))
    return s


SESION = _sesion()


def ine_serie(cod, **params):
    """Descarga una serie trimestral del INE. Devuelve pd.Series indexada por Period('Q')."""
    r = SESION.get(INE_URL + f"DATOS_SERIE/{cod}", params=params, timeout=90)
    r.raise_for_status()
    valores = {}
    for d in r.json().get("Data") or []:
        if d.get("Valor") is None or d.get("Secreto"):
            continue
        trimestre = d["FK_Periodo"] - 18  # 19..22 = T1..T4
        if not 1 <= trimestre <= 4:
            raise ValueError(f"{cod}: periodo no trimestral ({d['FK_Periodo']})")
        valores[pd.Period(year=d["Anyo"], quarter=trimestre, freq="Q")] = d["Valor"]
    if not valores:
        raise ValueError(f"{cod}: la API no devolvió datos")
    return pd.Series(valores, name=cod).sort_index()


def _mismo_final(series):
    """Todas las series deben llegar al mismo trimestre (detecta series congeladas)."""
    finales = {nombre: s.index.max() for nombre, s in series.items()}
    if len(set(finales.values())) > 1:
        raise ValueError(f"Las series no llegan al mismo trimestre: {finales}")


def descargar_nacional(**params):
    series = {col: ine_serie(cod, **params) for col, cod in SERIES_NACIONAL.items()}
    _mismo_final(series)
    df = pd.DataFrame(series)
    df.index.name = "trimestre"
    return df


def descargar_ccaa(**params):
    series = {nombre: ine_serie(cod, **params) for nombre, cod in SERIES_CCAA.items()}
    _mismo_final(series)
    df = pd.DataFrame(series)
    df.index.name = "trimestre"
    return df.reset_index().melt(id_vars="trimestre", var_name="comunidad", value_name="tasa")


def eurostat(edad, meses):
    """Tasa de paro desestacionalizada de une_rt_m para la UE-27 y sus países.
    Devuelve DataFrame geo, mes, tasa (solo valores no vacíos)."""
    params = {"age": edad, "sex": "T", "unit": "PC_ACT", "s_adj": "SA", "freq": "M",
              "lastTimePeriod": meses, "geo": list(PAISES)}
    r = SESION.get(EUROSTAT_URL, params=params, timeout=120)
    r.raise_for_status()
    j = r.json()
    ids, tamanos = j["id"], j["size"]
    etiquetas = {d: {pos: cod for cod, pos in j["dimension"][d]["category"]["index"].items()}
                 for d in ids}
    valores = j.get("value") or {}
    if isinstance(valores, list):
        valores = {i: v for i, v in enumerate(valores)}
    filas = []
    for k, v in valores.items():
        if v is None:
            continue
        k, coords = int(k), {}
        for d, n in reversed(list(zip(ids, tamanos))):
            coords[d] = etiquetas[d][k % n]
            k //= n
        filas.append({"geo": coords["geo"], "mes": coords["time"], "tasa": v})
    df = pd.DataFrame(filas, columns=["geo", "mes", "tasa"])
    faltan = set(PAISES) - set(df["geo"])
    if faltan:
        raise ValueError(f"Eurostat ({edad}): faltan países {sorted(faltan)}")
    return df.sort_values(["geo", "mes"]).reset_index(drop=True)


# --- Validaciones ----------------------------------------------------------------

def _consecutivos(trimestres):
    t = sorted(set(trimestres))
    return [p for p in pd.period_range(t[0], t[-1], freq="Q") if p not in set(t)]


def validar_nacional(df):
    if df.empty:
        raise ValueError("Serie nacional vacía")
    if df.index.min() != PRIMER_TRIMESTRE:
        raise ValueError(f"La serie nacional empieza en {df.index.min()}, no en {PRIMER_TRIMESTRE}")
    huecos = _consecutivos(df.index)
    if huecos:
        raise ValueError(f"Faltan trimestres en la serie nacional: {huecos}")
    if df[list(SERIES_NACIONAL)].isna().any().any():
        raise ValueError("Hay valores vacíos en la serie nacional")


def validar_ccaa(df):
    if df["tasa"].isna().any():
        raise ValueError("Hay tasas vacías en las comunidades")
    por_trimestre = df.groupby("trimestre")["comunidad"].nunique()
    incompletos = por_trimestre[por_trimestre != len(SERIES_CCAA)]
    if not incompletos.empty:
        raise ValueError(f"Trimestres sin todas las comunidades: {incompletos.to_dict()}")
    if len(por_trimestre) != TRIMESTRES_CCAA or _consecutivos(por_trimestre.index):
        raise ValueError(f"Se esperaban {TRIMESTRES_CCAA} trimestres consecutivos de CCAA")


# --- Lectura/escritura de datos/auxiliar --------------------------------------------

def _escribir_csv(df, ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        df.to_csv(f, index=False, lineterminator="\n")


def guardar_nacional(df):
    validar_nacional(df)
    salida = df.reset_index()
    salida["trimestre"] = salida["trimestre"].astype(str)
    _escribir_csv(salida, AUX_NACIONAL)


def leer_nacional():
    df = pd.read_csv(AUX_NACIONAL)
    df["trimestre"] = pd.PeriodIndex(df["trimestre"], freq="Q")
    return df.set_index("trimestre")


def guardar_ccaa(df):
    validar_ccaa(df)
    orden = {nombre: i for i, nombre in enumerate(SERIES_CCAA)}
    salida = df.sort_values(["comunidad", "trimestre"], key=lambda c: c.map(orden) if c.name == "comunidad" else c)
    salida["trimestre"] = salida["trimestre"].astype(str)
    _escribir_csv(salida, AUX_CCAA)


def leer_ccaa():
    df = pd.read_csv(AUX_CCAA)
    df["trimestre"] = pd.PeriodIndex(df["trimestre"], freq="Q")
    return df


def guardar_eurostat(df, ruta):
    if df.empty or set(PAISES) - set(df["geo"]):
        raise ValueError(f"Datos de Eurostat incompletos, no se sobrescribe {ruta.name}")
    _escribir_csv(df, ruta)


def leer_eurostat(ruta):
    return pd.read_csv(ruta, dtype={"mes": str})


def clave_orden(texto):
    """Orden alfabético en español ignorando tildes."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
