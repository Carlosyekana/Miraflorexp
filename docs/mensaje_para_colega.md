---
# 📣 Mensaje para enviar a un colega (copiar y pegar)

Ya puedes copiarlo tal cual y pegarlo en WhatsApp, Teams, correo o Slack.

---

**Hola 👋, te comparto algo que puede interesarte: un piloto de "catastro comercial" del sector Kennedy–Larco–La Mar, en Miraflores.**

Es un tablero interactivo (web) que cruza tres fuentes de datos del municipio y muestra, manzana por manzana y local por local, dónde hay actividad comercial real que **no tiene una licencia de funcionamiento compatible**:

👉 https://carlosyekana.github.io/Miraflorexp/

**Qué aporta en concreto:**
- 🎯 **Fiscalización**: prioriza manzanas y rubros por nº de locales sin licencia (dice dónde operar primero).
- 💰 **Tributación**: estima la **recaudación potencial** si esos locales se sanean (se puede mover la tarifa y recalcula al instante).
- 🏙️ **Desarrollo**: detecta saturación o vacíos comerciales según densidad y zonificación.
- 🗺️ Incluye catastro real: 172 manzanas, ~2.097 lotes y 6.752 numeraciones, con clic en cada lote/manzana.

**Un punto honesto importante:** está hecho **con la data disponible/abierta hoy**, que **no es del año en curso ni está sincronizada entre fuentes** (licencias 2020, catastro del GeoServer municipal y una aproximación a "actividad digital" tomada de OpenStreetMap). Por eso los números son un **orden de magnitud e indicadores**, no un censo oficial.

**Cómo puede mejorar a futuro:**
- Cruzar con **datos actuales de la municipalidad** (licencias vigentes, rentas/arbitrios), que es justo lo que ustedes ya tienen.
- Enriquecer con **Google Maps/Places** (rating, reseñas, cobertura), con una función serverless pequeña.
- Ampliar a **todo el distrito** (las capas catastrales completas ya existen).

¿Por qué te lo mando? Porque valdría muchísimo tener el **feedback de alguien de la municipalidad**: si esto sirve para priorizar operativos, qué campo le falta, y si tiene sentido hacerlo sobre datos oficiales actualizados. ¿Me ayudas a revisarlo? 🙏

---

## Nota para ti (no va en el mensaje)
- Si GitHub Pages aún no está activo, el link `https://carlosyekana.github.io/Miraflorexp/` dará 404 hasta activarlo en **Settings → Pages** (rama `main`, carpeta `/ root`).
- El archivo `dashboard_miraflores.html` se puede abrir directo en el navegador como plan B.
