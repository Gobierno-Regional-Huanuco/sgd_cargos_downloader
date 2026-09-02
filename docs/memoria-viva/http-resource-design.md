# Diseño HTTP orientado a recursos

## Cuándo leer esta directiva

Leerla completa cuando el proyecto ya exponga HTTP o la tarea introduzca o
modifique un endpoint, router, prefijo, recurso, relación, proyección, consulta,
acción, operación CRUD, nombre público o módulo propietario. Si no existe una
interfaz HTTP ni se está diseñando una, la directiva es `N/A`: no obliga a crear
`docs/api.md`, adoptar REST ni reorganizar el proyecto.

La finalidad es conservar una interfaz pública comprensible y evolutiva. El
modelo de persistencia aporta evidencia, pero no dicta la API: una tabla no crea
automáticamente un recurso HTTP y una diferencia entre ORM, dominio y contrato
público puede ser correcta si se explica.

## Regla transversal

Toda operación HTTP se clasifica explícitamente como una de estas categorías:

1. recurso canónico;
2. subrecurso;
3. relación;
4. proyección;
5. consulta calculada;
6. acción personalizada.

Cada recurso o concepto publicado declara su módulo propietario y una ruta
canónica de mutación. Las rutas contextuales pueden consultar o delegar en el
propietario, pero no crean en silencio una segunda autoridad de escritura. Para
un recurso canónico y un subrecurso con ciclo de vida propio se evalúan List,
Create, Get, Update y Delete. Una operación omitida se registra como no
aplicable, no permitida o pendiente, con una justificación de dominio o
contrato. Relaciones, proyecciones, consultas y acciones exponen únicamente los
métodos pertinentes a su naturaleza.

## Árbol de decisión

Aplicar las preguntas en orden y guardar la decisión en `docs/api.md`:

1. ¿Tiene identidad y ciclo de vida propios para el consumidor? Tratarlo como
   recurso canónico, aunque no corresponda uno a uno con una entidad almacenada.
2. ¿Tiene identidad o ciclo de vida propios, pero solo dentro de un padre real?
   Tratarlo como subrecurso y justificar el vínculo de pertenencia.
3. ¿Representa el vínculo entre dos conceptos?
   - Si el vínculo tiene rol, estado, fechas, permisos o ciclo de vida, modelarlo
     como recurso de relación.
   - Si solo conecta o desconecta dos recursos, puede representarse mediante
     operaciones sobre la relación, sin inventar una entidad pública.
4. ¿Es una vista contextual de datos ya gobernados por otro recurso? Es una
   proyección; normalmente es de lectura y remite a la mutación canónica.
5. ¿El resultado se calcula para la solicitud y no posee identidad estable? Es
   una consulta calculada.
6. ¿La intención no cabe limpiamente en CRUD, una relación o un nuevo recurso?
   Es una acción personalizada y requiere justificación.

Si la evidencia no permite responder, clasificar el punto como
`NOT_EVALUATED`. Un sustantivo en la URL, una clase ORM o la carpeta del router
no resuelven por sí solos esta decisión.

## Recursos canónicos y CRUD

Un recurso canónico es el punto público estable que posee identidad y ciclo de
vida. Ejemplos mínimos, no prescriptivos:

```text
GET    /users
POST   /users
GET    /users/{id}
PATCH  /users/{id}
DELETE /users/{id}
```

Evaluar las cinco capacidades, no imponerlas. Por ejemplo, Delete puede ser
`no permitida: la conservación es una obligación legal`, List puede ser
`no aplica: el recurso es singleton` y Create puede estar `pendiente` durante
una migración. La razón vive en el contexto funcional y se referencia desde la
matriz de `docs/api.md`.

## Subrecursos y anidamiento

Un subrecurso pertenece al ámbito de un padre y puede poseer ciclo de vida
propio dentro de él:

```text
/tenants/{tenant}/memberships
/tenants/{tenant}/memberships/{membership}
```

Preferir como máximo la secuencia padre → hijo. Una profundidad mayor requiere
explicar qué identidad o autorización aporta cada nivel. El primer segmento de
la URL no determina el propietario del código: normalmente el módulo que conoce
el ciclo de vida del hijo o de la relación es quien gobierna la operación.

No deducir jerarquía de dominio contando segmentos. Prefijos de despliegue,
versiones, scopes de autorización o compatibilidad pueden producir rutas largas
sin representar padres conceptuales.

## Relaciones: vínculo simple o recurso propio

Una relación simple puede exponer lectura y conexión o desconexión mediante una
convención consistente del proyecto. Por ejemplo, un par de recursos sin datos
propios podría admitir GET, PUT y DELETE sobre la relación. Documentar qué
recurso se modifica y quién autoriza la operación.

Cuando el vínculo tiene información propia —como `Membership` con rol, estado,
fechas y transiciones— tratarlo como recurso de relación:

```text
POST  /tenants/{tenant}/memberships
PATCH /memberships/{membership}
```

La primera ruta puede crear en contexto y la segunda ser la mutación canónica.
Ambas deben declarar el mismo concepto propietario y no implementar reglas de
escritura divergentes.

## Proyecciones

Una proyección reorganiza o filtra información de recursos existentes para un
contexto de lectura:

```text
GET /tenants/{tenant}/members
```

`members` puede ser una vista de usuarios y membresías, no un recurso `Member`.
Declarar los recursos que representa y sus rutas canónicas. Si una proyección
acepta una mutación, explicar por qué no constituye una segunda autoridad de
escritura y cómo delega o mantiene compatibilidad.

