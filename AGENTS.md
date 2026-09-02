# Protocolo de memoria viva

## Rol y fuentes normativas

Este archivo es el punto de entrada operativo para cualquier agente que trabaje en el
repositorio. Define qué leer, qué mostrar y cómo cerrar; no reemplaza la memoria técnica ni
los contratos del proyecto.

Cada conocimiento vive en una sola fuente normativa:

| Conocimiento | Fuente |
| --- | --- |
| Transporte HTTP | `docs/api.md` |
| Interfaz CLI | `docs/cli.md` |
| Persistencia | `docs/modelo-datos.md` |
| Negocio, actores, permisos, estados y flujo | `context.md` del módulo |
| Componentes y flujo global | `docs/arquitectura.md` |
| Organización y límites de módulos frontend | `docs/frontend.md` |
| Variables, requisitos y servicios | `docs/entorno.md` |
| Convenciones compartidas | `docs/convenciones.md` |
| Comandos y validaciones | `docs/procedimientos.md` |
| Reglas propias de una capa | `.github/instructions/<capa>.instructions.md` |

Los resúmenes y prompts deben enlazar estas fuentes, no duplicarlas.

## Alcance y autorización

- Ajustarse a la petición actual y aplicar cambios mínimos relacionados.
- Si el usuario pide explicar, revisar, diagnosticar o proponer, no editar archivos ni ejecutar
  acciones que cambien estado.
- Una petición puntual, como proponer un commit, no autoriza actualizar memoria ni resolver
  hallazgos adyacentes. Informarlos y pedir autorización antes de actuar.
- No modificar otro repositorio sin autorización explícita para ese caso. La lectura de solo
  consulta no autoriza escrituras posteriores.
- No reordenar, reformatear ni corregir contenido ajeno al alcance.
- Una propuesta aprobada delimita la implementación. Si aparece una alternativa materialmente
  distinta, volver a consultar antes de cambiar de rumbo.

## Lectura y regla de evidencia

Antes de ejecutar cualquier comando, leer y aplicar
`.github/prompts/base_universal.prompt.md`,
`docs/memoria-viva/resource-efficiency.md` y las referencias locales enlazadas
bajo `docs/memoria-viva/`. Si el preámbulo base falta, tratarlo como un error
del estándar y no afirmar que el contexto obligatorio fue cargado. Registrar
de forma compacta propósito, alcance, nivel, perfil, presupuesto, salida
esperada y condición de escalamiento. Después del comando conservar código de
salida, causa, ubicación y archivos afectados.
No ejecutar la suite completa, historial amplio, red, paralelismo ni comandos
destructivos sin la justificación, autorización y escalamiento que exige esa
política.

Aplicar la referencia específica además de la política de recursos según la
tarea:

- `workflow.md`: cualquier ejecución de la skill y su cierre.
- `detection-strategies.md`: auditorías, mantenimiento y evaluación de
  cobertura.
- `http-resource-design.md`: diseño o revisión de recursos HTTP.
- `portable-standard.md`: instalación, actualización, migración y validación
  del estándar portable.
- `succession-parity.md`: evolución, sucesión o retirada de la skill
  predecesora.

Antes de editar:

1. Leer completas las instrucciones aplicables desde la raíz hasta la ruta afectada.
2. Leer `docs/guia_IA.md`, `docs/convenciones.md` y `docs/procedimientos.md`.
3. Leer la instrucción de cada capa y el `context.md` de cada módulo afectado.
4. Leer la fuente normativa correspondiente si la tarea toca API, CLI, persistencia,
   arquitectura o entorno.
5. Explorar código, configuración, pruebas e historial en la profundidad necesaria para
   respaldar el cambio.
6. Evaluar todos los archivos obligatorios y condicionales definidos en este
   `AGENTS.md`; declarar los que no apliquen y la evidencia de esa decisión.

No afirmar que se siguió este protocolo si falta una lectura requerida. Declarar el archivo no
leído y la razón antes de editar. No completar vacíos con suposiciones.

