"""
browser_preview.py
===================
Gera uma página HTML simples de pré-visualização do QR Code e a abre
no navegador padrão do sistema operacional (via módulo `webbrowser`
da biblioteca padrão — funciona em Windows, macOS e Linux sem
dependências adicionais).
"""

from __future__ import annotations

import tempfile
import webbrowser
from pathlib import Path

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
    <style>
        body {{
            margin: 0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background-color: #111111;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #ffffff;
            text-align: center;
            padding: 24px;
            box-sizing: border-box;
        }}
        img {{
            max-width: min(90vw, 480px);
            max-height: 70vh;
            background: #ffffff;
            padding: 16px;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        }}
        h1 {{ font-size: 18px; font-weight: 600; margin-bottom: 24px; }}
        p {{ margin-top: 20px; color: #cccccc; font-size: 13px; word-break: break-all; max-width: 90vw; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <img src="{image_uri}" alt="QR Code gerado" />
    <p>Arquivo salvo em: {image_path}</p>
</body>
</html>
"""


def show_qr_in_browser(image_path: Path, title: str = "QR Code gerado com sucesso") -> Path:
    """
    Gera uma página HTML temporária exibindo o QR Code e a abre no
    navegador padrão do sistema.

    Args:
        image_path: Caminho do arquivo de imagem do QR Code (PNG ou SVG).
        title: Título exibido na página/aba do navegador.

    Returns:
        Caminho do arquivo HTML temporário gerado.
    """
    resolved_path = image_path.resolve()
    html = _HTML_TEMPLATE.format(
        title=title,
        image_uri=resolved_path.as_uri(),
        image_path=resolved_path,
    )

    temp_path = Path(tempfile.gettempdir()) / "qrcodegenerator_preview.html"
    temp_path.write_text(html, encoding="utf-8")
    webbrowser.open(temp_path.resolve().as_uri())
    return temp_path