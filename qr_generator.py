"""
qr_generator.py
================
Núcleo do projeto: classe responsável por gerar QR Codes de alta
qualidade (usando `segno`), com suporte a cores customizadas,
logotipo central (300x300 px) e exportação em PNG, SVG e PDF.

`segno` foi escolhido por ser leve, rápido, sem dependências nativas
e por seguir estritamente a especificação ISO/IEC 18004 do QR Code.
`Pillow` é usado para composição de imagens (logotipo) e exportação
em alta resolução (DPI).
"""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path
from typing import Dict

import segno
from PIL import Image, ImageDraw

from config import (
    DEFAULT_LOGO_RATIO,
    OutputFormat,
    QRStyleConfig,
)
from utils import (
    ensure_directory,
    hex_to_rgba,
    logger,
    resize_logo_with_transparency,
    validate_url,
)


class QRCodeGenerationError(Exception):
    """Erro genérico levantado durante a geração do QR Code."""


class QRCodeGenerator:
    """
    Responsável por gerar, personalizar e exportar um único QR Code
    a partir de uma configuração (`QRStyleConfig`).

    Uso típico:
        >>> cfg = QRStyleConfig(data="https://exemplo.com/redirect")
        >>> generator = QRCodeGenerator(cfg)
        >>> paths = generator.save(Path("output"), "meu_qrcode")
    """

    def __init__(self, style: QRStyleConfig) -> None:
        self.style = style
        self._qr: segno.QRCode | None = None
        self._validate_input()

    # ------------------------------------------------------------------ #
    # Validação
    # ------------------------------------------------------------------ #
    def _validate_input(self) -> None:
        """Valida os dados de entrada antes de gerar o QR Code."""
        if not self.style.data:
            raise QRCodeGenerationError("O conteúdo do QR Code não pode estar vazio.")
        if not validate_url(self.style.data):
            logger.warning(
                "O conteúdo informado não parece ser uma URL válida: %s",
                self.style.data,
            )
        if self.style.logo_path and not self.style.logo_path.exists():
            raise QRCodeGenerationError(
                f"Arquivo de logotipo não encontrado: {self.style.logo_path}"
            )

    # ------------------------------------------------------------------ #
    # Construção do QR Code (segno)
    # ------------------------------------------------------------------ #
    def _build_qr(self) -> segno.QRCode:
        """Cria o objeto QR Code (matriz) usando a biblioteca segno."""
        if self._qr is None:
            try:
                self._qr = segno.make(
                    self.style.data,
                    error=self.style.error_correction.lower(),
                    micro=False,
                )
            except Exception as exc:  # pragma: no cover - segurança extra
                raise QRCodeGenerationError(f"Falha ao gerar QR Code: {exc}") from exc
        return self._qr

    def _compute_scale(self) -> int:
        """Calcula o fator de escala (px por módulo) para atingir size_px."""
        qr = self._build_qr()
        modules = qr.symbol_size(scale=1, border=self.style.border)[0]
        scale = max(1, round(self.style.size_px / modules))
        return scale

    # ------------------------------------------------------------------ #
    # Renderização rasterizada (PNG base)
    # ------------------------------------------------------------------ #
    def _render_base_png(self) -> Image.Image:
        """Renderiza o QR Code (sem logo) como imagem PIL RGBA."""
        qr = self._build_qr()
        scale = self._compute_scale()
        buffer = io.BytesIO()

        dark = self.style.dark_color
        light = None if self.style.light_color.lower() == "transparent" else self.style.light_color

        qr.save(
            buffer,
            kind="png",
            scale=scale,
            border=self.style.border,
            dark=dark,
            light=light,
        )
        buffer.seek(0)
        image = Image.open(buffer).convert("RGBA")
        logger.info("QR Code base renderizado: %sx%s px", image.width, image.height)
        return image

    # ------------------------------------------------------------------ #
    # Composição do logotipo
    # ------------------------------------------------------------------ #
    def _build_logo_overlay(self, qr_size: int) -> Image.Image:
        """
        Prepara o logotipo (redimensionado, com fundo branco arredondado
        para garantir contraste e legibilidade) pronto para ser colado
        no centro do QR Code.
        """
        assert self.style.logo_path is not None  # garantido pelo chamador

        logo = resize_logo_with_transparency(self.style.logo_path)

        # O logo final ocupa no máx. DEFAULT_LOGO_RATIO da largura do QR
        target_dim = int(qr_size * DEFAULT_LOGO_RATIO)
        logo = logo.resize((target_dim, target_dim), Image.Resampling.LANCZOS)

        # Backdrop branco arredondado (padding) para manter contraste
        padding = int(target_dim * 0.12)
        backdrop_dim = target_dim + padding * 2
        backdrop = Image.new("RGBA", (backdrop_dim, backdrop_dim), (0, 0, 0, 0))
        draw = ImageDraw.Draw(backdrop)
        draw.rounded_rectangle(
            [(0, 0), (backdrop_dim - 1, backdrop_dim - 1)],
            radius=int(backdrop_dim * 0.18),
            fill=(255, 255, 255, 255),
        )
        backdrop.paste(logo, (padding, padding), mask=logo)
        return backdrop

    def _compose_with_logo(self, base_image: Image.Image) -> Image.Image:
        """Centraliza o logotipo (com backdrop) sobre o QR Code base."""
        overlay = self._build_logo_overlay(base_image.width)
        position = (
            (base_image.width - overlay.width) // 2,
            (base_image.height - overlay.height) // 2,
        )
        composed = base_image.copy()
        composed.paste(overlay, position, mask=overlay)
        logger.info("Logotipo centralizado no QR Code (%s%% da largura).", int(DEFAULT_LOGO_RATIO * 100))
        return composed

    # ------------------------------------------------------------------ #
    # API pública: geração da imagem final (usada também pela GUI)
    # ------------------------------------------------------------------ #
    def render(self) -> Image.Image:
        """
        Gera a imagem final do QR Code (com logotipo, se configurado),
        pronta para pré-visualização ou exportação.

        Returns:
            Imagem PIL (RGBA) do QR Code finalizado.
        """
        base_image = self._render_base_png()
        if self.style.logo_path:
            base_image = self._compose_with_logo(base_image)
        return base_image

    # ------------------------------------------------------------------ #
    # Exportação: PNG
    # ------------------------------------------------------------------ #
    def _save_png(self, image: Image.Image, destination: Path) -> Path:
        image.save(destination, format="PNG", dpi=(self.style.dpi, self.style.dpi))
        logger.info("PNG salvo em: %s (DPI=%s)", destination, self.style.dpi)
        return destination

    # ------------------------------------------------------------------ #
    # Exportação: PDF
    # ------------------------------------------------------------------ #
    def _save_pdf(self, image: Image.Image, destination: Path) -> Path:
        # PDFs não suportam transparência: aplica fundo branco se necessário
        rgb_image = Image.new("RGB", image.size, (255, 255, 255))
        rgb_image.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
        rgb_image.save(destination, format="PDF", resolution=self.style.dpi)
        logger.info("PDF salvo em: %s (DPI=%s)", destination, self.style.dpi)
        return destination

    # ------------------------------------------------------------------ #
    # Exportação: SVG (vetorial, com logotipo embutido em base64)
    # ------------------------------------------------------------------ #
    def _save_svg(self, destination: Path) -> Path:
        qr = self._build_qr()
        buffer = io.StringIO()
        light = None if self.style.light_color.lower() == "transparent" else self.style.light_color

        qr.save(
            buffer,
            kind="svg",
            scale=10,
            border=self.style.border,
            dark=self.style.dark_color,
            light=light,
        )
        svg_content = buffer.getvalue()

        if self.style.logo_path:
            svg_content = self._embed_logo_in_svg(svg_content, qr)

        destination.write_text(svg_content, encoding="utf-8")
        logger.info("SVG salvo em: %s", destination)
        return destination

    def _embed_logo_in_svg(self, svg_content: str, qr: segno.QRCode) -> str:
        """Insere o logotipo (como <image> base64) centralizado no SVG."""
        width, height = qr.symbol_size(scale=10, border=self.style.border)

        # Gera o overlay do logo (mesmo utilizado no PNG) em um tamanho
        # proporcional ao SVG e o converte para base64.
        overlay = self._build_logo_overlay(int(width))
        buffer = io.BytesIO()
        overlay.save(buffer, format="PNG")
        b64_logo = base64.b64encode(buffer.getvalue()).decode("ascii")

        x = (width - overlay.width) / 2
        y = (height - overlay.height) / 2
        image_tag = (
            f'<image x="{x:.2f}" y="{y:.2f}" '
            f'width="{overlay.width}" height="{overlay.height}" '
            f'href="data:image/png;base64,{b64_logo}" />'
        )

        # Insere o <image> imediatamente antes do fechamento de </svg>
        if "</svg>" in svg_content:
            svg_content = svg_content.replace("</svg>", f"{image_tag}</svg>")
        return svg_content

    # ------------------------------------------------------------------ #
    # API pública: salvar em todos os formatos solicitados
    # ------------------------------------------------------------------ #
    def save(self, output_dir: Path, filename_stem: str) -> Dict[OutputFormat, Path]:
        """
        Salva o QR Code nos formatos configurados em `style.output_formats`.

        Args:
            output_dir: Diretório de destino (será criado se não existir).
            filename_stem: Nome do arquivo, sem extensão.

        Returns:
            Dicionário {formato: caminho_do_arquivo_gerado}.
        """
        ensure_directory(output_dir)
        safe_stem = self._sanitize_filename(filename_stem)
        results: Dict[OutputFormat, Path] = {}

        try:
            rendered_image = self.render()

            if "PNG" in self.style.output_formats:
                path = output_dir / f"{safe_stem}.png"
                results["PNG"] = self._save_png(rendered_image, path)

            if "PDF" in self.style.output_formats:
                path = output_dir / f"{safe_stem}.pdf"
                results["PDF"] = self._save_pdf(rendered_image, path)

            if "SVG" in self.style.output_formats:
                path = output_dir / f"{safe_stem}.svg"
                results["SVG"] = self._save_svg(path)

        except QRCodeGenerationError:
            raise
        except Exception as exc:
            raise QRCodeGenerationError(f"Erro ao salvar QR Code: {exc}") from exc

        return results

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Remove caracteres inválidos de um nome de arquivo."""
        sanitized = re.sub(r"[^\w\-. ]", "_", name).strip() or "qrcode"
        return sanitized
