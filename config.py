"""
config.py
=========
Configurações centrais, constantes e modelos de dados (dataclasses)
utilizados em todo o projeto QRCodeGenerator.

Manter todas as constantes e tipos aqui facilita a manutenção e evita
"números mágicos" espalhados pelo código.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Tuple

# --------------------------------------------------------------------------- #
# Tipos auxiliares (Type Hints)
# --------------------------------------------------------------------------- #
ErrorCorrectionLevel = Literal["L", "M", "Q", "H"]
OutputFormat = Literal["PNG", "SVG", "PDF"]
CaptionPosition = Literal["top", "bottom"]
GradientDirection = Literal["diagonal", "horizontal", "vertical"]


def _resolve_base_dir() -> Path:
    """
    Resolve o diretório base do projeto, funcionando tanto em execução
    normal (via `python main.py`) quanto empacotado como executável
    (`.exe` gerado pelo PyInstaller).

    Quando empacotado com `--onefile`, os arquivos do projeto ficam
    extraídos em uma pasta temporária a cada execução — por isso,
    dados GRAVÁVEIS (como `output/` e `landing_page/`) precisam ficar
    ao lado do `.exe` real, não dentro dessa pasta temporária.
    """
    if getattr(sys, "frozen", False):
        # Executando como .exe empacotado: usa a pasta onde o .exe está.
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


# --------------------------------------------------------------------------- #
# Diretórios padrão do projeto
# --------------------------------------------------------------------------- #
BASE_DIR: Path = _resolve_base_dir()
ASSETS_DIR: Path = BASE_DIR / "assets"
OUTPUT_DIR: Path = BASE_DIR / "output"
LANDING_PAGE_DIR: Path = BASE_DIR / "landing_page"

# --------------------------------------------------------------------------- #
# Constantes de personalização do QR Code
# --------------------------------------------------------------------------- #
LOGO_TARGET_SIZE: Tuple[int, int] = (300, 300)   # tamanho padrão do logotipo (px)
MIN_DPI: int = 300                               # resolução mínima exigida (alta qualidade)
DEFAULT_LOGO_RATIO: float = 0.22                 # logo ocupa no máx. ~22% da largura do QR
LOGO_BACKDROP_PADDING_RATIO: float = 0.0         # margem branca ao redor do logo (0 = sem margem)
DEFAULT_QR_SIZE_PX: int = 1000                   # tamanho padrão da imagem final (px)
DEFAULT_BORDER_MODULES: int = 4                  # quiet zone padrão (módulos)

VALID_ERROR_LEVELS: Tuple[ErrorCorrectionLevel, ...] = ("L", "M", "Q", "H")
VALID_OUTPUT_FORMATS: Tuple[OutputFormat, ...] = ("PNG", "SVG", "PDF")

# --------------------------------------------------------------------------- #
# Cores oficiais do Sistema Indústria (Manual de Marcas CNI/SESI/SENAI/IEL,
# versão 2024). Usadas como preset rápido de identidade visual na GUI.
# --------------------------------------------------------------------------- #
SENAI_BLUE: str = "#164194"    # Pantone 293 C  (R22 G65 B148)
SENAI_ORANGE: str = "#EF4910"  # Pantone Orange 021 C (R239 G73 B16)
SESI_GREEN: str = "#52AE32"    # Pantone 361 C  (R82 G174 B50)


@dataclass(slots=True)
class QRStyleConfig:
    """
    Agrupa todas as opções necessárias para gerar um QR Code
    (dados, dimensões, cores, correção de erro, logotipo e legenda).

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
        caption_text: Texto opcional exibido na faixa do QR Code
            (ex.: "Aponte a Câmera").
        caption_color: Cor do texto da legenda (hex). Padrão branco,
            pensado para contrastar com a faixa colorida.
        caption_position: Posição da faixa de legenda: "top" (topo,
            estilo cartão/crachá) ou "bottom" (abaixo do QR Code).
        caption_background_color: Cor de fundo da faixa da legenda.
            Se None, usa `dark_color` (mesma cor do QR Code).
        eye_mark: Caractere opcional (ex.: "S") desenhado no centro dos
            3 marcadores de posição ("olhos") do QR Code. ATENÇÃO: essa
            personalização não é protegida por correção de erro — teste
            a leitura em vários celulares antes de usar em massa.
        rounded_corners: Se True, aplica cantos arredondados e uma borda
            colorida a toda a composição final (efeito "cartão").
        card_border_color: Cor da borda do cartão. Se None, usa `dark_color`.
        gradient_end_color: Se definido, os módulos escuros do QR Code são
            desenhados com um degradê de `dark_color` até esta cor, em vez
            de uma cor sólida.
        gradient_direction: Direção do degradê: "diagonal" (padrão),
            "horizontal" ou "vertical".
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
    caption_text: Optional[str] = None
    caption_color: str = "#FFFFFF"
    caption_position: CaptionPosition = "top"
    caption_background_color: Optional[str] = None
    eye_mark: Optional[str] = None
    rounded_corners: bool = True
    card_border_color: Optional[str] = None
    gradient_end_color: Optional[str] = None
    gradient_direction: GradientDirection = "diagonal"

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
