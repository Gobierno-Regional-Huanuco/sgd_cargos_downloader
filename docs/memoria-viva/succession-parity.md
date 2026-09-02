# Paridad con la skill predecesora

Leer esta referencia únicamente al evolucionar la skill o decidir el retiro de
`gestionar-memoria-proyecto`. La predecesora permanece congelada como evidencia;
no desarrollar dos estándares en paralelo.

## Capacidades conservadas o reincorporadas

| Capacidad | Destino en la sucesora | Evidencia actual |
| --- | --- | --- |
| Inicializar, Auditar y Mantener | `SKILL.md` y workflow | Flujo y forward test |
| Actualizar estándar y SemVer | `SKILL.md` y workflow | Pruebas de versión y downgrade |
| Inventario antes/después y umbrales | Workflow y `AGENTS.md` | Matriz evaluada en cuatro momentos |
| Fuente normativa única | Estándar portable y plantillas | Mapa por tipo de conocimiento |
| Artefactos condicionales | Estándar portable | Fixtures de API, CLI, datos, capa y módulo |
| Guarda contra expansión de alcance | `SKILL.md` y `AGENTS.md` | Preflight, conflicto y autorización |
| Regla de evidencia | `SKILL.md` y `AGENTS.md` | Lecturas y límites obligatorios |
| Conflictos entre fuentes | `SKILL.md` y `AGENTS.md` | Secuencia de detención y consulta |
| Preflight y cierre | Workflow y `AGENTS.md` | Checklists persistentes |
| Validación por capa | `AGENTS.md` e instrucción de capa | Comando, resultado y alternativa |
| Mejoras nacidas en consumidores | `SKILL.md` y `AGENTS.md` | Flujo de promoción con autorización |
| Diagnóstico profundo | Workflow y prompt de inicialización | Modo sin edición y plan con evidencia |
| Rename seguro de contratos | Estándar portable | Procedimiento con `git mv` y enlaces |
| Plantillas didácticas | `assets/standard/docs/` | Prueba dorada contra assets reales |
| Prompts por tarea | `.github/prompts/` | Shims finos sobre protocolo canónico |
| ER global con PK/FK | Plantilla de datos y validador | Fixture adversarial de atributos |

Todas las filas están reincorporadas y verificadas en esta revisión. Eso demuestra
paridad de diseño, no autoriza todavía retirar la predecesora: siguen pendientes
los pilotos y migraciones individuales descritos al final.

## Cambios normativos incorporados el 2026-08-03

La versión vigente se lee únicamente de `SKILL.md`; la fecha identifica este
incremento sin mantener otra copia manual del número normativo.

- Reincorpora gobernanza, preflight, cierre y explicación didáctica completa.
- Alinea las plantillas enriquecidas con el contrato estructural del validador.
- Separa `N/A`, `NOT_EVALUATED` y `OK` estructural sin prometer conformidad
  semántica.
- Añade SemVer estricto, protección contra downgrade y comparación explícita
  durante una actualización.
- Aísla imports del consumidor, rechaza symlinks base y evita interpretar
  comentarios o ejemplos Markdown como capacidades y placeholders.
- Amplía fixtures a OpenAPI, Spring no soportado, Django, SQLAlchemy moderno,
  Click, código cercado, casos adversariales y assets reales.
- Mantiene argumentos, salidas y códigos CLI, permisos dinámicos, constraints,
  índices, variables y semántica de módulos como revisión humana declarada.

Evidencia reproducible principal: `test_28` a `test_32` cubren evolución SemVer;
`test_37` a `test_47`, seguridad, falsos positivos y cobertura honesta;
`test_48`, compatibilidad entre las plantillas reales y el validador; y
`test_49`, confirmación explícita de capas. El forward test temporal complementa
el corpus con una inicialización completa y no cuenta como autorización para
migrar consumidores reales.

## Incremento de composición y procedencia del 2026-08-03

La observación del piloto sobre `APIRouter` y SQLModel se generalizó como dos
grafos de contratos, no como excepciones para FastAPI y SQLite:

- compone rutas a través de routers anidados, `include_router` y constantes
  estáticas locales o importadas;
- marca prefijos, inclusiones y rutas dinámicas como no evaluadas en vez de
  emitir una URL parcial falsa;
- enlaza entidades lógicas con nombres físicos y claves foráneas declaradas en
  SQLModel, SQLAlchemy y constraints compuestas;
