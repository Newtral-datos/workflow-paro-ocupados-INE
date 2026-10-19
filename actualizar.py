"""Actualización incremental de datos/auxiliar/.

- INE: vuelve a descargar los últimos 4 trimestres y los sobrescribe (revisiones);
  si ha salido un trimestre nuevo, queda añadido. Las CCAA se recortan a 8 trimestres.
- Eurostat: vuelve a descargar entera la ventana de meses (la serie SA se revisa).
Si una fuente falla, las demás se guardan igual y el script termina con error.
"""

import sys

import pandas as pd

import fuentes as f
from historico import ejecutar, europa, europa_juvenil


def _comprobar_continuidad(viejo_fin, nuevo):
    inicio, fin = nuevo.min(), nuevo.max()
    if inicio > viejo_fin + 1:
        raise ValueError(f"Hueco entre {viejo_fin} y {inicio}: ejecuta historico.py")
    if fin < viejo_fin:
        raise ValueError(f"La descarga llega a {fin} pero ya había datos hasta {viejo_fin}")


def nacional():
    viejo = f.leer_nacional()
    nuevo = f.descargar_nacional(nult=f.TRIMESTRES_ACTUALIZAR)
    _comprobar_continuidad(viejo.index.max(), nuevo.index)
    df = pd.concat([viejo[viejo.index < nuevo.index.min()], nuevo])
    f.guardar_nacional(df)
    return f"hasta {df.index.max()} (antes {viejo.index.max()})"


def ccaa():
    viejo = f.leer_ccaa()
    nuevo = f.descargar_ccaa(nult=f.TRIMESTRES_ACTUALIZAR)
    _comprobar_continuidad(viejo["trimestre"].max(), nuevo["trimestre"])
    df = pd.concat([viejo[viejo["trimestre"] < nuevo["trimestre"].min()], nuevo])
    ultimos = sorted(df["trimestre"].unique())[-f.TRIMESTRES_CCAA:]
    df = df[df["trimestre"].isin(ultimos)].reset_index(drop=True)
    f.guardar_ccaa(df)
    return f"{ultimos[0]}-{ultimos[-1]}"


if __name__ == "__main__":
    sys.exit(ejecutar({
        "INE nacional": nacional,
        "INE comunidades": ccaa,
        "Eurostat paro": europa,
        "Eurostat paro juvenil": europa_juvenil,
    }))
