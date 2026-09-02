# Economía de contexto y trabajo proporcional

## Cuándo leer esta política

Leerla antes de ejecutar cualquier comando relacionado con una tarea que use
`gestionar-memoria-viva-proyecto`. La regla no es condicional al tamaño aparente
del cambio: cada comando debe respetar alcance, presupuesto, seguridad y
retención de evidencia. Esta política no sustituye los controles obligatorios
de la skill: los hace proporcionales.

## Principio

La profundidad de exploración, documentación y validación debe ser proporcional
al alcance y al riesgo del cambio. La skill no puede omitir controles
obligatorios, pero sí debe reutilizar evidencia vigente, limitar lecturas a las
superficies afectadas y evitar repetir análisis que no puedan cambiar la
decisión.

## Clasificación operativa

Clasificar el trabajo antes de una exploración amplia:

| Nivel | Tipo de cambio | Profundidad esperada |
| --- | --- | --- |
| `L0` | Trivial: texto, formato, typo, comentario | Archivo directo y validación mínima |
| `L1` | Localizado: método, componente, prueba o configuración aislada | Módulo afectado y dependencias directas |
| `L2` | Transversal: varios archivos o capas relacionadas | Capacidades relacionadas y memoria afectada |
| `L3` | Estructural: arquitectura, contratos, persistencia, permisos o propiedad conceptual | Inventario amplio y validación completa |
| `L4` | Crítico: seguridad, migración normativa, autoridad de escritura, estándar o cambio de alto riesgo | Procedimiento exhaustivo |

Se eleva el nivel cuando aparece cualquiera de estas señales: una segunda
autoridad canónica, una capa adicional, un contrato HTTP afectado, una relación
o persistencia no prevista, una contradicción documental, una migración
normativa, una validación global necesaria o una ampliación del alcance
autorizado.

No se rebaja un nivel ya justificado para ahorrar recursos. Si el nivel cambia
durante la ejecución, se detiene la fase actual antes de ampliar lectura,
escritura o validación.

## Presupuesto operativo

Cada preflight declara un presupuesto de trabajo. El presupuesto indica qué tan
lejos puede llegar la ejecución antes de pedir escalamiento.

Campos recomendados:

- `level_estimated`.
- `initial_files_max`.
- `files_inspected_max_without_escalation`.
- `files_modified_max_without_escalation`.
- `modules_max_without_escalation`.
- `history_policy`.
- `suite_policy`.
- `subagents_policy`.
- `command_output_policy`.
- `validation_policy`.
- `escalation_triggers`.

Valores iniciales conservadores recomendados:

- perfil `economical`.
- 6 archivos iniciales.
- 12 archivos como máximo sin escalamiento.
- 5 archivos modificables como máximo sin escalamiento.
- 1 módulo inicial.
- historial bajo demanda.
- suite completa prohibida sin justificación.
- subagentes deshabilitados por defecto.
- salida de comandos resumida.

Estos valores son defaults seguros, no permisos para relajar controles
críticos.

El presupuesto es un contrato operativo del agente, no un contador automático
de tokens impuesto por el validador. El agente debe registrarlo, detenerse al
superarlo y explicar el escalamiento. El validador solo comprueba la cobertura
estructural declarada y no debe fingir que puede medir razonamiento, contexto o
tiempo de ejecución. Los perfiles son defaults normativos; un consumidor puede
restringirlos, pero no ampliar controles críticos ni rebajar un nivel ya
justificado.

## Regla por comando

Antes de ejecutar cada comando o grupo homogéneo de comandos, registrar de
forma compacta:

- propósito;
- superficie y alcance;
- nivel y perfil;
- presupuesto que consumirá;
- salida esperada y límite de retención;
- riesgo, permisos y condición de escalamiento.

Después de ejecutarlo, conservar código de salida, causa y ubicación relevante;
actualizar el presupuesto y registrar archivos inspeccionados o modificados.
Los comandos pueden agruparse solo cuando comparten propósito, alcance, riesgo
y tratamiento de salida. No encadenar comandos para ocultar qué acción consumió
recursos o produjo un cambio.

Clasificar los comandos así:

