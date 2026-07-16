"""
main.py
=======
Ponto de entrada do projeto QRCodeGenerator.

Uso:
    python main.py                     -> abre a interface gráfica (GUI)
    python main.py --cli ...           -> executa em modo linha de comando

Execute este arquivo diretamente no PyCharm (botão "Run" com main.py
selecionado como script principal) ou via terminal.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config import LANDING_PAGE_DIR, OUTPUT_DIR, QRStyleConfig, RedirectURLs
from landing_page_builder import build_landing_page
from qr_generator import QRCodeGenerationError, QRCodeGenerator
from utils import logger, validate_url


def build_arg_parser() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos para o modo CLI."""
    parser = argparse.ArgumentParser(
        prog="QRCodeGenerator",
        description=(
            "Gera um único QR Code que redireciona para URLs diferentes "
            "de acordo com o sistema operacional (Android/iOS)."
        ),
    )
    parser.add_argument(
        "--cli", action="store_true", help="Executa em modo linha de comando (sem GUI)."
    )
    parser.add_argument("--android-url", type=str, help="URL da loja Android (Google Play).")
    parser.add_argument("--ios-url", type=str, help="URL da loja iOS (App Store).")
    parser.add_argument(
        "--landing-url",
        type=str,
        help="URL pública já publicada da landing page (o que será codificado no QR Code).",
    )
    parser.add_argument(
        "--build-landing-page",
        action="store_true",
        help="Gera apenas o arquivo landing_page/index.html a partir de --android-url/--ios-url.",
    )
    parser.add_argument("--logo", type=Path, default=None, help="Caminho para o logotipo (opcional).")
    parser.add_argument("--size", type=int, default=1000, help="Tamanho do QR Code em pixels.")
    parser.add_argument("--border", type=int, default=4, help="Margem (quiet zone) em módulos.")
    parser.add_argument(
        "--error-correction",
        type=str,
        choices=["L", "M", "Q", "H"],
        default="M",
        help="Nível de correção de erro.",
    )
    parser.add_argument("--dark-color", type=str, default="#000000", help="Cor dos módulos do QR Code.")
    parser.add_argument("--light-color", type=str, default="#FFFFFF", help="Cor de fundo.")
    parser.add_argument(
        "--caption-text",
        type=str,
        default=None,
        help="Texto exibido abaixo do QR Code (ex.: 'Aponte a Câmera').",
    )
    parser.add_argument(
        "--caption-color", type=str, default="#164194", help="Cor do texto da legenda (hex)."
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=["PNG", "SVG", "PDF"],
        default=["PNG"],
        help="Formatos de exportação desejados.",
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Diretório de saída.")
    parser.add_argument("--filename", type=str, default="qrcode", help="Nome do arquivo (sem extensão).")
    return parser


def run_cli(args: argparse.Namespace) -> int:
    """Executa a geração do QR Code (e/ou landing page) via linha de comando."""
    try:
        if args.build_landing_page:
            if not args.android_url or not args.ios_url:
                logger.error("--android-url e --ios-url são obrigatórios para --build-landing-page.")
                return 1
            urls = RedirectURLs(android_url=args.android_url, ios_url=args.ios_url)
            path = build_landing_page(urls, LANDING_PAGE_DIR)
            print(f"Landing page gerada em: {path}")
            return 0

        if not args.landing_url:
            logger.error(
                "--landing-url é obrigatório para gerar o QR Code "
                "(é a URL publicada da landing page a ser codificada)."
            )
            return 1

        if not validate_url(args.landing_url):
            logger.error("--landing-url inválida: %s", args.landing_url)
            return 1

        style = QRStyleConfig(
            data=args.landing_url,
            size_px=args.size,
            border=args.border,
            error_correction=args.error_correction,
            dark_color=args.dark_color,
            light_color=args.light_color,
            logo_path=args.logo,
            output_formats=tuple(args.formats),
            caption_text=args.caption_text,
            caption_color=args.caption_color,
        )
        generator = QRCodeGenerator(style)
        results = generator.save(args.output_dir, args.filename)

        for fmt, path in results.items():
            print(f"[{fmt}] Arquivo gerado: {path}")
        return 0

    except QRCodeGenerationError as exc:
        logger.error("Erro ao gerar QR Code: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erro inesperado: %s", exc)
        return 1


def main() -> int:
    """Função principal: decide entre modo GUI e modo CLI."""
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.cli or args.build_landing_page or args.landing_url:
        return run_cli(args)

    # Modo padrão: interface gráfica
    from gui import launch_app  # importado aqui para não exigir customtkinter em modo CLI puro

    launch_app()
    return 0


if __name__ == "__main__":
    sys.exit(main())