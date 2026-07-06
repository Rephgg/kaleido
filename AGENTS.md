# Contexto del proyecto

Bot de Discord para sistema de puntos.

## Archivos principales
- bot.py - código principal con slash commands (/)
- .env - token de Discord (NO SUBIR)
- puntos.json - datos de usuarios y puntos (NO SUBIR)
- terms.html - términos de servicio (GitHub Pages)
- privacy.html - política de privacidad (GitHub Pages)

## Slash commands globales (funcionan en cualquier servidor)
- /addpoints @user <cantidad> - suma puntos (solo admin)
- /setpoints @user <cantidad> - asigna puntos exactos (solo admin)
- /delpoints @user - elimina usuario de lista (solo admin)
- /ranking - muestra todos los usuarios ordenados
- /puntos [@user] - consulta puntos
- /setcanal #canal - configura canal para respuestas de ranking/puntos (solo admin)
- /delcanal - elimina canal configurado (solo admin)
- /updateranking - actualiza el mensaje del ranking existente con datos recientes + timestamp (solo admin)
- /say <texto> - el bot repite el texto (solo admin)
- /help - muestra todos los comandos disponibles

## Hosting
- Código en GitHub: https://github.com/Rephgg/kaleido
- GitHub Pages activado para terms y privacy
- Pendiente: deploy en Render

## Pendiente
- Hacer deploy en Render para que el bot esté 24/7
