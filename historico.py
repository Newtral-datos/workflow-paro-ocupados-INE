"""Descarga completa inicial de todas las series en datos/auxiliar/.

Se ejecuta una vez (o de nuevo para rehacerlo todo). Después hay que ejecutar procesar.py.
Si una fuente falla, las demás se guardan igual y el script termina con error.
"""

import sys
import traceback

import fuentes as f


def nacional():
    df = f.descargar_nacional(date=f.PRIMER_TRIMESTRE.start_time.strftime("%Y%m%d") + ":")
    f.guardar_nacional(df)
    return f"{len(df)} trimestres ({df.index.min()}-{df.index.max()})"


def ccaa():
    df = f.descargar_ccaa(nult=f.TRIMESTRES_CCAA)
    f.guardar_ccaa(df)
    return f"{df['trimestre'].nunique()} trimestres x {df['comunidad'].nunique()} territorios"


def europa():
    df = f.eurostat("TOTAL", f.MESES_EUROPA)
    f.guardar_eurostat(df, f.AUX_EUROPA)
    return f"{df['geo'].nunique()} países, {df['mes'].min()}-{df['mes'].max()}"


def europa_juvenil():
    df = f.eurostat("Y_LT25", f.MESES_EUROPA_JUVENIL)
    f.guardar_eurostat(df, f.AUX_EUROPA_JUVENIL)
    return f"{df['geo'].nunique()} países, {df['mes'].min()}-{df['mes'].max()}"


def ejecutar(tareas):
    """Ejecuta cada tarea por separado; devuelve 1 si alguna falló."""
    errores = 0
    for nombre, tarea in tareas.items():
        try:
            print(f"OK    {nombre}: {tarea()}")
        except Exception:
            errores += 1
            print(f"ERROR {nombre}:", file=sys.stderr)
            traceback.print_exc()
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(ejecutar({
        "INE nacional": nacional,
        "INE comunidades": ccaa,
        "Eurostat paro": europa,
        "Eurostat paro juvenil": europa_juvenil,
    }))