## Consultas calculadas

Una consulta calculada devuelve un resultado derivado sin identidad ni ciclo de
vida propios. Documentar entradas, estabilidad, coste, autorización, efectos y
posible caché. No crear CRUD ficticio para un informe o cálculo. Si el resultado
se conserva, se consulta posteriormente o transita estados, reevaluar si se ha
convertido en un recurso.

## Acciones personalizadas

Usarlas solo cuando la intención no se modele limpiamente mediante métodos
estándar, una relación, un cambio de estado ordinario o un nuevo recurso. Antes
de aprobar una acción, responder:

1. ¿Es realmente una actualización parcial del recurso?
2. ¿Crea un recurso con identidad o estado observable?
3. ¿Es una transición de dominio que merece un verbo explícito?
4. ¿Qué método HTTP conserva seguridad e idempotencia esperadas?

Ejemplo orientativo:

```text
POST /memberships/{membership}:suspend
```

La sintaxis con dos puntos no es una obligación universal. Adoptar una
convención coherente con el proyecto, documentar el recurso o concepto
propietario y justificar por qué CRUD no expresa bien la operación.

## Propiedad y autoridad de mutación

Por cada recurso o concepto público registrar:

- propietario conceptual;
- módulo propietario en el código;
- ruta o familia canónica;
- rutas contextuales;
- operaciones admitidas;
- operaciones omitidas y su razón;
- fuente de negocio o contrato que respalda la decisión.

Debe existir una sola autoridad canónica de mutación. Dos rutas pueden ofrecer
compatibilidad temporal o diferentes contextos, pero la documentación debe
nombrar cuál es canónica, cómo delega la otra y cuándo se retirará. No inferir
propiedad por nombres de carpetas, routers o prefijos.

## Compatibilidad y retirada

Antes de renombrar una ruta, mover su propiedad, retirar CRUD o sustituir una
acción:

1. inventariar consumidores y contrato vigente con evidencia local;
2. declarar la ruta sucesora y la autoridad canónica;
3. definir convivencia, redirección o adaptación si aplica;
4. registrar señales y fecha de deprecación verificables;
5. cubrir ambos caminos mientras la compatibilidad siga activa;
6. retirar documentación y código juntos cuando termine la ventana aprobada.

No presentar una migración planificada como completada.

## Distribución de conocimiento

- `docs/convenciones.md`: decisiones transversales adoptadas sobre nombres,
  clasificación, anidamiento, métodos, acciones, compatibilidad y propiedad.
- `docs/api.md`: clasificación y aplicación real por operación, incluida la
  ruta canónica, efectos, CRUD omitido, compatibilidad y pruebas.
- `context.md` del módulo: identidad de dominio, ciclo de vida, permisos,
  estados y razones de negocio.
- `docs/modelo-datos.md`: persistencia y relaciones almacenadas; nunca se usa
  como catálogo automático de recursos HTTP.
- `docs/arquitectura.md`: límites entre módulos o componentes propietarios.

Enlazar entre fuentes; no repetir schemas, campos ni reglas completas.

## Qué automatizar y qué revisar manualmente

El validador puede comprobar con confianza alta:

- existencia de `docs/api.md` cuando detecta HTTP soportado;
- presencia de columnas y clasificación declarada al adoptar este estándar;
- tipo, propietario conceptual, módulo propietario y ruta canónica no vacíos;
- justificación escrita de omisiones CRUD;
- referencia canónica en rutas declaradas como contextuales;
- conflictos explícitos entre dos autoridades canónicas de mutación;
- placeholders residuales.

Requieren revisión humana y, si no hay evidencia, quedan `NOT_EVALUATED`:

- si la clasificación elegida representa correctamente el dominio;
- si una entidad ORM debe o no ser recurso público;
- si el sustantivo de una ruta identifica realmente un concepto;
- si el anidamiento expresa una jerarquía legítima;
- si CRUD aplica y si la justificación de una omisión es suficiente;
- si dos mutaciones implementan efectos equivalentes;
- si el módulo declarado es el propietario correcto.

No crear un detector semántico basado en expresiones regulares para estas
decisiones.

## Errores comunes

- publicar cada tabla como recurso y acoplar el contrato a la base de datos;
- llamar recurso a todo sustantivo o subrecurso a toda ruta anidada;
- duplicar escrituras mediante una proyección contextual;
- ocultar una relación con ciclo de vida dentro de un verbo ambiguo;
- crear acciones para evitar evaluar Update o un nuevo recurso;
- exigir CRUD completo aunque una operación no aplique al dominio;
- asignar propiedad al primer segmento de la ruta;
- aceptar dos autoridades canónicas sin compatibilidad explícita;
- convertir los ejemplos de esta directiva en sintaxis obligatoria.

## Fuentes conceptuales

Esta directiva adapta ideas, no impone literalmente las convenciones de ninguna
fuente externa:

- [AIP-121: Resource-oriented design](https://google.aip.dev/121),
  [AIP-122: Resource names](https://google.aip.dev/122),
  [AIP-130: Methods](https://google.aip.dev/130) y
  [AIP-136: Custom methods](https://google.aip.dev/136);
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html);
- [JSON:API 1.1](https://jsonapi.org/format/), como ejemplo de separación entre
  recursos relacionados y operaciones sobre relaciones;
- [Zalando RESTful API Guidelines](https://opensource.zalando.com/restful-api-guidelines/);
- [GitHub REST API: organization members](https://docs.github.com/en/rest/orgs/members),
  como ejemplo real de membresías y relaciones contextuales.