| Clase | Ejemplos | Regla |
| --- | --- | --- |
| `C0` | navegación, `rg`, lectura puntual, `git status` | Permitido dentro del alcance y con salida limitada |
| `C1` | prueba focalizada, lint del cambio, validador parcial | Predeterminado durante la modificación |
| `C2` | suite de módulo, historial dirigido, validación ampliada | Requiere justificar expansión de presupuesto |
| `C3` | suite global, historial amplio, red, Docker o paralelismo | Requiere justificación y nivel compatible |
| `C4` | destrucción, credenciales, producción o escritura externa | Requiere autorización y controles de seguridad independientes |

La economía nunca autoriza automáticamente un comando `C4`. Un comando que
supera el presupuesto debe detenerse antes de ejecutarse y producir un
escalamiento. Si se trata de un control de seguridad obligatorio, se registra
la excepción y su motivo.

## Exploración progresiva

Aplicar tres capas de lectura:

1. evidencia inmediata: archivos mencionados, diff actual, error reportado,
   prueba afectada e instrucciones directas;
2. dependencias directas: contratos consumidos, servicios invocados, modelos
   implicados, configuración inmediata y pruebas asociadas;
3. evidencia transversal: arquitectura global, historial, módulos adicionales,
   documentación global e integraciones externas.

No subir de capa hasta identificar la duda concreta que la capa actual no puede
resolver.

## Reutilización de evidencia

Una fuente ya leída y no modificada no se relee íntegramente en cada fase. Se
conserva un registro compacto de evidencia y se actualizan solo las señales
nuevas desde la evaluación anterior.

Las cuatro evaluaciones de umbrales usan ese registro así:

1. preflight: hipótesis inicial;
2. tras explorar: actualización por nueva evidencia;
3. tras el diff: revisión de señales introducidas o modificadas;
4. antes del cierre: confirmación de estados, validaciones y pendientes.

Reevaluar no significa reinventariar todo el proyecto.

## Inventario incremental

Después del diff, actualizar de forma incremental el inventario de capacidades
afectadas. Solo reconstruir el inventario completo cuando el cambio invalide
límites, introduzca una nueva capa, altere contratos globales, modifique
propiedad conceptual, afecte la autoridad canónica de escritura o demuestre
que el inventario previo era insuficiente.

## Historial y comandos

El historial se consulta de forma dirigida cuando las fuentes activas no
resuelven una contradicción o una decisión histórica es material. Preferir
rutas, archivos o commits relevantes antes que un recorrido general.

Las salidas de comandos se filtran y resumen. Conservar siempre código de
salida, causa y ubicación relevante; descartar volcado repetitivo o
irrelevante.

## Validación proporcional

La validación debe seguir el nivel estimado:

- `L0`: revisión del diff, validación estructural mínima y lint del alcance
  tocado. No ejecutar una suite solo por una modificación textual, de formato
  o de comentarios.
- `L1`: prueba automatizada directamente relacionada, validador focalizado y
  lint del alcance tocado;
- `L2`: validación ampliada del módulo o capacidad afectada, incluyendo sus
  integraciones directas;
- `L3` y `L4`: validación completa o estricta, con controles de seguridad y
  contrato cuando apliquen.

`NOT_EVALUATED` sigue siendo cobertura parcial, no conformidad. Un presupuesto
reducido nunca autoriza a omitir controles obligatorios o a declarar éxito
global sin evidencia.

### Pruebas durante la modificación y antes del commit

Durante una modificación se ejecutan por defecto únicamente las pruebas
relacionadas con los archivos, módulo, capacidad o contrato afectados. La
relación debe poder explicarse: una prueba es pertinente si cubre directamente
el comportamiento modificado, una regresión conocida o una dependencia directa
que pueda romperse.

No ejecutar una suite completa en cada iteración solo porque existe. La suite
completa debe ejecutarse antes del commit o declararse como pendiente si el
operador decide no prepararlo todavía. En cambios `L3` o `L4`, en
seguridad, autoridad canónica, contratos globales, migraciones o cuando una
prueba focalizada no cubra las dependencias relevantes, la suite pertinente o
completa puede ser obligatoria antes del cierre.