## Conflictos y ambigüedades

Si dos instrucciones, el código y la documentación, o dos fuentes normativas se contradicen:

1. Detener las ediciones afectadas.
2. Mostrar las dos evidencias con sus rutas.
3. Explicar qué decisión cambia y qué riesgo tiene cada alternativa.
4. Pedir confirmación cuando no exista una fuente de mayor prioridad que resuelva el conflicto.

No corregir una contradicción eligiendo silenciosamente la opción más conveniente.

## Preflight obligatorio

Antes de editar, mostrar de forma breve:

- raíz, alcance y tipo de tarea;
- perfil de recursos y presupuesto operativo inicial;
- instrucciones y memoria realmente leídas;
- capacidades iniciales y umbrales aplicables;
- evidencia que respalda el cambio;
- archivos previstos y propósito de cada uno;
- validaciones por capa y del proyecto;
- ambigüedades, límites de detección o autorizaciones pendientes.

Si la tarea es diagnóstica, el preflight debe declarar que no habrá ediciones.

## Loop obligatorio

1. Inventariar las capacidades antes del cambio.
2. Clasificar fuentes activas, pruebas, tooling y migraciones históricas;
  declarar nivel operativo y presupuesto antes de ampliar la exploración;
  resolver las raíces reales del código antes de enlazar imports.
3. Explorar la implementación y resolver conflictos o dudas.
4. Aplicar únicamente el cambio autorizado.
5. Inspeccionar el diff completo, incluida cualquier modificación preexistente relevante.
6. Inventariar las capacidades después del cambio.
7. Evaluar todos los umbrales y sincronizar la fuente normativa afectada.
8. Ejecutar `scripts/validate-project-memory` y las validaciones reales del proyecto.
9. Revisar resultados, advertencias y áreas no soportadas antes de cerrar.

## Umbrales persistentes

| Cambio detectado | Obligación documental |
| --- | --- |
| Primer endpoint HTTP | Crear `docs/api.md` |
| Primer recurso o familia HTTP | Clasificar operaciones y registrar propiedad y CRUD aplicable |
| Cambio de endpoint existente | Actualizar `docs/api.md` |
| Ruta anidada, relación, proyección, consulta o acción | Revisar tipo, ruta canónica, propietario y justificación |
| CRUD o nombre público añadido, retirado o renombrado | Revisar omisiones, compatibilidad y autoridad de mutación |
| Primer comando CLI | Crear `docs/cli.md` |
| Cambio de argumentos, salida o códigos CLI | Actualizar `docs/cli.md` |
| Segunda entidad relacionada | Crear `docs/modelo-datos.md` |
| Cambio de entidad, campo, relación o constraint | Actualizar `docs/modelo-datos.md` |
| Primera implementación en una capa | Crear `.github/instructions/<capa>.instructions.md` |
| Cambio de reglas propias de una capa | Actualizar sus instrucciones |
| Primer módulo funcional | Crear su `context.md` e indexarlo |
| Cambio de reglas, estados, permisos o flujo | Actualizar el `context.md` |
| Nueva variable o servicio | Actualizar `docs/entorno.md` |
| Cambio de componentes o flujo global | Actualizar `docs/arquitectura.md` |

Evaluar la matriz exactamente en cuatro puntos:

1. durante el preflight;
2. después de explorar código, configuración, pruebas e historial;
3. al inspeccionar el diff;
4. antes del cierre.

No basta con que un archivo exista: contrastar su contenido con la capacidad real. Si el cambio
cruza un umbral y crear el artefacto no estaba autorizado, explicar la brecha y pedir autorización
antes de ampliar el alcance.

Cuando cambien routers, controladores, handlers u OpenAPI, revisar en cada uno
de los cuatro momentos la clasificación declarada, el propietario conceptual y
técnico, la ruta canónica, la aplicabilidad CRUD y la compatibilidad. No inferir
esas decisiones desde el ORM, los segmentos de URL o la estructura de carpetas.

## Clasificación incremental

