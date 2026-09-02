# Estrategias de detección y cobertura

## Contenido

- [Modelo híbrido](#modelo-híbrido)
- [Estados](#estados)
- [Clasificación incremental](#clasificación-incremental)
- [Clasificación de fuentes](#clasificación-de-fuentes)
- [Layouts Python](#layouts-python)
- [Composición y trazabilidad](#composición-y-trazabilidad)
- [Representación interna y adaptadores](#representación-interna-y-adaptadores)
- [Cobertura por umbral](#cobertura-por-umbral)
- [Detectores incluidos](#detectores-incluidos)
- [Marcadores portables](#marcadores-portables)
- [Cómo adaptar un detector](#cómo-adaptar-un-detector)
- [Límites](#límites)

## Modelo híbrido

Combinar dos superficies:

1. **Comprobación determinista** para hechos estructurales con evidencia de alta
   confianza: archivos, operaciones OpenAPI, comandos reconocidos y enlaces.
2. **Revisión semántica** para propósito, reglas, permisos, decisiones y stacks
   no soportados.

El script no sustituye el análisis. Su función es detectar brechas repetibles y
explicar qué no pudo evaluar.

## Clasificación de fuentes

Antes de detectar capacidades, cada archivo recibe un rol:

| Rol | Uso |
| --- | --- |
| `active` | Puede representar el contrato vigente |
| `corroborating` | Respalda un hecho activo, pero no lo crea por sí solo |
| `test` | Verifica comportamiento; no activa capacidades desplegadas |
| `historical` | Migraciones y evolución pasada; contextualiza, no activa |
| `tooling` | Implementación del propio validador; nunca es dominio |

Se excluyen además fixtures, ejemplos, dependencias, cachés y artefactos
generados. Los nombres `test_*.py`, `*_test.py`, `*.test.*` y `*.spec.*` se
clasifican como pruebas aunque estén fuera de una carpeta convencional. El test
portable `scripts/test_validator.py` y el validador se excluyen explícitamente.

En Python, un marcador `MEMORY_*` solo es válido dentro de un token de
comentario. Una cadena usada como fixture no puede activar endpoints, comandos,
entidades, relaciones, campos o capas.

Las migraciones se presentan con confianza `HISTORICAL`. Sirven para explicar
la evolución o contrastar el modelo, pero una relación retirada no se convierte
en contrato vigente. Si una migración menciona ambos extremos de una relación
activa, su procedencia se añade como `CORROBORATING`; la confirmación sigue
naciendo del modelo actual. Cuando no exista snapshot o modelo activo suficiente,
la vigencia debe revisarse semánticamente.

## Layouts Python

La identidad modular se resuelve antes de enlazar imports. El detector reconoce
la raíz convencional `src/` y declaraciones compatibles en `pyproject.toml`
para setuptools, Poetry, Hatch y PDM. Conserva además la raíz plana para scripts
fuera del paquete y elige la raíz aplicable más específica.

Una raíz declarada pero ausente produce `NOT_EVALUATED`; no se reinterpreta el
import desde otra ubicación. Layouts con generación de paquetes, monorepos o
configuración dinámica requieren un adaptador futuro o revisión explícita.

## Composición y trazabilidad

El detector conserva un grafo interno antes de comparar documentos. Para HTTP,
una operación puede resultar de `prefijo del router padre + prefijo de
inclusión + prefijo del router hijo + ruta del decorador`. Para persistencia,
una relación enlaza entidad lógica, nombre físico, campo propietario y
declaración de clave foránea. Reducir estas cadenas a una coincidencia textual
aislada produciría falsos avisos y explicaciones imposibles de auditar.

Cada hallazgo derivado incluye:

- **confianza `CONFIRMED`** cuando todos los segmentos necesarios se resolvieron
  de manera estática;
- **confianza `UNRESOLVED`** y estado `NOT_EVALUATED` cuando un prefijo, una
  inclusión o una entidad destino depende de runtime o no puede enlazarse;
- **evidencia** con archivo, línea y pasos relevantes de registro o relación.

La evidencia enseña por qué se activó la obligación y permite corregir el
detector si interpretó mal una construcción. No prueba por sí sola propósito,
acceso, cardinalidad, cascadas ni comportamiento de runtime.

## Representación interna y adaptadores

La representación interna tiene `schema_version` propio y separa operaciones,
relaciones, procedencia, confianza, rol de fuente y dependencias estáticas. La
salida JSON expone `ir_schema_version`; cambiar de forma incompatible esa
representación exige incrementar su versión aunque la CLI conserve opciones.

El adaptador de acceso también tiene schema independiente. Sus reglas mapean un
símbolo de `Depends` o `Security` a una clasificación, pero el núcleo conserva
la responsabilidad de localizar la dependencia, componer la ruta y emitir
`evidence` y `confidence`. No se importa código ni se aceptan endpoints
declarados por el adaptador. Ver la interfaz completa en
[portable-standard.md](portable-standard.md#adaptadores-estáticos-de-acceso).

## Estados

| Estado | Significado | Efecto predeterminado |
| --- | --- | --- |
| `OK` | Controles estructurales soportados sin brechas | No sustituye revisión semántica |
| `ERROR` | Brecha verificable de alta confianza | Exit code distinto de cero |
| `WARN` | Deriva probable o decisión que revisar | No bloquea |
| `N/A` | Sin señales de la capacidad en superficies inspeccionadas | No prueba ausencia en stacks desconocidos |
| `NOT_EVALUATED` | Detector ausente, parcial o entrada ilegible | No afirmar conformidad |

El modo estricto trata advertencias o áreas no evaluadas como fallo, pero solo
endurece los controles estructurales soportados. No convierte una inferencia de
baja confianza en error ni certifica propósito, reglas o vigencia semántica.

## Clasificación incremental

Relacionar archivos cambiados con memoria que debe revisarse:

| Señal en el diff | Memoria a revisar | Pregunta didáctica |
| --- | --- | --- |
| Routers, controladores, OpenAPI | `docs/api.md` | ¿Cambió el contrato observable? |
| Entrypoints, comandos, parsers | `docs/cli.md` | ¿Cambió cómo se invoca o responde? |
| Modelos, schema, migraciones | `docs/modelo-datos.md` | ¿Cambió forma, significado o integridad? |
| Servicios, stores, vistas, auth | `context.md` | ¿Cambió una regla, permiso, estado o flujo? |
| Dependencias o carpetas nuevas | instrucciones de capa | ¿Existe una nueva forma de trabajar? |
| Configuración, variables, Compose | `docs/entorno.md` | ¿Cambió lo necesario para ejecutar? |
| Procesos e integraciones | `docs/arquitectura.md` | ¿Cambió un límite o flujo global? |

Una señal obliga a revisar; no demuestra por sí sola que el documento deba
cambiar. Si no cambia, explicar la razón al cierre.

## Economía de contexto

La clasificación L0–L4, los perfiles, presupuestos, escalamiento y reglas de
validación proporcional viven en
[resource-efficiency.md](resource-efficiency.md). Esta referencia solo aplica
esas reglas a la detección: conservar evidencia leída, limitar el inventario a
la superficie afectada y marcar como `NOT_EVALUATED` cualquier cobertura que el
detector no pueda sostener.

## Cobertura por umbral

| Umbral | Automático | Revisión humana obligatoria |
| --- | --- | --- |
| Primer endpoint | Sí, en OpenAPI y rutas Python estáticas, incluidos prefijos compuestos | Stacks no reconocidos y rutas dinámicas |
| Cambio de endpoint | Parcial: método, ruta y acceso detectables | Cuerpos, errores, permisos dinámicos |
| Diseño orientado a recursos | Estructura declarada, campos obligatorios y conflictos explícitos | Clasificación, jerarquía, propiedad y aplicabilidad CRUD |
| Primer comando CLI | Sí, para estrategias declaradas | Plugins y registro dinámico |
| Cambio de CLI | Parcial: comandos inventariados | Argumentos, salida y códigos no detectables |
| Segunda entidad relacionada | Parcial: Django, SQLAlchemy y SQLModel soportado | ORM no reconocido y relaciones calculadas |
| Cambio de modelo | Parcial: entidad, campo, FK simple o compuesta soportada | Índices, cascadas y semántica |
| Primera capa | Heurística por rutas conocidas | Límite arquitectónico real |
| Cambio de capa | No concluyente | Convenciones y validaciones propias |
| Primer módulo | Heurística por estructura o marcador | Responsabilidad funcional |
| Cambio de módulo | No concluyente | Reglas, estados, permisos y flujo |
| Módulo frontend concentrado | Tamaño de `index.vue` y guía frontend | Límites, subflujos y reutilización real |
| Nueva variable o servicio | No concluyente | Propósito, obligatoriedad y seguridad |
| Cambio global | No concluyente | Componentes, integraciones y flujo |

Cuando una fila sea parcial, informar la parte comprobada y la parte pendiente.

## Detectores incluidos

El validador reconoce de forma conservadora:

- OpenAPI JSON estructural y YAML cuando existe un parser compatible;
- decoradores HTTP Python explícitos mediante AST; composición de `APIRouter`,
  `FastAPI`, `include_router`, prefijos anidados y constantes locales o
  importadas que puedan resolverse estáticamente;
- raíces Python planas o `src/` y configuraciones estáticas habituales de
  empaquetado en `pyproject.toml`;
- acceso FastAPI mediante dependencias estáticas respaldadas por el adaptador
  opcional de proyecto;
- comandos Python `argparse`, Click y Typer en formas declaradas;
- entidades y relaciones Django, SQLAlchemy y tablas SQLModel; incluye
  anotaciones `Mapped`, `Field(foreign_key=...)`,
  `mapped_column(ForeignKey(...))` y `ForeignKeyConstraint` declarativa;
- marcadores portables para stacks no soportados;
- capas mediante rutas de implementación conocidas;
- módulos mediante `module.json` o directorios convencionales;
- raíces frontend convencionales (`frontend/src/modules`, `web/src/modules` o
  `client/src/modules`) y su guía de organización;
- contextos indexados, secciones base, enlaces, tokens de plantilla y adopción.

Desde la adopción de la directiva HTTP, también comprueba la forma documental
de la clasificación, los propietarios declarados, la referencia canónica, las
omisiones CRUD justificadas y autoridades canónicas incompatibles que estén
explícitas. No clasifica semánticamente rutas por expresiones regulares.

La inspección activa omite dependencias, artefactos de compilación, cachés y
directorios convencionales de pruebas, fixtures y ejemplos; separa las
migraciones como historia. Esas rutas
pueden contener APIs o modelos deliberadamente ficticios y no son evidencia del
contrato desplegable del proyecto.

Si encuentra evidencia de un stack que no puede interpretar, debe producir
`NOT_EVALUATED`, no `N/A`.

Una clase SQLModel solo se trata como entidad persistente cuando declara
`table=True` o un nombre físico explícito. Un schema de entrada o salida sin
tabla es un DTO, aunque herede de SQLModel. Una propiedad terminada en `_id`
sin constraint tampoco demuestra una relación.

Una ruta Python comentada no es evidencia de endpoint. El acceso que no pueda
deducirse de OpenAPI o de un marcador explícito queda `NOT_EVALUATED`. Cuando
existe una CLI, el script recuerda que argumentos, salida, códigos y efectos
requieren revisión semántica. El mensaje global `OK` solo resume comprobaciones
estructurales y nunca equivale a “la memoria es correcta en todo”.

La comprobación frontend es condicional y conservadora. Si existe una raíz
convencional, exige `docs/frontend.md` con una sección de organización y una de
revisión de módulos. También emite `WARN` cuando un `index.vue` supera 300
líneas: es una señal para revisar coordinación y separación, no prueba de una
arquitectura incorrecta. No exige `filtro.vue`, `listado.vue`, `formulario.vue`
ni `detalle.vue`; crear piezas sin responsabilidad sería una falsa conformidad.

Un `APIRouter` declarado pero sin una cadena de inclusión estática no se trata
como endpoint desplegado: queda `NOT_EVALUATED`. Esto evita exigir documentación
por código muerto, ejemplos o routers que aún no se registraron.

Una entidad ORM no equivale a un recurso público, un segmento sustantivo no
demuestra un concepto, una carpeta o router no establece propiedad y la
profundidad de una URL no prueba una jerarquía de dominio. Si falta una
clasificación explícita o la evidencia no permite verificar su corrección, el
resultado semántico es `NOT_EVALUATED`, nunca una categoría inventada.

No existe una opción para convertir una revisión manual en `OK` por simple
atestación. Si un consumidor necesita un gate estricto verde para una dimensión
parcial, debe añadir un adaptador determinista con fixtures o mantener el
validador en modo informativo; no silenciar el límite mediante un manifiesto.

Los tokens de plantilla usan `{{MAYUSCULAS_CON_GUIONES_BAJOS}}` sin espacios y
se rechazan incluso dentro de ejemplos cercados; deben resolverse antes de
copiar al consumidor. Expresiones de frameworks como `{{ user.name }}` y
comentarios HTML dentro de un bloque de código no se tratan como placeholders.

## Marcadores portables

Los marcadores son un contrato explícito para un consumidor cuyo stack no tenga
adaptador. Colocarlos junto a la declaración canónica o generar un inventario
local durante la instalación.

```text
MEMORY_ENDPOINT GET /orders authenticated
MEMORY_CLI_COMMAND orders-export
MEMORY_ENTITY Order
MEMORY_RELATION Order Customer
MEMORY_FIELD Order total
MEMORY_LAYER backend
```

No usar marcadores para ocultar una limitación sin documentarla. Explicar en
`docs/procedimientos.md` dónde viven y cómo mantenerlos.

No crear un manifiesto local para declarar capas, capacidades o consumidores.
Las capas se infieren de rutas de implementación conocidas; una estructura no
reconocida queda para revisión semántica o para un adaptador probado. Una ruta
con nombre conocido es solo candidata y produce `NOT_EVALUATED`; el marcador
explícito confirma el límite y hace bloqueante la ausencia de sus instrucciones.

## Cómo adaptar un detector

1. Definir qué evidencia del framework es canónica.
2. Decidir qué resultados son de alta confianza y cuáles requieren revisión.
3. Añadir fixture positivo mínimo.
4. Añadir fixture negativo que no debe activar la capacidad.
5. Añadir caso de deriva.
6. Añadir entrada inválida y caso adversarial.
7. Documentar limitaciones y exclusiones.
8. Ejecutar el corpus completo antes de convertir el hallazgo en bloqueante.

Priorizar stacks usados por consumidores reales. No anunciar compatibilidad por
tener una regex que coincide con un ejemplo.

## Límites

Requieren revisión o adaptación explícita:

- rutas o prefijos calculados en runtime, fábricas de routers, montajes ASGI y
  reescrituras externas de proxy;
- layouts de monorepo o paquetes generados que no estén declarados de forma
  estática;
- comandos registrados mediante plugins;
- permisos o contratos calculados dinámicamente;
- GraphQL, gRPC u otros transportes sin adaptador;
- relaciones polimórficas, constraints o índices de ORM no reconocido;
- reconstrucción completa del estado final desde una cadena arbitraria de
  migraciones; se necesita modelo o snapshot activo;
- nullabilidad, cardinalidad, cascadas e índices que no estén expresados por
  una construcción soportada y contrastados con migraciones;
- variables inyectadas fuera del repositorio;
- propósito y límites semánticos de módulos;
- documentación histórica que no representa contratos activos.

El ejecutable requiere un shell POSIX y Python 3.10 o posterior. Su launcher
inicia el primer intérprete con modo aislado (`python3 -I`) antes de cargar
`sitecustomize` o las dependencias del validador. Así, ni `scripts/` ni
`PYTHONPATH` pueden ejecutar por sombreado un `json.py`, `ast.py` o `yaml.py` del
consumidor. Debe invocarse directamente; `python3 scripts/validate-project-memory`
omite el aislamiento inicial. PyYAML es opcional: sin él, OpenAPI YAML queda
`NOT_EVALUATED`; OpenAPI JSON no requiere esa dependencia.

Los detectores textuales de lenguajes no Python siguen siendo conservadores y
no cubren todos los frameworks. La ausencia de una señal reconocida nunca debe
usarse como prueba absoluta de que un repositorio arbitrario carece de esa
capacidad.

No iniciar servicios, consultar APIs reales ni leer secretos para aumentar la
cobertura. Una limitación declarada es preferible a un falso verde.
