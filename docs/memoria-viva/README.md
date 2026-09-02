# Referencias operativas de memoria viva

Estas referencias forman parte de la documentación local del consumidor. No
dependen de que la skill central esté disponible durante una tarea.

| Documento | Uso |
| --- | --- |
| [`workflow.md`](workflow.md) | Preflight, modos, umbrales y cierre |
| [`detection-strategies.md`](detection-strategies.md) | Evidencia, detectores, estados y límites |
| [`http-resource-design.md`](http-resource-design.md) | Clasificación y propiedad de interfaces HTTP |
| [`portable-standard.md`](portable-standard.md) | Artefactos, fuentes normativas, validador y migración |
| [`resource-efficiency.md`](resource-efficiency.md) | Economía de contexto y ejecución proporcional |
| [`succession-parity.md`](succession-parity.md) | Paridad al evolucionar la skill |

Las copias deben conservar paridad con las referencias de la skill. La prueba
de paridad se ejecuta al actualizar el estándar; un consumidor puede operar con
estas copias aunque la skill central no esté disponible.
