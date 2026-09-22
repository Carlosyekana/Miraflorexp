# Cómo publicar el dashboard con GitHub Pages

El repo ya está listo. Solo falta **activar GitHub Pages** (es un clic en la web
de GitHub; no hay API/CLI para hacerlo por ti).

## Pasos (1 minuto)

1. Entra a → `https://github.com/Carlosyekana/Miraflorexp/settings/pages`
2. En **"Build and deployment"** → sección **"Source"** elige:
   - **Deploy from a branch**
3. En **"Branch"** selecciona:
   - rama: **`main`**
   - carpeta: **`/ (root)`**
4. Pulsa **Save**.

En ~1 minuto el sitio estará vivo en:

🔗 **https://carlosyekana.github.io/Miraflorexp/**

## Opcional · desplegar con GitHub Actions (automático)

Si prefieres un workflow explícito, crea el archivo
`.github/workflows/pages.yml` en `main` con:

```yaml
name: Deploy a GitHub Pages
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
      - id: deployment
        uses: actions/deploy-pages@v4
```

(y en Settings → Pages elige "Source: **GitHub Actions**")

## Notas
- El dashboard es un único HTML autocontenido: no requiere build ni internet.
- `index.html` es una copia exacta de `dashboard_miraflores.html`, generada por
  el mismo `build_dashboard.py`, para que Pages lo sirva en la raíz.
