# QRCodeGenerator

Projeto Python (3.12+) que gera **um único QR Code** capaz de direcionar o
usuário para a **URL correta da loja de aplicativos** (Google Play para
Android, App Store para iOS) de acordo com o sistema operacional do
dispositivo que escaneou o código.

## ⚠️ Como funciona o redirecionamento (leia primeiro)

Um QR Code armazena **um único conteúdo**. Não existe forma de o próprio
código "escolher" entre duas URLs. A solução usada aqui é a padrão de
mercado:

1. O QR Code codifica a URL de uma **landing page** (página estática).
2. Essa página, ao ser aberta, executa um JavaScript que lê o
   `navigator.userAgent` do dispositivo e redireciona automaticamente:
   - Android → `ANDROID_URL`
   - iPhone/iPad → `IOS_URL`
   - Outro dispositivo → URL de fallback (padrão: a URL Android)
3. O arquivo pronto fica em `landing_page/index.html`. Você precisa
   **publicá-lo** em qualquer host estático gratuito (GitHub Pages,
   Netlify, Vercel, Cloudflare Pages, S3, etc.) e usar a URL pública
   resultante como o conteúdo do QR Code.

Resumo do fluxo: `Android URL + iOS URL` → gera `index.html` → você
hospeda → copia a URL publicada → gera o QR Code apontando para ela.

## Estrutura do projeto

```
QRCodeGenerator/
├── main.py                  # Ponto de entrada (GUI padrão + modo CLI)
├── gui.py                   # Interface gráfica (CustomTkinter, dark mode)
├── qr_generator.py          # Núcleo: geração/composição/exportação do QR Code
├── landing_page_builder.py  # Geração da landing page (HTML/JS) de redirecionamento
├── browser_preview.py       # Pré-visualização do QR Code no navegador padrão
├── utils.py                 # Funções auxiliares (validação, cores, imagens, logging)
├── config.py                # Dataclasses e constantes centrais
├── build_windows_exe.bat    # Script para gerar o executável Windows (.exe)
├── requirements.txt         # Dependências do projeto
├── requirements-build.txt   # Dependência extra apenas para gerar o .exe
├── README.md                # Este arquivo
├── LICENSE                  # Licença MIT
├── assets/                  # Coloque aqui logotipos de exemplo
├── output/                  # QR Codes exportados (PNG/SVG/PDF)
└── landing_page/            # index.html gerado (publicar em host estático)
```

## Requisitos

- Python 3.12 ou superior
- PyCharm (Community ou Professional)

## Instalação

### 1. Clonar/copiar o projeto e abrir no PyCharm

Abra a pasta `QRCodeGenerator/` no PyCharm como um novo projeto
(`File > Open...`).

### 2. Criar o ambiente virtual

No PyCharm: `File > Settings > Project: QRCodeGenerator > Python Interpreter
> Add Interpreter > Add Local Interpreter > Virtualenv Environment > New`,
selecionando Python 3.12+.

Ou via terminal:

```bash
python3.12 -m venv venv

# Ativar o ambiente virtual
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

## Execução no PyCharm

1. Abra `main.py`.
2. Clique com o botão direito no editor → **Run 'main'** (ou use o botão
   ▶️ no canto superior direito).
3. A interface gráfica (CustomTkinter, modo escuro) será aberta.

### Passo a passo na interface

1. Preencha **URL Android** e **URL iPhone**.
2. Clique em **"Gerar landing_page/index.html"**.
3. Publique a pasta `landing_page/` em um host estático (ex.: arraste a
   pasta no [Netlify Drop](https://app.netlify.com/drop) para um teste
   rápido e gratuito).
4. Cole a URL pública resultante no campo **"URL pública da landing page"**.
5. (Opcional) Selecione um logotipo (será redimensionado automaticamente
   para 300×300 px, mantendo transparência e centralização).
6. Ajuste cores, tamanho, margem, correção de erro e formatos de saída.
7. Clique em **"Gerar QR Code"** para pré-visualizar.
8. Clique em **"Salvar"**, escolha a pasta de destino e o nome do arquivo.

> Ao usar um logotipo, o nível de correção de erro é automaticamente
> ajustado para **H** (máximo), garantindo que o QR Code continue
> legível mesmo com parte da imagem coberta.

## Uso via linha de comando (CLI)

O `main.py` também aceita argumentos via `argparse`, útil para automação:

```bash
# Gerar apenas a landing page
python main.py --build-landing-page \
    --android-url "https://play.google.com/store/apps/details?id=com.exemplo" \
    --ios-url "https://apps.apple.com/app/id123456789"

# Gerar o QR Code (após publicar a landing page)
python main.py \
    --landing-url "https://meusite.netlify.app/" \
    --logo assets/logo.png \
    --dark-color "#1A1A2E" \
    --light-color "#FFFFFF" \
    --size 1200 \
    --border 4 \
    --error-correction H \
    --formats PNG SVG PDF \
    --output-dir output \
    --filename meu_app_qrcode
