"""Capa de persistencia: lectura y escritura de archivos, registros y artefactos.

Implementa puertos del dominio. Puede usar ``domain``; no puede usar
``application``, ``ui`` ni ``experimentation``.
Contiene el lector de la configuración del proyecto, que implementa el puerto
``FuenteConfiguracion`` (H2.1).
"""
