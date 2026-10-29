# DP-08h — Piloto con cohortes excluidas

| Campo | Valor |
| --- | --- |
| Decisión | **Se permite un piloto**: entrenar modelos con datos reales de una o más cohortes antes de aprobar el protocolo confirmatorio (E2), con la condición de que esas cohortes queden fuera del análisis confirmatorio |
| Fecha | 29 de octubre de 2026 |
| Decide | Equipo y asesoría (especificación, sección 12.2) |
| Comunicada por | Jorge, en nombre del equipo |
| Estado | Decidida por el equipo; **pendiente de confirmación de Javier y de la conformidad de la asesoría** (acta, apartado 5.2) |
| Bloqueaba | DP-05 (partición cronológica) y CU-04 |

## Opciones consideradas

| Opción | Ventajas | Desventajas |
| --- | --- | --- |
| **Permitir el piloto** (elegida) | Las reglas de suficiencia se fijan sabiendo qué desempeño es realista, lo que reduce el riesgo de que ningún escenario cumpla | Se pierden para el análisis confirmatorio las cohortes del piloto, cuando ya existe el riesgo de no tener suficientes cohortes con seguimiento completo (RM-12). Un revisor puede verlo como un debilitamiento del protocolo, por lo que debe documentarse |
| No permitir el piloto | Todas las cohortes quedan disponibles para desarrollo y prueba; protocolo más estricto | Los criterios se fijan sin conocer el desempeño alcanzable |

La especificación no recomendaba ninguna de las dos opciones.

## Consecuencias

- DP-05 debe reservar las cohortes del piloto, además de fijar las de desarrollo y prueba y el plan de contingencia exigido al aceptar REC-01. Cuántas y cuáles cohortes se reservan no se decide aquí.
- Las cohortes del piloto no pueden usarse en E3 ni en E4. Si las cohortes con seguimiento completo no alcanzan para el piloto, el desarrollo y la prueba, el plan de contingencia de DP-05 decide.
- El piloto solo puede ejecutarse con datos reales, por lo que también requiere DP-01, DP-02, DP-14, DP-15 y DP-18 resueltas. Hoy no se puede ejecutar.
- Cada corrida del piloto se registra como experimento exploratorio en el registro de trazabilidad (H2.7).
- Ningún resultado del piloto es evidencia del método: sirve solo para fijar los criterios del protocolo.
