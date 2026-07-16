"""
gui.py
======
Interface gráfica (CustomTkinter, modo escuro) para o QRCodeGenerator.

Permite ao usuário informar as URLs de Android e iOS, personalizar
cores/tamanho/logotipo, gerar a landing page de redirecionamento,
pré-visualizar o QR Code resultante e salvá-lo nos formatos desejados.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox
from typing import Optional

import customtkinter as ctk
from PIL import Image

from config import (
    LANDING_PAGE_DIR,
    OUTPUT_DIR,
    OutputFormat,
    QRStyleConfig,
    RedirectURLs,
)
from landing_page_builder import build_landing_page
from qr_generator import QRCodeGenerationError, QRCodeGenerator
from utils import logger, validate_hex_color, validate_url

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class QRCodeApp(ctk.CTk):
    """Janela principal da aplicação."""

    def __init__(self) -> None:
        super().__init__()

        self.title("QR Code Generator - Redirecionamento por Sistema Operacional")
        self.geometry("1080x720")
        self.minsize(960, 640)

        # Estado interno
        self.logo_path: Optional[Path] = None
        self.dark_color: str = "#000000"
        self.light_color: str = "#FFFFFF"
        self.generator: Optional[QRCodeGenerator] = None
        self.preview_image_ctk: Optional[ctk.CTkImage] = None

        self._build_layout()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_form_panel()
        self._build_preview_panel()

    def _build_form_panel(self) -> None:
        form = ctk.CTkScrollableFrame(self, label_text="Configurações")
        form.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=16)
        form.grid_columnconfigure(0, weight=1)

        row = 0

        # --- URLs ---------------------------------------------------- #
        ctk.CTkLabel(form, text="URL Android (Google Play)", anchor="w").grid(
            row=row, column=0, sticky="ew", pady=(4, 0)
        )
        row += 1
        self.android_entry = ctk.CTkEntry(
            form, placeholder_text="https://play.google.com/store/apps/details?id=..."
        )
        self.android_entry.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        row += 1

        ctk.CTkLabel(form, text="URL iPhone (App Store)", anchor="w").grid(
            row=row, column=0, sticky="ew", pady=(4, 0)
        )
        row += 1
        self.ios_entry = ctk.CTkEntry(
            form, placeholder_text="https://apps.apple.com/app/id..."
        )
        self.ios_entry.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        row += 1

        ctk.CTkLabel(
            form,
            text="URL pública da landing page (após publicá-la)",
            anchor="w",
        ).grid(row=row, column=0, sticky="ew", pady=(4, 0))
        row += 1
        self.landing_entry = ctk.CTkEntry(
            form, placeholder_text="https://seusite.com/redirect/"
        )
        self.landing_entry.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        row += 1
        ctk.CTkLabel(
            form,
            text=(
                "* Esta é a URL que será codificada no QR Code. Gere a landing\n"
                "  page (botão abaixo), publique o arquivo landing_page/index.html\n"
                "  em um host estático e cole a URL final aqui."
            ),
            anchor="w",
            justify="left",
            text_color="gray70",
            font=ctk.CTkFont(size=11),
        ).grid(row=row, column=0, sticky="ew", pady=(0, 8))
        row += 1

        self.build_landing_btn = ctk.CTkButton(
            form, text="Gerar landing_page/index.html", command=self._on_build_landing_page
        )
        self.build_landing_btn.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        row += 1

        # --- Logotipo -------------------------------------------------- #
        ctk.CTkLabel(form, text="Logotipo (opcional, 300x300 px)", anchor="w").grid(
            row=row, column=0, sticky="ew", pady=(4, 0)
        )
        row += 1

        logo_frame = ctk.CTkFrame(form, fg_color="transparent")
        logo_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        logo_frame.grid_columnconfigure(0, weight=1)

        self.logo_btn = ctk.CTkButton(
            logo_frame, text="Selecionar logotipo...", command=self._on_select_logo
        )
        self.logo_btn.grid(row=0, column=0, sticky="ew")

        self.logo_preview_label = ctk.CTkLabel(logo_frame, text="", width=80, height=80)
        self.logo_preview_label.grid(row=0, column=1, padx=(8, 0))
        row += 1

        # --- Cores ------------------------------------------------------ #
        color_frame = ctk.CTkFrame(form, fg_color="transparent")
        color_frame.grid(row=row, column=0, sticky="ew", pady=(4, 8))
        color_frame.grid_columnconfigure((0, 1), weight=1)

        self.dark_color_btn = ctk.CTkButton(
            color_frame,
            text="Cor do QR Code",
            fg_color=self.dark_color,
            command=lambda: self._pick_color("dark"),
        )
        self.dark_color_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.light_color_btn = ctk.CTkButton(
            color_frame,
            text="Cor de fundo",
            fg_color=self.light_color,
            text_color="black",
            command=lambda: self._pick_color("light"),
        )
        self.light_color_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        row += 1

        # --- Tamanho / margem -------------------------------------------- #
        ctk.CTkLabel(form, text="Tamanho (px)", anchor="w").grid(
            row=row, column=0, sticky="ew", pady=(4, 0)
        )
        row += 1
        self.size_slider = ctk.CTkSlider(form, from_=400, to=2400, number_of_steps=20)
        self.size_slider.set(1000)
        self.size_slider.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        row += 1

        ctk.CTkLabel(form, text="Margem / quiet zone (módulos)", anchor="w").grid(
            row=row, column=0, sticky="ew", pady=(4, 0)
        )
        row += 1
        self.border_slider = ctk.CTkSlider(form, from_=1, to=12, number_of_steps=11)
        self.border_slider.set(4)
        self.border_slider.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        row += 1

        # --- Correção de erro -------------------------------------------- #
        ctk.CTkLabel(form, text="Correção de erro", anchor="w").grid(
            row=row, column=0, sticky="ew", pady=(4, 0)
        )
        row += 1
        self.error_correction_menu = ctk.CTkOptionMenu(form, values=["L", "M", "Q", "H"])
        self.error_correction_menu.set("M")
        self.error_correction_menu.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        row += 1

        # --- Formatos de saída --------------------------------------- #
        ctk.CTkLabel(form, text="Formatos de exportação", anchor="w").grid(
            row=row, column=0, sticky="ew", pady=(4, 0)
        )
        row += 1
        formats_frame = ctk.CTkFrame(form, fg_color="transparent")
        formats_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))

        self.format_vars = {
            "PNG": ctk.BooleanVar(value=True),
            "SVG": ctk.BooleanVar(value=False),
            "PDF": ctk.BooleanVar(value=False),
        }
        for i, fmt in enumerate(self.format_vars):
            ctk.CTkCheckBox(
                formats_frame, text=fmt, variable=self.format_vars[fmt]
            ).grid(row=0, column=i, padx=(0, 12))
        row += 1

        # --- Ações -------------------------------------------------------- #
        self.generate_btn = ctk.CTkButton(
            form, text="Gerar QR Code", command=self._on_generate, height=40
        )
        self.generate_btn.grid(row=row, column=0, sticky="ew", pady=(12, 4))
        row += 1

        self.save_btn = ctk.CTkButton(
            form,
            text="Salvar",
            command=self._on_save,
            height=40,
            state="disabled",
            fg_color="#2f8f4e",
            hover_color="#256e3c",
        )
        self.save_btn.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        row += 1

        self.status_label = ctk.CTkLabel(form, text="", text_color="gray70", anchor="w")
        self.status_label.grid(row=row, column=0, sticky="ew", pady=(8, 0))

    def _build_preview_panel(self) -> None:
        preview_frame = ctk.CTkFrame(self)
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=16)
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(
            preview_frame,
            text="A pré-visualização do QR Code aparecerá aqui",
            width=480,
            height=480,
        )
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

    # ------------------------------------------------------------------ #
    # Callbacks
    # ------------------------------------------------------------------ #
    def _pick_color(self, target: str) -> None:
        """Abre o seletor de cores nativo e atualiza o botão correspondente."""
        color = colorchooser.askcolor(title="Escolha uma cor")
        if color and color[1]:
            hex_color = color[1]
            if target == "dark":
                self.dark_color = hex_color
                self.dark_color_btn.configure(fg_color=hex_color)
            else:
                self.light_color = hex_color
                self.light_color_btn.configure(fg_color=hex_color)

    def _on_select_logo(self) -> None:
        """Abre o seletor de arquivos para escolher o logotipo."""
        filetypes = [("Imagens", "*.png *.jpg *.jpeg *.webp"), ("Todos os arquivos", "*.*")]
        path_str = filedialog.askopenfilename(title="Selecionar logotipo", filetypes=filetypes)
        if not path_str:
            return

        self.logo_path = Path(path_str)
        try:
            with Image.open(self.logo_path) as img:
                thumbnail = img.convert("RGBA").copy()
                thumbnail.thumbnail((80, 80), Image.Resampling.LANCZOS)
                ctk_thumb = ctk.CTkImage(
                    light_image=thumbnail, dark_image=thumbnail, size=thumbnail.size
                )
            self.logo_preview_label.configure(image=ctk_thumb, text="")
            self.logo_preview_label.image = ctk_thumb  # evita garbage collection
            # Logo presente -> força a maior correção de erro
            self.error_correction_menu.set("H")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erro ao carregar logotipo", str(exc))
            self.logo_path = None

    def _on_build_landing_page(self) -> None:
        """Gera o arquivo landing_page/index.html a partir das URLs informadas."""
        android_url = self.android_entry.get().strip()
        ios_url = self.ios_entry.get().strip()

        if not validate_url(android_url) or not validate_url(ios_url):
            messagebox.showerror(
                "URLs inválidas",
                "Informe URLs válidas (iniciando com http:// ou https://) "
                "para Android e iOS antes de gerar a landing page.",
            )
            return

        try:
            urls = RedirectURLs(android_url=android_url, ios_url=ios_url)
            path = build_landing_page(urls, LANDING_PAGE_DIR)
            self._set_status(f"Landing page gerada em: {path}")
            messagebox.showinfo(
                "Landing page gerada",
                f"Arquivo criado em:\n{path}\n\n"
                "Publique esta pasta em um host estático (GitHub Pages, "
                "Netlify, Vercel, etc.) e cole a URL final no campo "
                "'URL pública da landing page'.",
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erro ao gerar landing page", str(exc))

    def _collect_style_config(self) -> Optional[QRStyleConfig]:
        """Lê os campos da interface e monta um QRStyleConfig validado."""
        landing_url = self.landing_entry.get().strip()

        if not validate_url(landing_url):
            messagebox.showerror(
                "URL inválida",
                "Informe a URL pública da landing page (campo dedicado) "
                "antes de gerar o QR Code. É essa URL que será codificada.",
            )
            return None

        if not validate_hex_color(self.dark_color) or not validate_hex_color(self.light_color):
            messagebox.showerror("Cor inválida", "As cores selecionadas são inválidas.")
            return None

        try:
            return QRStyleConfig(
                data=landing_url,
                size_px=int(self.size_slider.get()),
                border=int(self.border_slider.get()),
                error_correction=self.error_correction_menu.get(),  # type: ignore[arg-type]
                dark_color=self.dark_color,
                light_color=self.light_color,
                logo_path=self.logo_path,
                output_formats=self._selected_formats(),
            )
        except ValueError as exc:
            messagebox.showerror("Configuração inválida", str(exc))
            return None

    def _selected_formats(self) -> tuple[OutputFormat, ...]:
        selected = tuple(fmt for fmt, var in self.format_vars.items() if var.get())  # type: ignore[misc]
        return selected or ("PNG",)

    def _on_generate(self) -> None:
        """Gera o QR Code e atualiza a pré-visualização."""
        style = self._collect_style_config()
        if style is None:
            return

        try:
            self.generator = QRCodeGenerator(style)
            image = self.generator.render()
            self._update_preview(image)
            self.save_btn.configure(state="normal")
            self._set_status("QR Code gerado com sucesso. Clique em 'Salvar' para exportar.")
        except QRCodeGenerationError as exc:
            messagebox.showerror("Erro ao gerar QR Code", str(exc))
            logger.exception("Falha ao gerar QR Code")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erro inesperado", str(exc))
            logger.exception("Erro inesperado ao gerar QR Code")

    def _update_preview(self, image: Image.Image) -> None:
        preview = image.copy()
        preview.thumbnail((480, 480), Image.Resampling.LANCZOS)
        self.preview_image_ctk = ctk.CTkImage(
            light_image=preview, dark_image=preview, size=preview.size
        )
        self.preview_label.configure(image=self.preview_image_ctk, text="")

    def _on_save(self) -> None:
        """Salva o QR Code gerado nos formatos selecionados."""
        if self.generator is None:
            messagebox.showwarning("Nada para salvar", "Gere o QR Code antes de salvar.")
            return

        directory = filedialog.askdirectory(title="Escolher pasta de destino", initialdir=str(OUTPUT_DIR))
        if not directory:
            return

        filename = ctk.CTkInputDialog(
            text="Nome do arquivo (sem extensão):", title="Nome do arquivo"
        ).get_input()
        if not filename:
            filename = "qrcode_app"

        try:
            results = self.generator.save(Path(directory), filename)
            files_list = "\n".join(f"- {fmt}: {path}" for fmt, path in results.items())
            messagebox.showinfo("QR Code salvo", f"Arquivos gerados:\n{files_list}")
            self._set_status(f"Arquivos salvos em: {directory}")
        except QRCodeGenerationError as exc:
            messagebox.showerror("Erro ao salvar", str(exc))
            logger.exception("Falha ao salvar QR Code")

    def _set_status(self, message: str) -> None:
        self.status_label.configure(text=message)


def launch_app() -> None:
    """Ponto de entrada para iniciar a interface gráfica."""
    app = QRCodeApp()
    app.mainloop()