Si no existen pruebas automatizadas, no se inventa una suite ni se considera
que la ausencia reduzca el riesgo. Se ejecutan las comprobaciones disponibles:
revisión del diff, validador, lint, comprobación de contrato y revisión manual
proporcional. La ausencia de pruebas se declara explícitamente.

Las salidas extensas de pruebas se resumen conservando código de salida,
prueba fallida, causa y ubicación. No volcar automáticamente la salida de una
suite completa al contexto.

Una recomendación de pre-commit no equivale a una prueba superada: el cierre
debe separar validaciones ejecutadas, omitidas y recomendadas para el commit.
El validador debe ejecutarse sin alcance para obtener cobertura global;
Markdownlint debe ejecutarse sobre todo el repositorio en ese mismo cierre.
`--changed` y `--module` son comprobaciones parciales y no sustituyen esa
ejecución final.

## Resumen operativo obligatorio

Toda tarea debe finalizar con un resumen operativo, aunque no produzca cambios
en archivos. El resumen debe permitir reconstruir qué se hizo, con qué alcance
y qué cobertura tuvo la validación.

Usar esta estructura:

```text
Nivel: L0 | L1 | L2 | L3 | L4
Perfil: economical | balanced | exhaustive
Objetivo atendido: <resultado concreto>

Archivos inspeccionados:
- <ruta o grupo de rutas>

Archivos modificados:
- <ruta y propósito del cambio>

Comandos ejecutados:
- <propósito> → <resultado y código de salida>

Validaciones ejecutadas:
- <validación> → <resultado>

Validaciones omitidas:
- <validación y motivo>, o "ninguna"

Resultados NOT_EVALUATED:
- <resultado y motivo>, o "ninguno"

Presupuesto y escalamiento:
- <presupuesto utilizado, ampliación justificada o "sin escalamiento">

Documentación actualizada:
- <contexto, contrato o guía>, o "ninguna"

Riesgos:
- <riesgo pendiente>, o "ninguno identificado"

Pendientes:
- <siguiente acción>, o "ninguno"
```

Los comandos deben resumirse por grupos homogéneos y no como una transcripción
completa de la terminal. El cierre debe distinguir siempre entre validaciones
ejecutadas, omitidas y no evaluadas; ninguna de estas categorías puede
presentarse como evidencia de conformidad de otra.

## Perfiles de recursos

| Perfil | Uso | Regla práctica |
| --- | --- | --- |
| `economical` | Cambios pequeños o localizados | Menor contexto posible compatible con rigor |
| `balanced` | Cambios transversales acotados | Expandir solo lo necesario para resolver la duda |
| `exhaustive` | Cambios estructurales o críticos | Contexto amplio, validación completa y mayor trazabilidad |

El perfil orienta el consumo de contexto; no reemplaza el juicio sobre riesgo.
Cuando la plataforma no permita cambiar de modelo entre fases, registrar el
perfil previsto y el perfil realmente usado.

## Escalamiento

Detenerse antes de superar el presupuesto cuando aparezca una de estas señales:

- sube el nivel;
- aparecen módulos adicionales;
- se supera el máximo de archivos;
- hace falta modificar más archivos;
- aparece otra autoridad propietaria;
- se requiere historial amplio;
- se necesita una suite global;
- surge una contradicción normativa;
- cambia una ruta canónica de escritura;
- hacen falta subagentes;
- aparece una capacidad nueva no prevista;
- el alcance autorizado deja de ser suficiente.

El mensaje de escalamiento debe declarar la razón, las fuentes adicionales y
la validación requerida antes de continuar.

## Salvaguardas

La economía de contexto no puede:

- ocultar contradicciones;
- omitir pruebas críticas;
- tratar `N/A` o `NOT_EVALUATED` como conformidad;
- evitar revisar seguridad o privacidad cuando correspondan;
- dejar de detectar una segunda autoridad de escritura;
- omitir contratos HTTP afectados;
- permitir modificar fuera del alcance;
- convertir el presupuesto en permiso para ignorar evidencia;
- reducir controles en cambios `L3` o `L4`;
- rebajar unilateralmente un nivel ya justificado.
