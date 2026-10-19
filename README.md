# Paro: EPA (INE) y Eurostat para Datawrapper

Descarga y prepara los datos de paro para los gráficos de Datawrapper. Se actualiza
solo con GitHub Actions cada día laborable a las 11:30 UTC (y a mano con *Run workflow*).

## Scripts

| Script | Qué hace |
|---|---|
| `historico.py` | Descarga completa en `datos/auxiliar/`. Una vez, o para rehacerlo todo. |
| `actualizar.py` | INE: vuelve a bajar los 4 últimos trimestres (añade el nuevo si ha salido). Eurostat: vuelve a bajar la ventana entera. |
| `procesar.py` | Genera los CSV de `datos/` y sus JSON. Solo reescribe los que cambian. |
| `fuentes.py` | Código común: códigos de series, llamadas a las API, validaciones. |

```
pip install -r requirements.txt
python historico.py && python procesar.py   # primera vez
python actualizar.py && python procesar.py  # después
```

Si una fuente falla, las demás se guardan y el script sale con error (GitHub avisa por correo).
Nunca se sobrescribe un CSV con datos vacíos o incompletos.

## CSV finales (`datos/`)

| CSV | Contenido | Fuente |
|---|---|---|
| `parados.csv` | trimestre, parados (personas) desde 2002Q1 | INE EPA387800 (tabla 65218) |
| `ocupados.csv` | trimestre, ocupados (personas) desde 2002Q1 | INE EPA387796 (tabla 65109) |
| `tasa_paro.csv` | trimestre, tasa de paro (%) | INE EPA423474 (tabla 65219) |
| `tasa_paro_sexo.csv` | trimestre, hombres, mujeres (%) | INE EPA423488, EPA423501 (tabla 65219) |
| `tasa_paro_juvenil.csv` | trimestre, menores de 25 años y total (%) | INE EPA452436 (tabla 65334) y EPA423474 |
| `tasa_paro_ccaa.csv` | último trimestre: comunidad, tasa, variación interanual | INE tabla 65334 (20 series) |
| `tasa_paro_europa.csv` | último mes de cada país: tasa, variación interanual | Eurostat une_rt_m, SA |
| `paro_juvenil_europa.csv` | último mes de cada país: tasa menores de 25 | Eurostat une_rt_m, SA |

Cada CSV tiene un JSON con el mismo nombre y la fecha del último cambio real del CSV:
`{"nota": "Actualizado por última vez dd/mm/aaaa", "annotate": {"notes": "..."}}`.
Datawrapper solo lee `annotate.notes` (lo muestra como *Notas* del gráfico).

## URL para Datawrapper

> Repositorio: https://github.com/Newtral-datos/workflow-paro-ocupados-INE (rama `main`).
> El repositorio tiene que ser **público**: Datawrapper no puede leer archivos de repos privados.

En Datawrapper: *Upload data → Link external dataset*, pega la URL del CSV y, en
*Show advanced options*, la URL del JSON de metadatos.

| Gráfico | CSV | JSON |
|---|---|---|
| Parados | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/parados.csv` | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/parados.json` |
| Ocupados | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/ocupados.csv` | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/ocupados.json` |
| Tasa de paro | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/tasa_paro.csv` | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/tasa_paro.json` |
| Tasa de paro por sexo | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/tasa_paro_sexo.csv` | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/tasa_paro_sexo.json` |
| Paro juvenil | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/tasa_paro_juvenil.csv` | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/tasa_paro_juvenil.json` |
| Paro por CCAA | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/tasa_paro_ccaa.csv` | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/tasa_paro_ccaa.json` |
| Paro en Europa | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/tasa_paro_europa.csv` | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/tasa_paro_europa.json` |
| Paro juvenil en Europa | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/paro_juvenil_europa.csv` | `https://raw.githubusercontent.com/Newtral-datos/workflow-paro-ocupados-INE/main/datos/paro_juvenil_europa.json` |

- Trimestres en formato `2026Q2` (Datawrapper lo reconoce como fecha); meses en `2026-08`.
- Columnas para los mapas de Datawrapper (vacías para España y la UE-27, que no están en los mapas):
  - `tasa_paro_ccaa.csv`: `nombre_datawrapper` (mapa *Spain » Autonomous Communities*) y
    `codigo_nuts2` (mapa *Spain » NUTS2 (2021)*). La columna `comunidad` usa los nombres
    oficiales; el mapa no reconoce "Comunitat Valenciana" ni "Illes Balears".
  - CSV de Europa: `codigo_iso` (ISO-2, válido en todos los mapas de Europa; Grecia es `GR`,
    no `EL` como en Eurostat). Los mapas no tienen nombres en español.
- La variación interanual es relativa: `(tasa / tasa hace un año − 1) × 100`. En Europa se
  calcula con el último mes publicado por cada país.

`datos/auxiliar/` guarda los datos intermedios (no van a Datawrapper). No se llama `aux`
porque es un nombre reservado en Windows y Git no puede guardarlo.
