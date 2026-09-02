# Antecedente Del Backend SGD

El backend SGD se implementa en otro repositorio y no es modificado por este
proyecto. La aplicacion consume sus rutas bajo `/api/cargos` mediante un token
Bearer temporal.

El contrato externo que la aplicacion realmente consume esta documentado en
[api.md](api.md). Antes de cambiar rutas, payloads, permisos o paginacion, se
debe contrastar ese documento con el backend SGD y actualizar ambos repositorios
mediante un alcance autorizado.
