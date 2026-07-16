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
from PIL import Image, ImageDraw, ImageFont

from config import (
    DEFAULT_LOGO_RATIO,
    LOGO_BACKDROP_PADDING_RATIO,
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
        if self.style.gradient_end_color:
            return self._render_gradient_png()

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

    def _gradient_progress(self, row: int, col: int, modules: int) -> float:
        """Calcula o progresso (0.0 a 1.0) de um módulo ao longo do degradê."""
        denom = max(modules - 1, 1)
        if self.style.gradient_direction == "horizontal":
            return col / denom
        if self.style.gradient_direction == "vertical":
            return row / denom
        return (row + col) / (2 * denom)  # diagonal (padrão)

    @staticmethod
    def _lerp_color(start: tuple, end: tuple, t: float) -> tuple:
        """Interpola linearmente entre duas cores RGB, em um ponto 0.0-1.0."""
        return tuple(int(start[i] + (end[i] - start[i]) * t) for i in range(3))

    def _render_gradient_png(self) -> Image.Image:
        """
        Renderiza o QR Code módulo a módulo (em vez de usar o renderizador
        padrão do segno), aplicando um degradê de cor entre `dark_color`
        e `gradient_end_color` de acordo com a posição de cada módulo.

        Necessário porque o segno não tem suporte nativo a gradientes —
        cada módulo escuro recebe sua própria cor interpolada.
        """
        qr = self._build_qr()
        scale = self._compute_scale()
        matrix = qr.matrix
        modules = len(matrix)
        border = self.style.border
        module_px = scale
        total_px = (modules + 2 * border) * module_px

        light_rgba = (
            (255, 255, 255, 0)
            if self.style.light_color.lower() == "transparent"
            else hex_to_rgba(self.style.light_color)
        )

        image = Image.new("RGBA", (total_px, total_px), light_rgba)
        draw = ImageDraw.Draw(image)

        start_rgb = hex_to_rgba(self.style.dark_color)[:3]
        end_rgb = hex_to_rgba(self.style.gradient_end_color)[:3]

        for row_idx, row in enumerate(matrix):
            for col_idx, value in enumerate(row):
                if not value:
                    continue
                t = self._gradient_progress(row_idx, col_idx, modules)
                color = self._lerp_color(start_rgb, end_rgb, t) + (255,)
                x0 = (border + col_idx) * module_px
                y0 = (border + row_idx) * module_px
                draw.rectangle([x0, y0, x0 + module_px - 1, y0 + module_px - 1], fill=color)

        logger.info(
            "QR Code renderizado com degradê (%s -> %s, %s).",
            self.style.dark_color,
            self.style.gradient_end_color,
            self.style.gradient_direction,
        )
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

        # Backdrop branco (com cantos levemente arredondados) atrás do logo.
        # padding=0 por padrão: o logo ocupa o backdrop inteiro, sem margem.
        padding = int(target_dim * LOGO_BACKDROP_PADDING_RATIO)
        backdrop_dim = target_dim + padding * 2
        backdrop = Image.new("RGBA", (backdrop_dim, backdrop_dim), (0, 0, 0, 0))
        draw = ImageDraw.Draw(backdrop)
        draw.rounded_rectangle(
            [(0, 0), (backdrop_dim - 1, backdrop_dim - 1)],
            radius=max(int(backdrop_dim * 0.12), 2),
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
    # Personalização dos marcadores de posição ("olhos")
    # ------------------------------------------------------------------ #
    def _apply_custom_eyes(self, image: Image.Image) -> Image.Image:
        """
        Substitui o quadrado central (3x3 módulos) de cada um dos 3
        marcadores de posição do QR Code por um caractere (ex.: "S").

        Os anéis externos do marcador (7x7 módulos) permanecem
        INTOCADOS — é neles que a maioria dos leitores de QR Code se
        baseia para localizar e alinhar o código. Ainda assim, esta é
        uma personalização estrutural que foge do padrão e não é
        protegida por correção de erro: teste a leitura em múltiplos
        aparelhos antes de usar em impressões de grande escala.

        Args:
            image: Imagem do QR Code já renderizada (sem logo/legenda).

        Returns:
            Imagem com os 3 marcadores de posição personalizados.
        """
        if not self.style.eye_mark:
            return image

        qr = self._build_qr()
        modules = qr.symbol_size(scale=1, border=0)[0]  # módulos, sem quiet zone
        scale = self._compute_scale()
        border_px = self.style.border * scale
        module_px = scale
        inner_size = 3 * module_px  # quadrado central do marcador (3x3 módulos)

        eye_top_left_modules = [
            (0, 0),                    # marcador superior-esquerdo
            (modules - 7, 0),          # marcador superior-direito
            (0, modules - 7),          # marcador inferior-esquerdo
        ]

        draw = ImageDraw.Draw(image)
        font = self._load_font(max(int(inner_size * 0.8), 8))
        light_rgba = (
            (255, 255, 255, 255)
            if self.style.light_color.lower() == "transparent"
            else hex_to_rgba(self.style.light_color)
        )
        dark_rgba = hex_to_rgba(self.style.dark_color)

        for mx, my in eye_top_left_modules:
            cx = border_px + (mx + 3.5) * module_px
            cy = border_px + (my + 3.5) * module_px
            half = inner_size / 2

            draw.rectangle([cx - half, cy - half, cx + half, cy + half], fill=light_rgba)

            bbox = draw.textbbox((0, 0), self.style.eye_mark, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            draw.text(
                (cx - text_w / 2 - bbox[0], cy - text_h / 2 - bbox[1]),
                self.style.eye_mark,
                font=font,
                fill=dark_rgba,
            )

        logger.info(
            "Marca '%s' aplicada nos 3 marcadores de posição do QR Code "
            "(anéis externos preservados).",
            self.style.eye_mark,
        )
        return image

    # ------------------------------------------------------------------ #
    # Composição da legenda (ex.: "Aponte a Câmera")
    # ------------------------------------------------------------------ #
    # Fontes candidatas, em ordem de preferência. A fonte embutida do
    # Pillow (load_default) NÃO cobre bem caracteres acentuados
    # (ex.: "Câmera" aparece com uma caixa no lugar do "â"), então
    # preferimos uma fonte de sistema de verdade sempre que disponível.
    _FONT_CANDIDATES: tuple = (
        "arial.ttf",                                            # Windows (busca padrão do FreeType)
        "Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",                            # Windows (caminho absoluto)
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",          # macOS
        "/System/Library/Fonts/Helvetica.ttc",
    )

    @classmethod
    def _load_font(cls, size: int) -> ImageFont.ImageFont:
        """
        Carrega uma fonte em negrito com bom suporte a acentuação
        (português do Brasil: ã, â, ç, é, í, ó, ú etc.).

        Tenta, em ordem, fontes reais do sistema operacional (Arial,
        Segoe UI, DejaVu Sans, Liberation Sans, Helvetica). Só recorre
        à fonte padrão embutida do Pillow se nenhuma delas for
        encontrada — nesse caso, caracteres acentuados podem não
        aparecer corretamente.
        """
        for candidate in cls._FONT_CANDIDATES:
            try:
                return ImageFont.truetype(candidate, size)
            except (OSError, IOError):
                continue

        logger.warning(
            "Nenhuma fonte de sistema com suporte a acentos foi encontrada; "
            "usando fonte padrão do Pillow (acentos podem não aparecer corretamente)."
        )
        try:
            return ImageFont.load_default(size=size)
        except TypeError:  # Pillow < 10.1 não aceita o parâmetro "size"
            return ImageFont.load_default()

    def _add_caption(self, image: Image.Image) -> Image.Image:
        """
        Adiciona uma faixa colorida com texto centralizado ao QR Code
        (ex.: "Aponte a Câmera"), no topo ou embaixo conforme
        `caption_position` — útil para materiais impressos.

        Args:
            image: Imagem do QR Code já renderizada (com logo, se houver).

        Returns:
            Nova imagem, mais alta, com a faixa de legenda.
        """
        if not self.style.caption_text:
            return image

        band_height = max(int(image.height * 0.16), 60)
        band_color_hex = self.style.caption_background_color or self.style.dark_color
        band_background = (
            (255, 255, 255, 255)
            if band_color_hex.lower() == "transparent"
            else hex_to_rgba(band_color_hex)
        )

        canvas = Image.new("RGBA", (image.width, image.height + band_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        if self.style.caption_position == "top":
            band_top = 0
            image_offset = (0, band_height)
        else:
            band_top = image.height
            image_offset = (0, 0)

        draw.rectangle([(0, band_top), (image.width, band_top + band_height)], fill=band_background)
        canvas.paste(image, image_offset, mask=image)

        font_size = int(band_height * 0.42)
        font = self._load_font(font_size)
        text_color = hex_to_rgba(self.style.caption_color)

        bbox = draw.textbbox((0, 0), self.style.caption_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (canvas.width - text_width) / 2 - bbox[0]
        y = band_top + (band_height - text_height) / 2 - bbox[1]

        draw.text((x, y), self.style.caption_text, font=font, fill=text_color)
        logger.info(
            "Legenda '%s' adicionada (%s) ao QR Code.", self.style.caption_text, self.style.caption_position
        )
        return canvas

    # ------------------------------------------------------------------ #
    # Efeito "cartão": cantos arredondados + borda colorida
    # ------------------------------------------------------------------ #
    def _apply_card_style(self, image: Image.Image) -> Image.Image:
        """
        Envolve a composição final (QR + logo + legenda) em cantos
        arredondados com uma borda colorida, no estilo "cartão/crachá".

        A imagem é EXPANDIDA (nunca cortada) para acomodar a borda, de
        forma que nenhum módulo do QR Code ou texto da legenda seja
        sobreposto pela borda.

        Args:
            image: Imagem já composta (QR + logo + legenda, se houver).

        Returns:
            Imagem com cantos arredondados e borda, ou a mesma imagem
            recebida caso `rounded_corners` esteja desativado.
        """
        if not self.style.rounded_corners:
            return image

        border_width = max(int(min(image.size) * 0.018), 4)
        radius = int(min(image.size) * 0.07) + border_width

        padded_size = (image.width + border_width * 2, image.height + border_width * 2)
        padded = Image.new("RGBA", padded_size, (0, 0, 0, 0))
        padded.paste(image, (border_width, border_width))

        border_color_hex = self.style.card_border_color or self.style.dark_color
        border_color = hex_to_rgba(border_color_hex)

        mask = Image.new("L", padded_size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [(0, 0), (padded_size[0] - 1, padded_size[1] - 1)], radius=radius, fill=255
        )
        rounded = Image.new("RGBA", padded_size, (0, 0, 0, 0))
        rounded.paste(padded, (0, 0), mask=mask)

        draw = ImageDraw.Draw(rounded)
        inset = border_width / 2
        draw.rounded_rectangle(
            [(inset, inset), (padded_size[0] - 1 - inset, padded_size[1] - 1 - inset)],
            radius=radius,
            outline=border_color,
            width=border_width,
        )
        logger.info("Efeito cartão aplicado (cantos arredondados + borda %s).", border_color_hex)
        return rounded

    # ------------------------------------------------------------------ #
    # API pública: geração da imagem final (usada também pela GUI)
    # ------------------------------------------------------------------ #
    def render(self) -> Image.Image:
        """
        Gera a imagem final do QR Code (com logotipo e legenda, se
        configurados), pronta para pré-visualização ou exportação.

        Returns:
            Imagem PIL (RGBA) do QR Code finalizado.
        """
        base_image = self._render_base_png()
        if self.style.eye_mark:
            base_image = self._apply_custom_eyes(base_image)
        if self.style.logo_path:
            base_image = self._compose_with_logo(base_image)
        if self.style.caption_text:
            base_image = self._add_caption(base_image)
        base_image = self._apply_card_style(base_image)
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
        if self.style.gradient_end_color:
            svg_content = self._apply_gradient_svg(svg_content)

        width, height = qr.symbol_size(scale=10, border=self.style.border)

        if self.style.eye_mark:
            svg_content = self._embed_eyes_in_svg(svg_content, qr)
        if self.style.logo_path:
            svg_content = self._embed_logo_in_svg(svg_content, qr)
        if self.style.caption_text:
            svg_content = self._embed_caption_in_svg(svg_content, qr)
            band_height = max(int(width * 0.16), 60)
            height += band_height

        svg_content = self._apply_card_style_svg(svg_content, width, height)

        destination.write_text(svg_content, encoding="utf-8")
        logger.info("SVG salvo em: %s", destination)
        return destination

    def _apply_gradient_svg(self, svg_content: str) -> str:
        """
        Substitui o preenchimento sólido dos módulos do QR Code por um
        gradiente linear SVG nativo (`<linearGradient>`), entre
        `dark_color` e `gradient_end_color`.
        """
        direction_coords = {
            "diagonal": ("0%", "0%", "100%", "100%"),
            "horizontal": ("0%", "0%", "100%", "0%"),
            "vertical": ("0%", "0%", "0%", "100%"),
        }
        x1, y1, x2, y2 = direction_coords.get(self.style.gradient_direction, direction_coords["diagonal"])

        gradient_def = (
            '<defs><linearGradient id="qrGradient" '
            f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
            f'<stop offset="0%" stop-color="{self.style.dark_color}" />'
            f'<stop offset="100%" stop-color="{self.style.gradient_end_color}" />'
            "</linearGradient></defs>"
        )

        # Troca o preenchimento sólido dos módulos (fill="dark_color") pelo gradiente
        target = f'fill="{self.style.dark_color}"'
        if target in svg_content:
            svg_content = svg_content.replace(target, 'fill="url(#qrGradient)"', 1)

        match = re.search(r'<svg[^>]*>', svg_content)
        if match:
            insert_at = match.end()
            svg_content = svg_content[:insert_at] + gradient_def + svg_content[insert_at:]

        return svg_content

    def _embed_eyes_in_svg(self, svg_content: str, qr: segno.QRCode) -> str:
        """
        Insere o caractere de `eye_mark` (ex.: "S") sobre o quadrado
        central dos 3 marcadores de posição, mantendo os anéis externos
        do SVG original intactos (mesma lógica aplicada no PNG).
        """
        svg_scale = 10  # mesma escala usada em _save_svg
        modules = qr.symbol_size(scale=1, border=0)[0]
        module_px = svg_scale
        border_px = self.style.border * svg_scale
        inner_size = 3 * module_px

        eye_top_left_modules = [
            (0, 0),
            (modules - 7, 0),
            (0, modules - 7),
        ]

        light_color = (
            "#FFFFFF" if self.style.light_color.lower() == "transparent" else self.style.light_color
        )
        font_size = max(int(inner_size * 0.8), 8)

        markup_parts = []
        for mx, my in eye_top_left_modules:
            cx = border_px + (mx + 3.5) * module_px
            cy = border_px + (my + 3.5) * module_px
            half = inner_size / 2
            markup_parts.append(
                f'<rect x="{cx - half:.2f}" y="{cy - half:.2f}" '
                f'width="{inner_size}" height="{inner_size}" fill="{light_color}" />'
                f'<text x="{cx:.2f}" y="{cy + font_size * 0.35:.2f}" '
                f'font-family="Arial, Helvetica, sans-serif" font-weight="bold" '
                f'font-size="{font_size}" fill="{self.style.dark_color}" '
                f'text-anchor="middle">{self._escape_xml(self.style.eye_mark)}</text>'
            )

        markup = "".join(markup_parts)
        if "</svg>" in svg_content:
            svg_content = svg_content.replace("</svg>", f"{markup}</svg>")
        return svg_content

    def _embed_caption_in_svg(self, svg_content: str, qr: segno.QRCode) -> str:
        """
        Amplia o SVG (altura e viewBox) e insere uma faixa colorida com
        texto vetorial centralizado, no topo ou embaixo conforme
        `caption_position` — mantém tudo em um único arquivo vetorial,
        nítido em qualquer tamanho de impressão.
        """
        width, height = qr.symbol_size(scale=10, border=self.style.border)
        band_height = max(int(width * 0.16), 60)
        new_height = height + band_height
        band_color = self.style.caption_background_color or self.style.dark_color
        font_size = int(band_height * 0.42)

        if self.style.caption_position == "top":
            band_y = 0
            text_y = band_height / 2 + font_size * 0.35
            content_shift = f'<g transform="translate(0,{band_height})">'
        else:
            band_y = height
            text_y = height + band_height / 2 + font_size * 0.35
            content_shift = "<g>"

        # Atualiza os atributos height/viewBox do <svg> raiz para acomodar a faixa
        svg_content = re.sub(r'height="[\d.]+"', f'height="{new_height}"', svg_content, count=1)
        svg_content = re.sub(
            r'viewBox="0 0 [\d.]+ [\d.]+"', f'viewBox="0 0 {width} {new_height}"', svg_content, count=1
        )

        band_and_text = (
            f'<rect x="0" y="{band_y}" width="{width}" height="{band_height}" fill="{band_color}" />'
            f'<text x="{width / 2:.2f}" y="{text_y:.2f}" '
            f'font-family="Arial, Helvetica, sans-serif" font-weight="bold" font-size="{font_size}" '
            f'fill="{self.style.caption_color}" text-anchor="middle">'
            f"{self._escape_xml(self.style.caption_text)}</text>"
        )

        # Se a legenda fica no topo, o conteúdo original do QR (que começa
        # em y=0) precisa ser deslocado para baixo, para abrir espaço.
        if self.style.caption_position == "top":
            match = re.search(r'<svg[^>]*>', svg_content)
            if match:
                svg_open_end = match.end()
                before = svg_content[:svg_open_end]
                rest = svg_content[svg_open_end:].replace("</svg>", "")
                svg_content = f"{before}{content_shift}{rest}</g>{band_and_text}</svg>"
        else:
            if "</svg>" in svg_content:
                svg_content = svg_content.replace("</svg>", f"{band_and_text}</svg>")

        return svg_content

    def _apply_card_style_svg(self, svg_content: str, content_width: float, content_height: float) -> str:
        """
        Envolve todo o SVG em cantos arredondados com uma borda colorida
        (efeito "cartão"), expandindo o viewBox para nunca cortar o
        conteúdo original — equivalente vetorial de `_apply_card_style`.
        """
        if not self.style.rounded_corners:
            return svg_content

        border_width = max(min(content_width, content_height) * 0.018, 4)
        radius = min(content_width, content_height) * 0.07 + border_width
        total_width = content_width + border_width * 2
        total_height = content_height + border_width * 2
        border_color = self.style.card_border_color or self.style.dark_color

        match = re.search(r'<svg[^>]*>', svg_content)
        if not match:
            return svg_content
        svg_open_end = match.end()
        before = svg_content[:svg_open_end]
        rest = svg_content[svg_open_end:].replace("</svg>", "")

        before = re.sub(r'width="[\d.]+"', f'width="{total_width:.2f}"', before, count=1)
        before = re.sub(r'height="[\d.]+"', f'height="{total_height:.2f}"', before, count=1)
        before = re.sub(
            r'viewBox="0 0 [\d.]+ [\d.]+"',
            f'viewBox="0 0 {total_width:.2f} {total_height:.2f}"',
            before,
            count=1,
        )

        clip_def = (
            '<defs><clipPath id="cardClip">'
            f'<rect x="0" y="0" width="{total_width:.2f}" height="{total_height:.2f}" '
            f'rx="{radius:.2f}" ry="{radius:.2f}" /></clipPath></defs>'
        )
        border_rect = (
            f'<rect x="{border_width / 2:.2f}" y="{border_width / 2:.2f}" '
            f'width="{total_width - border_width:.2f}" height="{total_height - border_width:.2f}" '
            f'rx="{radius:.2f}" ry="{radius:.2f}" fill="none" stroke="{border_color}" '
            f'stroke-width="{border_width:.2f}" />'
        )

        return (
            f"{before}{clip_def}"
            f'<g clip-path="url(#cardClip)">'
            f'<g transform="translate({border_width:.2f},{border_width:.2f})">{rest}</g>'
            f"</g>{border_rect}</svg>"
        )

    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escapa caracteres especiais para inserção segura em texto SVG/XML."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

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
