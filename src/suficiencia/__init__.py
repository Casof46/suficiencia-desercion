"""Motor del método temporal de suficiencia de información (deserción académica).

Hito H2.0: este paquete solo contiene la estructura de capas y el lector de la
configuración del proyecto. No implementa todavía ninguna lógica metodológica.

Capas (sección 5 de la especificación v0.4), de arriba abajo:

- ``ui``: presentación (Streamlit). Solo puede usar ``application``.
- ``application``: servicios de casos de uso y contratos de entrada y salida.
- ``experimentation`` y ``persistence``: adaptadores, independientes entre sí.
- ``domain``: conceptos y reglas del método, sin entrada ni salida.

Las reglas se verifican con import-linter (archivo ``.importlinter``).
El nombre ``suficiencia`` es provisional mientras REC-05 no esté decidida.
"""

__version__ = "0.1.0.dev0"
