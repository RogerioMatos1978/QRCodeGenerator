"""
config.py
=========
Configurações centrais, constantes e modelos de dados (dataclasses)
utilizados em todo o projeto QRCodeGenerator.

Manter todas as constantes e tipos aqui facilita a manutenção e evita
"números mágicos" espalhados pelo código.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Tuple

# --------------------------------------------------------------------------- #
# Tipos auxiliares (Type Hints)
# --------------------------------------------------------------------------- #
ErrorCorrectionLevel = Literal["L", "M", "Q", "H"]
OutputFormat = Literal["PNG", "SVG", "PDF"]

# --------------------------------------------------------------------------- #
# Diretórios padrão do projeto
# --------------------------------------------------------------------------- #
BASE_DIR: Path = Path(__file__).resolve().parent
ASSETS_DIR: Path = BASE_DIR / "assets"
OUTPUT_DIR: Path = BASE_DIR / "output"
LANDING_PAGE_DIR: Path = BASE_DIR / "landing_page"

# --------------------------------------------------------------------------- #
# Constantes de personalização do QR Code
# --------------------------------------------------------------------------- #
LOGO_TARGET_SIZE: Tuple[int, int] = (300, 300)   # tamanho padrão do logotipo (px)
MIN_DPI: int = 300                               # resolução mínima exigida (alta qualidade)
DEFAULT_LOGO_RATIO: float = 0.22                 # logo ocupa no máx. ~22% da largura do QR
DEFAULT_QR_SIZE_PX: int = 1000                   # tamanho padrão da imagem final (px)
DEFAULT_BORDER_MODULES: int = 4                  # quiet zone padrão (módulos)

VALID_ERROR_LEVELS: Tuple[ErrorCorrectionLevel, ...] = ("L", "M", "Q", "H")
VALID_OUTPUT_FORMATS: Tuple[OutputFormat, ...] = ("PNG", "SVG", "PDF")


@dataclass(slots=True)
class QRStyleConfig:
    """
    Agrupa todas as opções necessárias para gerar um QR Code
    (dados, dimensões, cores, correção de erro e logotipo).

    Attributes:
        data: Conteúdo que será codificado no QR Code (URL da landing page).
        size_px: Tamanho final da imagem (lado, em pixels).
        border: Margem (quiet zone), em número de módulos.
        error_correction: Nível de correção de erro (L, M, Q, H).
        dark_color: Cor dos módulos escuros do QR Code (hex, ex.: "#000000").
        light_color: Cor de fundo (hex, ex.: "#FFFFFF"). Use "transparent"
            para gerar fundo transparente (apenas PNG).
        logo_path: Caminho opcional para um logotipo a ser centralizado.
        output_formats: Formatos de exportação desejados.
        dpi: Resolução da imagem exportada (mínimo recomendado: 300).
    """

    data: str
    size_px: int = DEFAULT_QR_SIZE_PX
    border: int = DEFAULT_BORDER_MODULES
    error_correction: ErrorCorrectionLevel = "M"
    dark_color: str = "#000000"
    light_color: str = "#FFFFFF"
    logo_path: Optional[Path] = None
    output_formats: Tuple[OutputFormat, ...] = ("PNG",)
    dpi: int = MIN_DPI

    def __post_init__(self) -> None:
        """Regras de negócio aplicadas após a criação do objeto."""
        # Regra obrigatória: se houver logotipo, a correção de erro deve
        # ser a maior possível (H), pois parte do QR Code ficará coberta.
        if self.logo_path is not None:
            self.error_correction = "H"

        if self.error_correction not in VALID_ERROR_LEVELS:
            raise ValueError(
                f"Nível de correção de erro inválido: {self.error_correction}. "
                f"Valores aceitos: {VALID_ERROR_LEVELS}"
            )

        for fmt in self.output_formats:
            if fmt not in VALID_OUTPUT_FORMATS:
                raise ValueError(
                    f"Formato de saída inválido: {fmt}. "
                    f"Valores aceitos: {VALID_OUTPUT_FORMATS}"
                )


@dataclass(slots=True)
class RedirectURLs:
    """Par de URLs (Android / iOS) usadas para montar a landing page."""

    android_url: str
    ios_url: str
    fallback_url: Optional[str] = None  # usada quando o SO não é identificado

    def __post_init__(self) -> None:
        if not self.fallback_url:
            # Por padrão, dispositivos não identificados caem na URL Android
            self.fallback_url = self.android_url
