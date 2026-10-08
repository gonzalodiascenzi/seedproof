# evidencia agregada

## tasas base
- empresas de ee. uu. (todas, no solo software): ~79–80 % sobreviven 1 año y ~50 % a los 5 (bls: https://www.bls.gov/bdm/us_age_naics_00_table7.txt). cohorte 2019: 51,6 % (https://www.axios.com/2025/11/04/new-business-survival-rates-map).
- cierres de startups con capital de riesgo en ee. uu.: 966 en 2024 vs 769 en 2023, probablemente subestimado (https://techcrunch.com/2025/01/26/2025-will-likely-be-another-brutal-year-of-failed-startups-data-suggests).
- fundadores solos: pasaron de 23,7 % de las nuevas startups en 2019 a 36,3 % en el 1.er semestre de 2025 (https://carta.com/data/solo-founders-report). no se encontraron datos de resultados.
- microempresas verificadas con stripe (5.079 proyectos de trustmrr): mrr mediano $169; ~10 % supera $10k; 0,9 % supera $10k creciendo más de 50 % mensual; los proyectos de ia son 24,5 % de la muestra, con mediana de $156 (https://www.indiehackers.com/post/i-analyzed-5-079-stripe-verified-startups-f0f6bd053f). muestra voluntaria, así que la mediana real probablemente es menor; el autor promociona un producto.
- las 100 mejores startups de ia llegaron a $5 m anualizados en 24 meses frente a 37 meses para las mejores 100 de saas de 2018 (https://techcrunch.com/2025/02/27/stripe-ceo-says-ai-startups-are-growing-faster-than-saas-ever-did-and-calling-them-wrappers-misses-the-point). solo los mejores, sin datos de retención.
- **vacío:** no hay una tasa de supervivencia creíble específica de microempresas construidas con ia.

## churn
- apps móviles por suscripción: las de ia retienen 21,1 % anual vs 30,7 % las demás, y 6,1 % mensual vs 9,5 % (revenuecat, vía https://techcrunch.com/2026/03/10/ai-powered-apps-struggle-with-long-term-retention-new-report-shows). monetizan mejor: $30,16 vs $21,37 por usuario pagante al año. leído a través de prensa, no del informe.
- wrappers: sin datos públicos; el único dato tipo churn es el de 11x.

## seguridad del código generado
- veracode 2025: ~45 % de las muestras (más de 100 modelos, 80 tareas) con fallas; xss falló 86 % y log injection 88 % (https://www.veracode.com/press-release/ai-generated-code-poses-major-security-risks-in-nearly-half-of-all-development-tasks-veracode-research-reveals/).
- veracode 2026: tasa de aprobación 56 %, prácticamente estancada (https://www.veracode.com/news/llms-are-getting-smarter-but-not-safer-veracode-2026-genai-code-security-report-finds-ai-generated-code-security-has-stalled-at-56%25-pass-rate/).
- estudio revisado por pares: quienes usaron asistente de ia escribieron código menos seguro y con más confianza, con solo 47 participantes analizados (https://arxiv.org/abs/2211.03622).
- escape.tech reporta 2.038 vulnerabilidades críticas y más de 400 secretos expuestos en apps "vibe coded"; su propia página da 1,4 mil y 5,6 mil apps escaneadas: conflicto (https://escape.tech/state-of-security-of-vibe-coded-apps).
- el dato de 91,5 % de apps con fallas proviene de una fuente comercial con muestreo no revelado: no usarlo como base.
- el agente de replit borró una base en vivo de 1.206 ejecutivos durante una prueba; se agregó separación dev/prod después (https://www.eweek.com/news/replit-ai-coding-assistant-failure/).
- productividad (no seguridad): ensayo de metr con 16 desarrolladores experimentados, 246 tareas, tardaron 19 % más con ia creyendo ir más rápido; herramientas de principios de 2025 y muestra chica (https://getdx.com/blog/metr-study-on-how-ai-affects-developer-productivity/).

## dependencia de plataformas
- cursor pasó su plan pro a facturación por uso el 16 jun 2025 y luego se disculpó y ofreció reembolsos (https://techcrunch.com/2025/07/07/cursor-apologizes-for-unclear-pricing-changes-that-upset-users/).
- márgenes de herramientas de código descriptos por fuentes internas como neutros a muy negativos (https://techcrunch.com/2025/08/07/the-high-costs-and-thin-margins-threatening-ai-coding-startups/); el dato duro es el margen casi nulo de base44.
- anthropic cortó el acceso de windsurf a claude con menos de 5 días de aviso en junio de 2025 (fuente secundaria: https://svgn.substack.com/p/anthropic-abruptly-terminates-windsurfs); en enero de 2026 bloqueó herramientas de terceros que usaban suscripciones de consumo (https://venturebeat.com/ai/anthropic-cracks-down-on-unauthorized-claude-usage-by-third-party-harnesses/).
- apple habría bloqueado actualizaciones de replit y vibecode bajo la guía 2.5.2; apple dice que no apunta al vibe coding; reporte sin fecha (https://the-decoder.com/apple-reportedly-blocks-vibe-coding-apps-from-publishing-updates/).

## patrones
1. fundadores con incentivos de financiamiento o audiencia exageraron ingresos (cluely, 11x, polsia en disputa); solo los dashboards y las presentaciones del adquirente resistieron.
2. las fallas de seguridad golpean más a quienes no programan (enrichlead, moltbook, apps de lovable).
3. el costo de inferencia es el riesgo estructural: margen de base44 y repricing de cursor.

## implicancia para los playbooks
refuerza la elección de servicios con criterio humano (playbook 01 y 03 en particular): el mercado muestra demanda de seguridad para software hecho con ia, y la propia evidencia de fallas es un argumento de venta que se puede documentar con casos públicos.