- excluye DTO SQLModel sin tabla y referencias por convención `_id` sin FK;
- añade procedencia y confianza a salida humana y JSON.

Los casos `test_50` a `test_62` protegen composición anidada e importada,
dinamismo, falsos positivos de DTO, claves simples, compuestas y no resueltas,
routers no montados, alias y el contrato de evidencia. La revisión humana sigue
siendo obligatoria para runtime, proxy, permisos, cardinalidad, cascadas,
índices y semántica.

## Incremento de fuentes y extensibilidad del 2026-08-03

El punto publicado anterior quedó congelado en `674a4b3`; el nuevo incremento
no reescribe ese artefacto y formaliza la inmutabilidad después de adopción.

- Clasifica implementación activa, tests, tooling y migraciones históricas
  antes de detectar capacidades.
- Interpreta marcadores Python únicamente en comentarios y excluye el corpus
  portable aunque se copie al consumidor.
- Resuelve raíz plana y layouts `src/` desde convención o configuración estática
  de `pyproject.toml`.
- Evita que migraciones retiradas activen el modelo vigente y conserva su
  procedencia con confianza `HISTORICAL`.
- Versiona la representación interna y la interfaz JSON de adaptadores.
- Permite mapear dependencias FastAPI a acceso sin ejecutar código ni declarar
  rutas desde configuración.

Los casos posteriores a `test_62` cubren contaminación por fixtures, roles de
fuente, layouts, historia de persistencia, reglas de acceso, conflictos,
evidencia JSON y entradas adversariales.

## Incremento de diseño HTTP orientado a recursos del 2026-08-03

La evolución posterior a `1.3.0` añade una directiva condicional para gobernar
la interfaz HTTP durante Inicializar, Auditar, Mantener y Actualizar estándar:

- clasifica explícitamente recursos, subrecursos, relaciones, proyecciones,
  consultas calculadas y acciones;
- evalúa CRUD sin volverlo universal y exige razón para cada omisión;
- separa propiedad conceptual, módulo propietario, ruta canónica y rutas
  contextuales para evitar autoridades de escritura duplicadas;
- mantiene modelo de persistencia, dominio y contrato público desacoplados;
- verifica solo estructura declarada y conserva como `NOT_EVALUATED` las
  decisiones semánticas que requieren evidencia humana.

Los casos `test_80` a `test_97` cubren las seis categorías, propiedad, omisiones,
conflictos, rutas dinámicas, independencia del ORM, contenido adversarial,
salida JSON y migración compatible desde `1.3.0`.

## Capacidades reemplazadas

| Diseño anterior | Reemplazo |
| --- | --- |
| Auditoría solo por LLM | Validador determinista más revisión semántica |
| Lectura exhaustiva para toda tarea | Lectura guiada por impacto |
| Ocho prompts con reglas duplicadas | Prompts finos enlazados a `AGENTS.md` |
| Dos capas fijas | Instrucciones por cada capa real |
| Validación solo Markdown | Validación estructural, cobertura y Markdown |
| Ausencia de versión adoptada | SemVer y registro informativo |

## Capacidades retiradas deliberadamente

- Supuestos obligatorios de Laravel, Vue, Pinia o CRUD universal. Los recursos
  HTTP evalúan las cinco capacidades y justifican excepciones; no se obliga a
  implementarlas cuando no corresponden al dominio.
- Referencias a una carpeta `_standard/` inexistente.
- Copia automática de todos los artefactos condicionales.
- Duplicación completa del protocolo en cada prompt.
- Aprobaciones adicionales cuando el usuario ya autorizó claramente el cambio y
  no existe ambigüedad, riesgo ni ampliación de alcance.

## Criterios de retiro de la predecesora

1. Todas las filas de paridad tienen implementación y prueba o una decisión de
   retiro aprobada.
2. Los umbrales declaran cobertura automática, manual o no soportada.
3. El validador no confunde `N/A` con `NOT_EVALUATED` y no tiene excepciones no
   controladas en el corpus.
4. Las plantillas conservan profundidad de API, CLI, datos, arquitectura,
   entorno, capas y módulos.
5. Los pilotos autorizados no dejan falsos bloqueos críticos sin resolver.
6. Los consumidores se migran individualmente y registran su versión.
7. Catálogos y metadatos presentan solo la sucesora como activa.
8. La predecesora queda recuperable en Git y el operador aprueba el retiro.
