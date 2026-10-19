"""Genera los CSV finales de datos/ a partir de datos/auxiliar/ y escribe sus JSON.

Un CSV solo se reescribe si su contenido cambia; en ese caso su JSON recibe la fecha de hoy.
Cada CSV se valida antes de escribirse: si no pasa, se conserva el anterior.
"""

import json
import sys
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

import fuentes as f


def hoy():
    return datetime.now(ZoneInfo("Europe/Madrid")).strftime("%d/%m/%Y")


def escribir(nombre, df):
    """Escribe datos/<nombre>.csv y su JSON solo si el contenido ha cambiado."""
    ruta_csv = f.DATOS / f"{nombre}.csv"
    ruta_json = f.DATOS / f"{nombre}.json"
    contenido = df.to_csv(index=False, lineterminator="\n")
    if ruta_csv.exists() and ruta_json.exists() and ruta_csv.read_text(encoding="utf-8") == contenido:
        return "sin cambios"
    f.DATOS.mkdir(parents=True, exist_ok=True)
    with open(ruta_csv, "w", encoding="utf-8", newline="") as fh:
        fh.write(contenido)
    nota = f"Actualizado por última vez {hoy()}"
    with open(ruta_json, "w", encoding="utf-8", newline="\n") as fh:
        # annotate.notes es la clave que Datawrapper lee como "Notas" en los metadatos externos
        json.dump({"nota": nota, "annotate": {"notes": nota}}, fh, ensure_ascii=False)
        fh.write("\n")
    return "actualizado"


def variacion(actual, anterior):
    """Variación relativa en %, respecto al mismo periodo del año anterior."""
    return ((actual / anterior - 1) * 100).round(2)


# --- Series nacionales -------------------------------------------------------------

def _nacional(columnas):
    df = f.leer_nacional()
    f.validar_nacional(df)
    salida = df[list(columnas)].rename(columns=columnas).reset_index()
    salida["trimestre"] = salida["trimestre"].astype(str)
    return salida


def parados():
    df = _nacional({"parados_miles": "parados"})
    df["parados"] = (df["parados"] * 1000).round().astype(int)
    return df


def ocupados():
    df = _nacional({"ocupados_miles": "ocupados"})
    df["ocupados"] = (df["ocupados"] * 1000).round().astype(int)
    return df


def tasa_paro():
    return _nacional({"tasa_paro": "tasa_paro"})


def tasa_paro_sexo():
    return _nacional({"tasa_hombres": "hombres", "tasa_mujeres": "mujeres"})


def tasa_paro_juvenil():
    return _nacional({"tasa_menores25": "menores_25", "tasa_paro": "total"})


# --- Comunidades: último trimestre y variación interanual -----------------------------

def tasa_paro_ccaa():
    df = f.leer_ccaa()
    f.validar_ccaa(df)
    ultimo = df["trimestre"].max()
    tabla = df.pivot(index="comunidad", columns="trimestre", values="tasa")
    salida = pd.DataFrame({
        "comunidad": list(f.SERIES_CCAA),
        "trimestre": str(ultimo),
    })
    salida["tasa"] = salida["comunidad"].map(tabla[ultimo])
    salida["variacion_interanual"] = variacion(
        salida["tasa"], salida["comunidad"].map(tabla[ultimo - 4]))
    if len(salida) != len(f.SERIES_CCAA) or salida.isna().any().any():
        raise ValueError("Faltan comunidades o datos del año anterior")
    salida["nombre_datawrapper"] = salida["comunidad"].map(lambda c: f.DATAWRAPPER_CCAA.get(c, ("", ""))[0])
    salida["codigo_nuts2"] = salida["comunidad"].map(lambda c: f.DATAWRAPPER_CCAA.get(c, ("", ""))[1])
    return salida


# --- Europa ----------------------------------------------------------------------------

def _ordenar_paises(df):
    """UE-27 primero y después los países por orden alfabético."""
    orden = df["pais"].map(lambda p: (p != "UE-27", f.clave_orden(p)))
    return df.loc[orden.sort_values().index].reset_index(drop=True)


def _codigo_iso(df):
    """Sustituye el código de Eurostat por el ISO-2 que reconocen los mapas de Datawrapper."""
    df["codigo_iso"] = df.pop("geo").map(f.ISO_DATAWRAPPER).fillna("")
    return df


def _ultimo_por_pais(df):
    return df.sort_values("mes").groupby("geo").tail(1)


def tasa_paro_europa():
    df = f.leer_eurostat(f.AUX_EUROPA)
    df["periodo"] = pd.PeriodIndex(df["mes"], freq="M")
    anterior = df.set_index(["geo", "periodo"])["tasa"]
    ultimo = _ultimo_por_pais(df).copy()
    claves = list(zip(ultimo["geo"], ultimo["periodo"] - 12))
    ultimo["tasa_anterior"] = [anterior.get(k) for k in claves]
    ultimo["variacion_interanual"] = variacion(ultimo["tasa"], ultimo["tasa_anterior"].astype(float))
    ultimo["pais"] = ultimo["geo"].map(f.PAISES)
    salida = _ordenar_paises(ultimo[["pais", "mes", "tasa", "variacion_interanual", "geo"]])
    if len(salida) != len(f.PAISES) or salida.isna().any().any():
        sin_dato = ultimo.loc[ultimo["tasa_anterior"].isna(), "geo"].tolist()
        raise ValueError(f"Faltan países o el dato del año anterior: {sin_dato}")
    return _codigo_iso(salida)


def paro_juvenil_europa():
    df = f.leer_eurostat(f.AUX_EUROPA_JUVENIL)
    ultimo = _ultimo_por_pais(df)
    ultimo = ultimo.assign(pais=ultimo["geo"].map(f.PAISES))
    salida = _ordenar_paises(ultimo[["pais", "mes", "tasa", "geo"]])
    if len(salida) != len(f.PAISES) or salida.isna().any().any():
        raise ValueError("Faltan países en el paro juvenil europeo")
    return _codigo_iso(salida)


SALIDAS = {
    "parados": parados,
    "ocupados": ocupados,
    "tasa_paro": tasa_paro,
    "tasa_paro_sexo": tasa_paro_sexo,
    "tasa_paro_juvenil": tasa_paro_juvenil,
    "tasa_paro_ccaa": tasa_paro_ccaa,
    "tasa_paro_europa": tasa_paro_europa,
    "paro_juvenil_europa": paro_juvenil_europa,
}


if __name__ == "__main__":
    errores = 0
    for nombre, generar in SALIDAS.items():
        try:
            print(f"OK    {nombre}.csv: {escribir(nombre, generar())}")
        except Exception:
            errores += 1
            print(f"ERROR {nombre}.csv (se conserva el anterior):", file=sys.stderr)
            traceback.print_exc()
    sys.exit(1 if errores else 0)
