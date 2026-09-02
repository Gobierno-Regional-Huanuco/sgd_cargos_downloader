# Prompt: inicializar la memoria viva

Aplicar `AGENTS.md` y usar el modo Inicializar.

Además del protocolo general:

1. Inventariar instrucciones y memoria existentes sin asumir que un sistema diferente es
   inválido.
2. Identificar stack, capas, módulos, interfaces HTTP o CLI, persistencia, configuración,
   servicios, pruebas y procedimientos reales.
3. Explorar módulos representativos hasta distinguir patrones compartidos de excepciones
   locales; no imponer una cantidad fija si la evidencia ya es suficiente.
4. Presentar antes de escribir:
   - estado, evidencia y acción propuesta por artefacto;
   - capas y módulos detectados;
   - umbrales cumplidos y archivos condicionales aplicables;
   - contradicciones, dudas y límites de detección;
   - plan ordenado de creación, fusión o conservación.
5. Si el usuario autorizó solo el diagnóstico, esperar aprobación antes de
   implementar. Si autorizó claramente la inicialización completa, continuar
   tras el preflight siempre que el plan no amplíe el alcance ni revele una
   contradicción o decisión material pendiente.
6. Preservar contenido correcto, crear solo condicionales aplicables, instalar el validador y
   registrar la versión adoptada.
7. Cerrar sin placeholders de plantilla y con todos los contextos e instrucciones indexados.
