# Estándar portable y didáctico

## Contenido

- [Propósito](#propósito)
- [Artefactos base](#artefactos-base)
- [Artefactos condicionales](#artefactos-condicionales)
- [Fuentes normativas](#fuentes-normativas)
- [Cómo adaptar una plantilla](#cómo-adaptar-una-plantilla)
- [Instalación del validador](#instalación-del-validador)
- [Publicación e inmutabilidad](#publicación-e-inmutabilidad)
- [Adaptadores estáticos de acceso](#adaptadores-estáticos-de-acceso)
- [Migración segura de nombres](#migración-segura-de-nombres)
- [Calidad de la documentación](#calidad-de-la-documentación)

## Propósito

El estándar portable enseña dónde vive cada clase de conocimiento y cómo
mantenerla. Las plantillas son guías de razonamiento, no archivos para copiar
sin leer.

Cada documento debe responder cuatro preguntas:

1. ¿Qué necesita entender un desarrollador?
2. ¿Qué evidencia demuestra que la explicación es correcta?
3. ¿Qué otra fuente contiene el detalle ejecutable?
4. ¿Qué cambio futuro obliga a revisarlo?

## Artefactos base

Instalar y adaptar siempre:

| Artefacto | Qué enseña o controla |
| --- | --- |
| `AGENTS.md` | Orden de lectura, alcance, ciclo de cambio y cierre |
| `CLAUDE.md` | Carga el mismo protocolo sin duplicarlo |
| `.markdownlint-cli2.yaml` | Calidad mecánica de Markdown |
| `docs/guia_IA.md` | Adopción del estándar e índices de contexto |
| `docs/convenciones.md` | Patrones confirmados del código |
| `docs/procedimientos.md` | Comandos y pasos operativos reproducibles |
| `docs/memoria-viva/` | Copia local de las referencias explicativas del estándar |
| `docs/arquitectura.md` | Componentes, límites y flujo global |
| `docs/entorno.md` | Runtimes, variables y servicios necesarios |
| `docs/context-template.md` | Estructura mínima del conocimiento de módulo |
| `.github/copilot-instructions.md` | Remite al protocolo canónico |
| `.github/prompts/*.prompt.md` | Activa tareas recurrentes sin duplicar normas |
| `scripts/validate-project-memory` | Comprueba brechas verificables sin la skill |

Un archivo base puede ser breve en un proyecto pequeño, pero debe contener
información real. No considerar completa una plantilla que solo conserva sus
encabezados.

## Artefactos condicionales

Las plantillas existen dentro de la skill para estar disponibles cuando se
cruce el umbral. No crearlas antes:

| Evidencia actual | Artefacto que pasa a ser obligatorio |
| --- | --- |
| Al menos un endpoint HTTP real | `docs/api.md` |
| Al menos un comando CLI propio | `docs/cli.md` |
| Dos entidades relacionadas | `docs/modelo-datos.md` |
| Implementación real en una capa | `.github/instructions/<capa>.instructions.md` |
| Módulo con responsabilidad funcional | `<módulo>/context.md` |
| Raíz frontend convencional | `docs/frontend.md` |

Crear documentos vacíos “por si acaso” reduce confianza: hace imposible saber
si su existencia representa una capacidad real.

## Fuentes normativas

| Conocimiento | Fuente documental | Evidencia ejecutable habitual |
| --- | --- | --- |
| Transporte HTTP | `docs/api.md` | OpenAPI, routers, tests de contrato |
| Convención HTTP transversal | `docs/convenciones.md` | Contrato, decisiones y código representativo |
| Interfaz CLI | `docs/cli.md` | entrypoints, parser, tests CLI |
| Semántica de persistencia | `docs/modelo-datos.md` | schema, modelos, migraciones |
| Negocio, permisos y estados | `<módulo>/context.md` | servicios, autorización, tests |
| Componentes y flujo global | `docs/arquitectura.md` | configuración y puntos de entrada |
| Variables y servicios | `docs/entorno.md` | ejemplos de entorno y manifests |
| Protocolo operativo | `AGENTS.md` | instrucciones del repositorio |
| Reglas propias de una capa | `.instructions.md` | configuración y código de la capa |

La evidencia ejecutable define la forma técnica actual. La memoria explica
significado, decisiones, límites y procedimientos. No copiar todo un schema o
OpenAPI al Markdown: enlazarlo y documentar lo que el contrato no puede enseñar.

## Cómo adaptar una plantilla

1. Leer la plantilla completa y entender por qué existe cada sección.
2. Buscar evidencia del repositorio para cada afirmación.
3. Eliminar secciones opcionales que no aplican; no inventar contenido para
   conservar la forma.
4. Reemplazar todos los tokens `{{...}}` con datos confirmados.
5. Mantener un pendiente solo cuando incluya una pregunta concreta y responsable
   de resolverla.
6. Enlazar schemas, tests, migraciones o configuración en vez de duplicarlos.
7. Añadir ejemplos mínimos que ayuden a usar el sistema y que puedan mantenerse.
8. Explicar casos límite o errores frecuentes cuando cambien la forma correcta
   de trabajar.
9. Ejecutar Markdownlint, revisar enlaces y comprobar coherencia con código.

### Ejemplo de adaptación correcta

En `docs/api.md`, no escribir “la API usa autenticación” porque el proyecto tiene
un middleware con nombre parecido. Identificar qué operación está protegida,
qué evidencia lo demuestra y cómo se representa en OpenAPI o tests.

Si existe HTTP, adaptar además la sección condicional de diseño orientado a
recursos en `docs/convenciones.md` y el inventario enriquecido de `docs/api.md`.
La primera conserva decisiones globales; el segundo registra su aplicación por
operación. El ciclo de vida y las razones de negocio quedan en el `context.md`,
la persistencia en `docs/modelo-datos.md` y las fronteras en arquitectura.

### Error frecuente

Copiar una tabla con filas de ejemplo y sustituir solo los nombres. El resultado
parece completo, pero puede inventar defaults, permisos o códigos que no existen.

## Instalación del validador

Requiere un shell POSIX y Python 3.10 o posterior. PyYAML es opcional: habilita
OpenAPI YAML; sin él debe aportarse OpenAPI JSON o aceptarse `NOT_EVALUATED`
para ese archivo.

1. Copiar `assets/standard/scripts/validate-project-memory` a
   `scripts/validate-project-memory`.
2. Preservar el permiso ejecutable.
3. Ejecutarlo directamente desde la raíz y revisar cobertura, no solo el exit
   code. Leer también `Confianza` y cada línea de `Evidencia`; muestran cómo se
   compuso una ruta o relación. No anteponer `python3`: el launcher inicia el
   intérprete aislado.
4. Añadir el comando a `docs/procedimientos.md` y al cierre de `AGENTS.md`.
5. Adaptar un detector únicamente con fixtures positivos, negativos y adversos.
6. Integrarlo en CI o pre-commit primero en modo informativo. Bloquear solo
   hallazgos de alta confianza cuando exista un baseline limpio.

El validador local no conoce automáticamente futuras versiones de la skill. La
skill activa puede pasar su versión normativa mediante la opción correspondiente
durante una auditoría de actualización.

Antes de ejecutar cualquier comando, leer
`docs/memoria-viva/resource-efficiency.md` y
las referencias locales enlazadas bajo `docs/memoria-viva/`; registrar su
propósito, alcance, nivel, perfil, presupuesto, salida esperada y condición de
escalamiento. Usar el modo normal para diagnóstico estructural.
`--strict` hace fallar también
advertencias y áreas no evaluadas, pero no reemplaza la revisión semántica.
Las opciones `--changed` y `--module` activan una ejecución parcial: limitan los
controles a los archivos o contextos declarados, informan los controles
ejecutados y omitidos, y siempre emiten `NOT_EVALUATED` para la cobertura global.
Una ejecución parcial nunca puede producir un resultado `OK` global; usar el
modo completo antes del commit o cuando el nivel/riesgo lo exija.
Durante Actualizar estándar, la skill activa debe ejecutar además
`--expected-standard-version` con la versión leída de su única fuente normativa;
no guardar otra copia manual en scripts o manifiestos.

En la versión 1.5.2, la salida JSON conserva `level`, `code` y `message`, añade
`evidence` y
`confidence` por hallazgo. Los consumidores pueden automatizar sobre esos
campos y sobre `scope.coverage`, `scope.checks_executed`,
`scope.checks_skipped` y `scope.global_checks_executed`, pero no deben
reinterpretar `UNRESOLVED` como confirmación ni depender del texto humano del
mensaje.

El launcher inicia Python aislado (`-I`), ignora `PYTHONPATH`, evita importar
módulos homónimos y no sigue symlinks durante el inventario. Aun así, ejecutar
repositorios no confiables dentro de un sandbox: parsear archivos adversariales
no convierte el validador en una frontera de seguridad.

## Publicación e inmutabilidad

Una versión puede iterarse mientras no se haya publicado ni adoptado. Desde que
un consumidor la copia o registra, sus bytes y comportamiento quedan congelados:

- una corrección compatible requiere incrementar `patch`;
- una capacidad compatible nueva requiere incrementar `minor`;
- una incompatibilidad de contrato requiere incrementar `major`;
- el commit de publicación identifica el artefacto exacto y no se reescribe.

La versión anterior quedó publicada en el commit `25b3a61`. Este identificador
sirve para comparar una copia del piloto; no debe duplicarse como configuración
del validador ni sustituye la versión adoptada en `docs/guia_IA.md`.

## Adaptadores estáticos de acceso

Cuando el acceso no esté expresado en OpenAPI, puede crearse opcionalmente
`.project-memory/access-adapters.json`. No se crea por defecto ni inventaría
endpoints: solo asigna significado a símbolos de dependencias que el AST ya
encontró en una aplicación, router, inclusión o handler.

```json
{
  "schema_version": 1,
  "rules": [
    {
      "id": "current-user",
      "symbol": "app.auth.current_user",
      "access": "authenticated",
      "evidence": "docs/seguridad.md#autenticacion"
    }
  ]
}
```

El schema vive en `assets/standard/schemas/access-adapters.schema.json`. Cada
regla necesita un identificador estable, el nombre importable resuelto
estáticamente, la clasificación documental y una evidencia local existente.
No admite rutas, métodos ni una afirmación manual de conformidad.

El validador nunca importa el símbolo ni ejecuta el adaptador. Si dos
dependencias aplicables producen accesos distintos, conserva ambas evidencias y
devuelve `NOT_EVALUATED`. Toda regla requiere fixtures positivo, negativo,
conflictivo y adversarial antes de usarse como gate.

## Migración segura de nombres

Si ya existe un contrato equivalente con otro nombre, preservar su contenido e
historial. Por ejemplo, para migrar `docs/contratos.md` a `docs/api.md`:

1. Confirmar que el archivo documenta realmente transporte HTTP y no mezcla
   CLI, persistencia o reglas de negocio.
2. Separar primero los conocimientos que pertenezcan a otras fuentes.
3. Usar `git mv` cuando el repositorio use Git.
4. Buscar todas las referencias al nombre anterior.
5. Actualizar enlaces, índices, prompts y procedimientos en el mismo cambio.
6. Ejecutar validación de enlaces y revisar el diff del rename.

No renombrar por uniformidad si el archivo existente tiene un alcance diferente.

## Calidad de la documentación

Una memoria útil debe ser:

- **correcta**: respaldada por evidencia actual;
- **suficiente**: permite comprender propósito, uso y límites;
- **didáctica**: explica por qué y cómo, no solo enumera nombres;
- **localizable**: cada conocimiento tiene una fuente clara;
- **mantenible**: evita duplicación y ejemplos enormes;
- **verificable**: enlaza contratos y declara cómo comprobarse;
- **honesta**: diferencia hecho, inferencia, pendiente y área no evaluada.

La brevedad es una ventaja solo cuando conserva esas propiedades.