```

Parâmetros disponíveis: `--android-url`, `--ios-url`, `--landing-url`,
`--build-landing-page`, `--logo`, `--size`, `--border`,
`--error-correction {L,M,Q,H}`, `--dark-color`, `--light-color`,
`--formats {PNG,SVG,PDF}`, `--output-dir`, `--filename`.

## Gerando o executável Windows (.exe)

O projeto pode ser empacotado em um **único arquivo `.exe` portátil**, que roda em qualquer computador Windows **sem precisar instalar Python** — basta copiar o arquivo e dar duplo-clique.

> ⚠️ A geração do `.exe` precisa ser feita **rodando o script no próprio Windows** (não é possível gerar um `.exe` válido a partir de Linux/macOS).

### Passo a passo (uma única vez)

1. Abra o terminal do PyCharm (ou Prompt de Comando) na pasta do projeto, com o ambiente virtual ativo.
2. Instale a dependência de build:
   ```bash
   pip install -r requirements-build.txt
   ```
3. Execute o script:
   ```bash
   build_windows_exe.bat
   ```
4. Aguarde a compilação (alguns minutos). O executável final estará em:
   ```
   dist\QRCodeGenerator.exe
   ```
5. Copie `QRCodeGenerator.exe` para qualquer computador Windows — ele funciona sozinho, sem precisar de Python instalado.

### O que o `.exe` faz diferente da versão em código

- O executável detecta automaticamente que está "empacotado" e passa a salvar `output/` e `landing_page/` **na mesma pasta onde o `.exe` está**, em vez de uma pasta temporária (que seria apagada a cada execução).
- Antivírus podem, ocasionalmente, marcar executáveis gerados por PyInstaller como suspeitos (falso positivo comum, por não serem assinados digitalmente). Se isso ocorrer, adicione uma exceção ou assine o executável com um certificado, se sua instituição tiver um.

## Salvar em Imagens e pré-visualizar no navegador

Além do botão **"Salvar"** (que deixa você escolher a pasta), a interface tem o botão **"📂 Salvar em Imagens e Abrir no Navegador"**, que:

1. Salva o QR Code automaticamente na pasta **Imagens/Pictures** do usuário (`C:\Users\<seu-usuário>\Pictures`).
2. Mostra uma janela confirmando o caminho exato onde os arquivos foram salvos.
3. Abre uma página no navegador padrão do sistema exibindo o QR Code gerado.

Esse mesmo comportamento está disponível via linha de comando:

```bash
python main.py --landing-url "https://qrcodedinamicsenai.netlify.app" ^
    --save-to-pictures --open-browser --formats PNG
```



| Biblioteca      | Uso                                                                 |
|------------------|----------------------------------------------------------------------|
| `segno`          | Geração do QR Code em si (leve, sem dependências binárias, segue a especificação ISO/IEC 18004, suporta exportação nativa em PNG e SVG). |
| `Pillow`         | Composição do logotipo sobre o QR Code, controle de DPI (≥300) e exportação em PDF. |
| `customtkinter`  | Interface gráfica moderna, responsiva e com suporte nativo a modo escuro sobre o Tkinter. |
| `argparse`, `pathlib`, `logging`, `dataclasses`, `typing` | Bibliotecas padrão do Python usadas para CLI, manipulação de caminhos, logs, modelos de dados tipados e type hints. |

Nenhuma biblioteca adicional além das recomendadas foi necessária.

## Funcionalidades implementadas

- Geração de um único QR Code apontando para a landing page de redirecionamento.
- Geração automática da landing page com detecção de SO (Android/iOS/outro).
- Tamanho, margem (quiet zone) e nível de correção de erro configuráveis.
- Cores do QR Code e do fundo totalmente customizáveis (inclusive fundo transparente em PNG).
- Exportação em PNG, SVG e PDF, com resolução mínima de 300 DPI.
- Inserção de logotipo central (300×300 px), redimensionado automaticamente,
  com transparência preservada, centralização perfeita e correção de erro H forçada.
- Interface gráfica completa (CustomTkinter, dark mode) com pré-visualização
  do logotipo e do QR Code.
- Modo CLI completo via `argparse` para uso em scripts/automação.
- Tratamento de exceções, logging estruturado e tipagem completa (type hints).

## Observações técnicas

- O redimensionamento do logotipo usa `Image.Resampling.LANCZOS` (melhor
  qualidade) e é colado sobre um fundo branco arredondado para garantir
  contraste e legibilidade do QR Code.
- A área máxima ocupada pelo logotipo é limitada a ~22% da largura do QR
  Code (`DEFAULT_LOGO_RATIO` em `config.py`), valor seguro para manter a
  leitura mesmo com correção de erro H.
- Para arquivos SVG com logotipo, a imagem é embutida como `<image>`
  em base64 diretamente no XML do SVG, mantendo um único arquivo vetorial autossuficiente.
