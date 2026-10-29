"""Motor del método temporal de suficiencia de información (deserción académica).

Hito H2.1: estructura de capas, puertos y errores del dominio, contratos y
servicios de aplicación sin lógica científica, y la línea de comandos
(``suficiencia.cli``). No implementa todavía ninguna lógica metodológica.

Capas (sección 5 de la especificación v0.6), de arriba abajo:

- ``ui``: presentación (Streamlit). Solo puede usar ``application``.
- ``application``: servicios de casos de uso y contratos de entrada y salida.
- ``experimentation`` y ``persistence``: adaptadores, independientes entre sí.
- ``domain``: conceptos y reglas del método, sin entrada ni salida.

La línea de comandos solo usa ``application``. Las reglas se verifican con
import-linter (archivo ``.importlinter``).
"""

__version__ = "0.1.0.dev0"
