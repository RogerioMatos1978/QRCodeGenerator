"""
utils.py
========
Funções utilitárias reutilizáveis: validação de URLs, manipulação de
cores, redimensionamento de logotipos com transparência e configuração
de logging. Mantidas separadas para favorecer reuso e testabilidade.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

from PIL import Image, ImageChops

from config import LOGO_TARGET_SIZE

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configura e retorna um logger padronizado para o projeto.

    Args:
        level: Nível de logging (padrão: logging.INFO).

    Returns:
        Instância de logging.Logger configurada.
    """
    logger = logging.getLogger("QRCodeGenerator")
    if not logger.handlers:  # evita handlers duplicados em reimportações
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


logger = setup_logging()


# --------------------------------------------------------------------------- #
# Validação
# --------------------------------------------------------------------------- #
def validate_url(url: str) -> bool:
    """
    Valida se uma string é uma URL bem formada (http/https).

    Args:
        url: String a ser validada.

    Returns:
        True se a URL for válida, False caso contrário.
    """
    if not url or not isinstance(url, str):
        return False
    try:
        result = urlparse(url.strip())
        return all([result.scheme in ("http", "https"), result.netloc])
    except ValueError:
        return False


def validate_hex_color(color: str) -> bool:
    """
    Valida se uma string representa uma cor hexadecimal válida
    (ex.: "#FFFFFF" ou "#FFF"). A palavra "transparent" também é aceita.

    Args:
        color: String de cor a ser validada.

    Returns:
        True se válida, False caso contrário.
    """
    if color.lower() == "transparent":
        return True
    pattern = r"^#(?:[0-9a-fA-F]{3}){1,2}$"
    return bool(re.match(pattern, color))


# --------------------------------------------------------------------------- #
# Cores
# --------------------------------------------------------------------------- #
def hex_to_rgba(color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    """
    Converte uma cor hexadecimal (#RRGGBB ou #RGB) em uma tupla RGBA.

    Args:
        color: Cor no formato hexadecimal.
        alpha: Canal alfa (0-255). Ignorado se color == "transparent".

    Returns:
        Tupla (R, G, B, A).
    """
    if color.lower() == "transparent":
        return (255, 255, 255, 0)

    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    if len(color) != 6:
        raise ValueError(f"Cor hexadecimal inválida: {color}")

    r, g, b = (int(color[i : i + 2], 16) for i in (0, 2, 4))
    return (r, g, b, alpha)


# --------------------------------------------------------------------------- #
# Manipulação de imagens (logotipo)
# --------------------------------------------------------------------------- #
def ensure_directory(path: Path) -> Path:
    """Garante que um diretório exista, criando-o se necessário."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_pictures_directory() -> Path:
    """
    Retorna a pasta de imagens ("Pictures") do usuário atual, de forma
    multiplataforma (Windows, macOS, Linux).

    No Windows, mesmo em instalações com o Explorer exibindo o nome
    traduzido "Imagens", o caminho real da pasta no sistema de arquivos
    continua sendo `Pictures` (a tradução é apenas visual, feita via
    `desktop.ini`) — por isso `Path.home() / "Pictures"` funciona de
    forma confiável na grande maioria dos casos.

    Returns:
        Caminho da pasta de imagens do usuário (criada se não existir).
    """
    pictures_dir = Path.home() / "Pictures"
    return ensure_directory(pictures_dir)


def _autocrop_to_content(image: Image.Image, tolerance: int = 12) -> Image.Image:
    """
    Remove margens vazias ao redor do conteúdo real de uma imagem RGBA,
    para que o logotipo preencha melhor o espaço disponível (em vez de
    ficar pequeno dentro de uma grande área em branco/transparente).

    Primeiro tenta usar o canal alfa (transparência real). Se a imagem
    não tiver transparência (é totalmente opaca), detecta e remove uma
    margem de cor sólida (ex.: fundo branco) comparando com a cor do
    canto superior esquerdo.

    Args:
        image: Imagem RGBA de entrada.
        tolerance: Diferença de cor (0-255) tolerada como "fundo".

    Returns:
        Imagem recortada na caixa delimitadora do conteúdo. Se nenhum
        conteúdo distinto do fundo for detectado, retorna a imagem original.
    """
    rgba = image.convert("RGBA")
    bbox = rgba.split()[-1].getbbox()  # bounding box do canal alfa

    if bbox is None or bbox == (0, 0, rgba.width, rgba.height):
        # Sem transparência real (ou totalmente opaca): tenta detectar
        # uma margem de cor de fundo sólida a partir do canto da imagem.
        background_color = rgba.getpixel((0, 0))
        background = Image.new("RGBA", rgba.size, background_color)
        diff = ImageChops.difference(rgba.convert("RGB"), background.convert("RGB"))
        mask = diff.convert("L").point(lambda p: 255 if p > tolerance else 0)
        bbox = mask.getbbox()

    return rgba.crop(bbox) if bbox else rgba


def resize_logo_with_transparency(
    image_path: Path, target_size: Tuple[int, int] = LOGO_TARGET_SIZE
) -> Image.Image:
    """
    Carrega um logotipo, converte para RGBA (preservando transparência),
    recorta automaticamente margens vazias ao redor do conteúdo real, e
    o redimensiona proporcionalmente para caber em um quadrado
    `target_size`, centralizando o resultado em um canvas transparente.

    Args:
        image_path: Caminho do arquivo de imagem do logotipo.
        target_size: Tamanho (largura, altura) do canvas final em pixels.

    Returns:
        Imagem PIL redimensionada e centralizada, com fundo transparente.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        OSError: Se o arquivo não puder ser aberto como imagem.
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Logotipo não encontrado: {image_path}")

    with Image.open(image_path) as img:
        img = img.convert("RGBA")
        img = _autocrop_to_content(img)

        # Redimensiona mantendo a proporção (thumbnail respeita aspect ratio)
        img_copy = img.copy()
        img_copy.thumbnail(target_size, Image.Resampling.LANCZOS)

        # Cria um canvas transparente do tamanho alvo e centraliza a imagem
        canvas = Image.new("RGBA", target_size, (255, 255, 255, 0))
        offset = (
            (target_size[0] - img_copy.width) // 2,
            (target_size[1] - img_copy.height) // 2,
        )
        canvas.paste(img_copy, offset, mask=img_copy)

    logger.info("Logotipo recortado e redimensionado para %sx%s px", *target_size)
    return canvas