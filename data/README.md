# Carpeta `data/` — no versionada

Esta carpeta está excluida del control de versiones (`.gitignore`). Solo este README se versiona.

- **No coloque aquí datos institucionales reales** mientras no se cumplan las condiciones de la sección H.1 del documento "Fase 1 — Auditoría final y acta de cierre": autorización (DP-02), protección y custodia (DP-14), formato (DP-15), entre otras.
- Los datos institucionales **no deben subirse a repositorios** (públicos ni privados) **ni enviarse a servicios externos o asistentes de IA** sin autorización expresa.
- La seudonimización no equivale a anonimización: los datos seudonimizados siguen siendo datos personales.

Subcarpetas previstas por la especificación (sección 6), que se crearán cuando un hito las use:

- `raw/`: archivos fuente, de solo lectura.
- `interim/`: datos seudonimizados.
- `processed/`: datasets listos para M2.

Desde H2.3 también se usan:

- `sintetico/`: archivos **sintéticos** generados con `scripts/generar_sintetico.py`. No contienen datos de ninguna persona.
- `interim/`: datasets sintéticos ya seudonimizados y auditados con `suficiencia datos importar --salida`.

El comando `suficiencia datos importar` rechaza cualquier archivo que no esté marcado como sintético en todas sus filas.
