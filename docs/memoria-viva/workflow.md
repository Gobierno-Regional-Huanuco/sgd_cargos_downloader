# Flujo operativo didáctico

## Contenido

- [Qué significa memoria viva](#qué-significa-memoria-viva)
- [Preflight](#preflight)
- [Inventario de capacidades](#inventario-de-capacidades)
- [Matriz de umbrales](#matriz-de-umbrales)
- [Modo Inicializar](#modo-inicializar)
- [Modo Auditar](#modo-auditar)
- [Modo Mantener](#modo-mantener)
- [Modo Actualizar estándar](#modo-actualizar-estándar)
- [Cierre](#cierre)

## Qué significa memoria viva

La memoria viva no es una colección de archivos creados una vez. Es el vínculo
verificable entre capacidades actuales y explicaciones útiles para quien deba
mantenerlas después.

Por ejemplo, agregar `POST /orders` no obliga únicamente a que exista
`docs/api.md`. Obliga a comprobar que el documento explique método, ruta,
acceso, entrada, salida, errores y relación con schemas ejecutables. El archivo
puede existir y seguir desactualizado.

Aplicar siempre este ciclo:

```text
capacidad anterior → cambio → capacidad actual
        ↓                         ↓
 memoria anterior   →     memoria sincronizada
```

## Preflight

Antes de editar, mostrar:

1. Raíz, modo y alcance autorizado.
2. Perfil de recursos y presupuesto operativo inicial.
3. `.github/prompts/base_universal.prompt.md`, instrucciones y memoria leídas.
4. Lecturas requeridas que no pudieron completarse y por qué.
5. Capacidades relevantes encontradas y su evidencia.
6. Umbrales que podrían activarse.
7. Archivos previstos y qué conocimiento pertenece a cada uno.
8. Validaciones que demostrarán el resultado.

El preflight no es ceremonia: permite al desarrollador corregir una inferencia
antes de que se convierta en documentación falsa.

## Economía de contexto

Antes de abrir lectura amplia, clasificar el trabajo por nivel operativo y
declarar un presupuesto. La exploración avanza por evidencia inmediata,
dependencias directas y solo después fuentes transversales, siempre con una
duda concreta que justifique el salto.

Una fuente ya leída y sin cambios se reutiliza mediante el registro de
evidencia; no se relee íntegramente si no puede cambiar la decisión. Si el nivel
sube o el presupuesto se agota, la ejecución se detiene antes de ampliar el
alcance.

## Validación durante el trabajo y antes del commit

Durante el modo Mantener, elegir primero la prueba o comprobación directamente
relacionada con la señal modificada. No ejecutar automáticamente la suite
completa en cada iteración cuando una validación focalizada pueda detectar la
regresión relevante.

La validación mínima por nivel es:

| Nivel | Durante la modificación | Antes del commit |
| --- | --- | --- |
| `L0` | Diff, estructura y lint del alcance | Suite completa solo si existe o si el cambio se agrupa con otros |
| `L1` | Pruebas del comportamiento afectado y validador focalizado | Recomendar suite completa |
| `L2` | Pruebas del módulo e integraciones directas | Recomendar suite completa; exigir la pertinente si la cobertura focalizada es insuficiente |
| `L3` | Suite pertinente, contrato y controles arquitectónicos | Suite completa o justificación explícita de no ejecución |
| `L4` | Validación estricta, seguridad y suite pertinente/completa | Suite completa obligatoria salvo bloqueo documentado |

La tabla no permite omitir controles de seguridad, autoridad canónica,
contratos HTTP afectados ni estados `NOT_EVALUATED`. “Antes del commit” es un
punto de recomendación o exigencia de validación; no implica que la skill deba
crear el commit ni que una prueba no ejecutada pueda informarse como superada.

Si no hay pruebas automatizadas, registrar esa ausencia y ejecutar el
validador, lint, comprobaciones de contrato y revisión manual disponibles. Las
salidas se conservan resumidas con código de salida, causa y ubicación.

Para cambios pequeños puede usarse el validador con `--changed` o `--module`.
Estas opciones limitan realmente la validación a la superficie declarada, pero
reportan `NOT_EVALUATED` para los controles globales omitidos. Antes del commit,
ejecutar el validador sin esas opciones para recuperar cobertura completa.

## Inventario de capacidades

Buscar evidencia en código, configuración, tests, contratos e historial. Usar
esta tabla como guía, no como sustituto de explorar el repositorio:

| Capacidad | Evidencia habitual | Memoria relacionada |
| --- | --- | --- |
| HTTP | OpenAPI, routers, controladores, tests de contrato | `docs/api.md` |
| CLI | entrypoints, parsers, scripts publicados, tests | `docs/cli.md` |
| Persistencia | modelos, migraciones, schema, constraints | `docs/modelo-datos.md` |
| Módulos | servicios, vistas, stores, autorización, estados | `context.md` |
| Capas | carpetas, dependencias y configuración del stack | `.instructions.md` |
| Entorno | variables de ejemplo, Compose, manifests, servicios | `docs/entorno.md` |
| Arquitectura | procesos, integraciones y flujo global | `docs/arquitectura.md` |

Explicar qué señal se usó. Si el stack no está soportado por el validador,
marcar la revisión como manual; no declarar que la capacidad no existe.

Una capa es una superficie tecnológica coherente con reglas, dependencias y
validaciones propias. API, CLI, dominio y persistencia no son automáticamente
cuatro capas si comparten el mismo runtime y convenciones. Un nombre de carpeta
solo propone una candidata; confirmar el límite mediante arquitectura,
dependencias, configuración y comandos antes de crear instrucciones.

## Matriz de umbrales

| Cambio detectado | Obligación documental |
| --- | --- |
| Primer endpoint HTTP | Crear `docs/api.md` |
| Primer recurso o familia HTTP | Adoptar la clasificación, propiedad y matriz CRUD aplicable |
| Cambio de endpoint existente | Actualizar `docs/api.md` |
| Ruta anidada, relación, proyección o consulta nueva | Revisar clasificación, ruta canónica y propietario |
| Acción personalizada | Justificar por qué no basta CRUD, una relación o un recurso nuevo |
| Operación CRUD añadida o retirada | Actualizar aplicabilidad, razón, compatibilidad y pruebas |
| Nombre público o ruta canónica renombrados | Definir sucesión, deprecación y autoridad de mutación |
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
| Primer frontend o cambio de estructura de módulos frontend | Crear o actualizar `docs/frontend.md` |

Evaluar la matriz antes de editar, después de explorar, al revisar el diff y
antes del cierre. Los cuatro momentos usan únicamente señales nuevas desde la
evaluación anterior; no hace falta releer de forma íntegra todo lo que no
cambió.

Cuando una fila HTTP se active, leer
[http-resource-design.md](http-resource-design.md) y revisar en los cuatro
momentos la clasificación de cada operación afectada, el propietario conceptual
y técnico, la ruta canónica, la aplicabilidad CRUD y cualquier diferencia entre
persistencia, dominio y superficie pública. No convertir un hallazgo estructural
en una conclusión semántica automática.

Cuando se detecte frontend, revisar además que cada `index.vue` coordine su
vista, que los subflujos no mezclen responsabilidades y que los recursos vivan
con su entidad o relación propietaria. Esta revisión no obliga a crear archivos
con nombres prefijados: listado, filtro, formulario y detalle se separan solo
cuando existen como responsabilidades reales.

## Modo Inicializar

### Objetivo de inicialización

Construir memoria suficiente para el proyecto actual, no llenar todas las
plantillas disponibles.

### Procedimiento de inicialización

1. Leer instrucciones existentes antes de decidir que falta un estándar.
2. Explorar estructura, stack, configuración, tests e historial reciente.
3. Identificar capas y módulos funcionales con evidencia concreta.
4. Revisar al menos una implementación representativa por capacidad relevante.
5. Separar hechos confirmados, inferencias y preguntas abiertas.
6. Presentar diagnóstico de artefactos existentes, faltantes y obsoletos.
7. Proponer archivos base y condicionales, explicando por qué aplica cada uno.
8. Adaptar plantillas; no copiar ejemplos ni tokens sin resolver.
9. Instalar el validador y enseñar cómo interpretar su salida.
10. Validar y registrar la adopción en `docs/guia_IA.md`.

### Resultado esperado

Un desarrollador nuevo debe poder ubicar componentes, ejecutar el proyecto,
entender contratos activos, reconocer reglas de negocio y saber cómo validar un
cambio sin leer todo el código desde cero.

## Modo Auditar

### Objetivo de auditoría

Determinar no solo qué falta, sino qué contenido dejó de representar al sistema.

### Procedimiento de auditoría

1. Ejecutar el validador y conservar códigos, evidencia y cobertura reportada.
2. Separar `ERROR`, `WARN`, `N/A` y `NOT_EVALUATED`.
3. Contrastar cada hallazgo con código, configuración, tests e historial.
4. Revisar semántica que el script no puede decidir: propósito, permisos,
   invariantes, excepciones y decisiones. Para HTTP incluye clasificación,
   jerarquía, propiedad, aplicabilidad CRUD y autoridad real de mutación.
5. Detectar duplicación, contradicciones y enlaces a fuentes inexistentes.
6. Reconocer mejoras locales superiores al molde y preservarlas.
7. Presentar hallazgos por severidad, evidencia, impacto y corrección propuesta.

Si el usuario pidió diagnóstico, terminar ahí. Un hallazgo no autoriza editar.

## Modo Mantener

### Objetivo de mantenimiento

Cerrar una tarea normal con código y memoria representando el mismo estado.

### Procedimiento de mantenimiento

1. Registrar el inventario relevante anterior al cambio.
2. Clasificar los archivos previstos mediante las estrategias de detección.
3. Leer contratos y contextos afectados antes de implementar.
4. Realizar el cambio autorizado sin expandir el alcance.
5. Inspeccionar el diff completo y actualizar incrementalmente el inventario de
   capacidades afectadas.
6. Identificar capacidades creadas, modificadas o retiradas. Reconstruir el
   inventario completo solo si se invalidaron sus límites o apareció una señal
   estructural, global o de autoridad canónica.
7. Si cambió HTTP, revisar clasificación, propietario, ruta canónica, CRUD y
   compatibilidad antes de actualizar la fuente normativa correspondiente;
   enlazar desde resúmenes.
8. Revisar que ejemplos, pruebas y procedimientos sigan siendo ejecutables.
9. Evaluar todos los archivos obligatorios y condicionales definidos en
   `AGENTS.md`. Ejecutar validaciones focalizadas relacionadas con el cambio;
   exigir las ampliadas cuando el nivel o el riesgo lo indiquen. Declarar las
   validaciones no ejecutadas. Contrastar contratos y modelos documentados
   contra el código real.

Un documento sin cambios no es evidencia de que siga vigente. Explicar por qué
no necesitó actualizarse cuando el diff tocó una categoría relacionada.

## Modo Actualizar estándar

### Objetivo de actualización

Migrar obligaciones y plantillas sin perder conocimiento válido del consumidor.

### Procedimiento de actualización

1. Leer skill, versión, fecha y versión anterior en `docs/guia_IA.md`.
2. Validar el formato SemVer sin asumir que una versión diferente es anterior.
3. Comparar la versión adoptada con la versión normativa de `SKILL.md`.
4. Inventariar adaptaciones y mejoras locales antes de aplicar el molde nuevo.
5. Explicar obligaciones añadidas, modificadas y retiradas.
6. Migrar por artefacto; no sobrescribir documentos completos.
7. Ejecutar pruebas y validador con la versión esperada proporcionada por la
   skill activa.
8. Registrar versión anterior, nueva versión y fecha únicamente al terminar.

Si el consumidor usa nombres históricos como `docs/contratos.md`, seguir la
migración segura descrita en el estándar portable.

## Cierre

Antes de cerrar o preparar un commit, además:

1. Inspeccionar el diff completo y repetir el inventario de capacidades.
2. Ejecutar `scripts/validate-project-memory` sin `--changed` ni `--module`.
3. Ejecutar Markdownlint sobre todo el repositorio.
4. Resolver errores y revisar advertencias con evidencia.
5. Revisar placeholders, enlaces, índices y contextos.
6. Declarar cada comprobación `NOT_EVALUATED` y la acción necesaria para
   recuperar su cobertura.

Reportar:

- capacidades antes y después;
- umbrales cruzados;
- fuentes de evidencia;
- memoria creada o sincronizada;
- documentos revisados que no necesitaron cambio y por qué;
- comandos ejecutados y resultados;
- cobertura automática, revisión manual y áreas no evaluadas;
- riesgos, pendientes y decisiones abiertas.
- nivel, perfil, presupuesto, escalamiento y resumen operativo conforme a la
  política de economía de recursos.

No cerrar con errores verificables, placeholders de plantilla o una afirmación
de conformidad que oculte cobertura desconocida.
