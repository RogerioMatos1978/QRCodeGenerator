"""
landing_page_builder.py
========================
Gera a página estática (HTML + JS) responsável por detectar o sistema
operacional do dispositivo e redirecionar automaticamente para a URL
correta (Android, iOS ou uma URL de fallback).

Esta página é o "destino" real codificado no QR Code: como um QR Code
só pode armazenar um único conteúdo, a URL desta página (após publicada
em um host estático, ex.: GitHub Pages, Netlify, Vercel ou servidor
próprio) é o que deve ser passado para `QRStyleConfig.data`.
"""

from __future__ import annotations

from pathlib import Path

from config import RedirectURLs
from utils import ensure_directory, logger

# Template HTML com detecção de SO via JavaScript (navigator.userAgent).
# Mantido em uma única página estática para funcionar em qualquer host
# gratuito, sem necessidade de backend/servidor dinâmico.
_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Redirecionando...</title>
    <style>
        body {{
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #111111;
            color: #ffffff;
            text-align: center;
        }}
        .spinner {{
            width: 42px;
            height: 42px;
            border: 4px solid #333333;
            border-top-color: #ffffff;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 16px auto;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        a {{ color: #4da3ff; }}
    </style>
</head>
<body>
    <div>
        <div class="spinner"></div>
        <p>Redirecionando você para o aplicativo...</p>
        <p><a id="manual-link" href="{fallback_url}">Clique aqui se não for redirecionado automaticamente</a></p>
    </div>

    <script>
        (function () {{
            var ANDROID_URL = "{android_url}";
            var IOS_URL = "{ios_url}";
            var FALLBACK_URL = "{fallback_url}";

            function detectAndRedirect() {{
                var userAgent = navigator.userAgent || navigator.vendor || window.opera;
                var destination = FALLBACK_URL;

                if (/android/i.test(userAgent)) {{
                    destination = ANDROID_URL;
                }} else if (/iPad|iPhone|iPod/.test(userAgent) && !window.MSStream) {{
                    destination = IOS_URL;
                }}

                document.getElementById("manual-link").href = destination;
                window.location.replace(destination);
            }}

            detectAndRedirect();
        }})();
    </script>
</body>
</html>
"""


def build_landing_page(urls: RedirectURLs, output_dir: Path) -> Path:
    """
    Gera o arquivo `index.html` de redirecionamento automático por SO.

    Args:
        urls: Par de URLs (Android/iOS) e fallback opcional.
        output_dir: Diretório onde o `index.html` será salvo.

    Returns:
        Caminho do arquivo `index.html` gerado.
    """
    ensure_directory(output_dir)
    html_content = _HTML_TEMPLATE.format(
        android_url=urls.android_url,
        ios_url=urls.ios_url,
        fallback_url=urls.fallback_url,
    )
    destination = output_dir / "index.html"
    destination.write_text(html_content, encoding="utf-8")
    logger.info("Landing page gerada em: %s", destination)
    return destination