- Routers, controladores, OpenAPI y modelos de transporte: `docs/api.md`.
- Entrypoints, comandos y parsers: `docs/cli.md`.
- Modelos, esquemas y migraciones: `docs/modelo-datos.md`.
- Servicios, vistas, stores, reglas y autorización: `context.md` del módulo.
- Carpetas o tecnologías nuevas: instrucciones de la capa.
- Configuración, variables y servicios: `docs/entorno.md`.
- Componentes, integraciones y flujos globales: `docs/arquitectura.md`.

## Mejoras candidatas del estándar

Si un repositorio consumidor contiene una práctica que supera el molde:

1. Preservarla; no normalizarla a la baja ni copiarla al estándar por cuenta propia.
2. Mostrar la evidencia, el beneficio, los riesgos y la diferencia frente al estándar actual.
3. Pedir al operador que decida entre mantenerla local, promoverla o descartarla.
4. Si se aprueba promoverla, cambiar el estándar compartido solo dentro de un alcance autorizado.
5. Proponer por separado la migración de cada consumidor; nunca replicarla automáticamente.

Un hallazgo propio de otro repositorio se informa antes de registrarlo o resolverlo allí.

## Validación por capa

- Ejecutar los comandos documentados para cada capa afectada sobre el alcance apropiado.
- Durante cada modificación, ejecutar primero las pruebas de los flujos modificados y
  validaciones de contratos directamente relacionadas. Recomendar la suite completa antes
  del commit; exigirla antes del cierre para cambios críticos, estructurales o sin cobertura
  focalizada suficiente.
- Validar Markdown, enlaces, contextos indexados y ausencia de placeholders residuales.
- Tratar errores verificables del validador como bloqueo. Revisar cada advertencia con evidencia.
- Una comprobación `N/A` o no soportada no demuestra conformidad; declararla en el cierre.
- Un resultado global `OK` se limita a controles estructurales soportados; la revisión semántica
  de propósito, reglas, permisos y vigencia sigue siendo obligatoria.
- Si una validación no puede ejecutarse, explicar comando omitido, causa, riesgo y comprobación
  alternativa. No presentarla como superada.
- Si no existen pruebas automatizadas, declarar su ausencia y ejecutar las comprobaciones
  estructurales, de lint y manuales disponibles; no convertir la ausencia en conformidad.

## Seguridad y privacidad

No exponer secretos, credenciales, datos personales ni muestras reales innecesarias. No iniciar
servicios ni consultar sistemas externos para completar la memoria salvo autorización explícita.
Usar evidencia local y marcar la incertidumbre que requiera revisión humana.
No importar ni ejecutar módulos del proyecto desde el validador. Un adaptador de
acceso es configuración estática con evidencia local, no código ejecutable ni
una declaración libre de endpoints.

## Cierre obligatorio

Antes de terminar, mostrar:

- capacidades antes y después y umbrales cruzados;
- archivos modificados y memoria sincronizada;
- validaciones ejecutadas, comandos y resultados;
- advertencias, comprobaciones no aplicables o no soportadas;
- impacto en seguridad, privacidad y otros repositorios;
- riesgos, pendientes y preguntas abiertas.

Antes de cerrar o preparar un commit, además:

- inspeccionar el diff completo y repetir el inventario de capacidades;
- ejecutar `scripts/validate-project-memory` sin alcance;
- ejecutar Markdownlint sobre todo el repositorio;
- resolver errores y revisar advertencias con evidencia;
- revisar placeholders, enlaces, índices y contextos;
- declarar por separado cada comprobación `NOT_EVALUATED` y la acción
  necesaria para cubrirla;
- explicar por qué los documentos relacionados que no cambiaron siguen
  vigentes.
- entregar el resumen operativo con nivel, perfil, objetivo, archivos,
  comandos, validaciones, presupuesto, escalamiento, documentación, riesgos y
  pendientes, usando la plantilla de `docs/memoria-viva/resource-efficiency.md`.

No cerrar con errores verificables, memoria exigible desactualizada ni placeholders residuales.
