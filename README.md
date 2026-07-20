# QRCodeGenerator

Projeto Python (3.12+) que gera **um único QR Code** capaz de direcionar o
usuário para a **URL correta da loja de aplicativos** (Google Play para
Android, App Store para iOS) de acordo com o sistema operacional do
dispositivo que escaneou o código — com personalização visual completa
(cores, degradê, logotipo, legenda, cantos arredondados) e exportação em
PNG, SVG e PDF em alta resolução.

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

> **Dica de hospedagem gratuita:** para testes rápidos ou campanhas
> curtas (ex.: 30 dias), o [Netlify Drop](https://app.netlify.com/drop)
> funciona sem cadastro complexo — arraste a pasta `landing_page/` e
> pronto. O plano gratuito não expira e não deve estourar limite de uso
> para o volume de scans de um QR Code institucional comum.

## Estrutura do projeto

```
QRCodeGenerator/
├── main.py                  # Ponto de entrada (GUI padrão + modo CLI)
├── gui.py                   # Interface gráfica (CustomTkinter, dark mode, responsiva)
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
├── .gitignore                # Arquivos/pastas ignorados pelo Git
├── .gitattributes             # Normalização de finais de linha (LF/CRLF)
├── assets/                  # Coloque aqui logotipos de exemplo
├── output/                  # QR Codes exportados (PNG/SVG/PDF)
└── landing_page/            # index.html gerado (publicar em host estático)
```

## Requisitos

- Python 3.12 ou superior
- PyCharm (Community ou Professional)
- Windows, macOS ou Linux (o executável `.exe` é específico para Windows)

---

## 1. Instalação

### 1.1. Obter o projeto

Baixe/extraia o projeto (ou clone o repositório Git) para uma pasta local,
por exemplo `C:\Users\<usuário>\PycharmProjects\QRCodeGenerator`.

> **Importante:** se você já tinha uma versão antiga do projeto na mesma
> pasta, é mais seguro **apagar a pasta inteira e extrair tudo de novo**
> a partir do zip mais recente, em vez de copiar arquivo por arquivo.
> Isso evita erros de `ModuleNotFoundError` ou `ImportError` causados por
> arquivos antigos misturados com os novos.

### 1.2. Abrir no PyCharm

`File > Open...` e selecione a pasta `QRCodeGenerator/`.

### 1.3. Criar o ambiente virtual

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

### 1.4. Instalar as dependências

```bash
pip install -r requirements.txt
```

Isso instala `segno`, `Pillow` e `customtkinter`.

---

## 2. Execução no PyCharm

1. Abra `main.py`.
2. Clique com o botão direito no editor → **Run 'main'** (ou use o botão
   ▶️ no canto superior direito).
3. A interface gráfica (CustomTkinter, modo escuro, responsiva) será aberta.

### Passo a passo na interface

1. Preencha **URL Android** e **URL iPhone** (confira que não estão
   trocadas — a URL Android deve ser do Google Play, a do iPhone da
   App Store).
2. Clique em **"Gerar landing_page/index.html"**.
3. Publique a pasta `landing_page/` em um host estático (Netlify Drop,
   GitHub Pages, Vercel, etc.).
4. Cole a URL pública resultante no campo **"URL pública da landing page"**
   — é essa URL que será codificada no QR Code.
5. *(Opcional)* Clique em **"🎨 Aplicar cores do SENAI"** para já deixar
   tudo no padrão visual oficial (azul → laranja em degradê, legenda
   branca, cantos arredondados). Veja a seção
   [Paleta e preset do SENAI](#paleta-e-preset-do-senai) para detalhes.
6. *(Opcional)* Selecione um logotipo — é redimensionado automaticamente
   para 300×300 px, com recorte automático de margens vazias, mantendo
   transparência e centralização perfeita.
7. *(Opcional)* Escreva um texto de legenda (ex.: "Aponte a Câmera"),
   escolha a cor do texto.
8. *(Opcional, experimental)* Marque "Personalizar 'olhos' com S do
   SENAI" — veja o aviso de cautela na seção correspondente abaixo.
9. Ajuste tamanho, margem (quiet zone), correção de erro e formatos de
   exportação (PNG/SVG/PDF).
10. Clique em **"Gerar QR Code"** para pré-visualizar.
11. Salve de duas formas:
    - **"Salvar"** → escolhe a pasta de destino manualmente.
    - **"📂 Salvar em Imagens e Abrir no Navegador"** → salva direto na
      pasta Imagens/Pictures do usuário, confirma o caminho numa janela,
      e abre uma pré-visualização no navegador padrão.

> Ao usar um logotipo, o nível de correção de erro é automaticamente
> ajustado para **H** (máximo), garantindo que o QR Code continue
> legível mesmo com parte da imagem coberta.

---

## 3. Uso via linha de comando (CLI)

O `main.py` também aceita argumentos via `argparse`, útil para automação:

```bash
# Gerar apenas a landing page
python main.py --build-landing-page \
    --android-url "https://play.google.com/store/apps/details?id=com.exemplo" \
    --ios-url "https://apps.apple.com/app/id123456789"

# Gerar o QR Code completo (após publicar a landing page), com o visual do SENAI
python main.py \
    --landing-url "https://meusite.netlify.app/" \
    --logo assets/logo.png \
    --dark-color "#164194" \
    --light-color "#FFFFFF" \
    --gradient-end-color "#EF4910" \
    --gradient-direction diagonal \
    --caption-text "Aponte a Câmera" \
    --caption-color "#FFFFFF" \
    --caption-position top \
    --size 1200 \
    --border 4 \
    --error-correction H \
    --formats PNG SVG PDF \
    --save-to-pictures \
    --open-browser \
    --filename meu_app_qrcode
```

### Todos os parâmetros disponíveis

| Parâmetro | Descrição |
|---|---|
| `--android-url` | URL da Google Play |
| `--ios-url` | URL da App Store |
| `--landing-url` | URL pública já publicada da landing page (o que vai no QR Code) |
| `--build-landing-page` | Gera apenas o `landing_page/index.html` |
| `--logo` | Caminho para o logotipo (opcional) |
| `--size` | Tamanho do QR Code em pixels (padrão: 1000) |
| `--border` | Margem/quiet zone em módulos (padrão: 4) |
| `--error-correction {L,M,Q,H}` | Nível de correção de erro (padrão: M; force H se houver logo) |
| `--dark-color` | Cor dos módulos do QR Code (hex) |
| `--light-color` | Cor de fundo (hex, ou `transparent`) |
| `--gradient-end-color` | Se definido, aplica degradê de `--dark-color` até esta cor |
| `--gradient-direction {diagonal,horizontal,vertical}` | Direção do degradê (padrão: diagonal) |
| `--caption-text` | Texto da legenda (ex.: "Aponte a Câmera") |
| `--caption-color` | Cor do texto da legenda (padrão: branco) |
| `--caption-position {top,bottom}` | Posição da faixa de legenda (padrão: top) |
| `--eye-mark` | Caractere no centro dos 3 marcadores de posição (ex.: "S") — experimental |
| `--no-rounded-corners` | Desativa cantos arredondados e borda (estilo cartão vem ativado por padrão) |
| `--formats {PNG,SVG,PDF}` | Formatos de exportação (pode combinar vários) |
| `--output-dir` | Diretório de saída (padrão: `output/`) |
| `--save-to-pictures` | Salva na pasta Imagens/Pictures do usuário (ignora `--output-dir`) |
| `--open-browser` | Abre uma pré-visualização no navegador padrão após salvar |
| `--filename` | Nome do arquivo, sem extensão |

---

## 4. Gerando o executável Windows (.exe)

O projeto pode ser empacotado em um **único arquivo `.exe` portátil**, que
roda em qualquer computador Windows **sem precisar instalar Python** —
basta copiar o arquivo e dar duplo-clique.

> ⚠️ A geração do `.exe` precisa ser feita **rodando o script no próprio
> Windows** (não é possível gerar um `.exe` válido a partir de
> Linux/macOS — não existe compilação cruzada confiável para isso).

### Passo a passo (uma única vez)

1. Abra o terminal do PyCharm (ou Prompt de Comando) na pasta do
   projeto, com o ambiente virtual ativo.
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
5. Copie `QRCodeGenerator.exe` para qualquer computador Windows — ele
   funciona sozinho, sem precisar de Python instalado.

### O que o `.exe` faz diferente da versão em código

- O executável detecta automaticamente que está "empacotado" (via
  `sys.frozen`) e passa a salvar `output/` e `landing_page/` **na mesma
  pasta onde o `.exe` está**, em vez de uma pasta temporária do
  PyInstaller (que seria apagada a cada execução).
- Antivírus podem, ocasionalmente, marcar executáveis gerados por
  PyInstaller como suspeitos (falso positivo comum, por não serem
  assinados digitalmente). Se isso ocorrer, adicione uma exceção ou
  assine o executável com um certificado, se sua instituição tiver um.

---

## 5. Todas as funcionalidades

### Geração e redirecionamento
- QR Code único apontando para uma landing page com detecção automática
  de sistema operacional (Android/iOS/outro), gerada junto com o projeto.
- Correção de erro configurável (L/M/Q/H), forçada para H automaticamente
  quando há logotipo ou marcadores de posição personalizados.
- Tamanho e margem (quiet zone) configuráveis.
- Exportação em PNG, SVG (vetorial) e PDF, com resolução mínima de 300 DPI.

### Personalização visual
- **Cores** do QR Code e do fundo totalmente customizáveis (inclusive
  fundo transparente em PNG).
- **Degradê**: os módulos escuros do QR Code podem ter um gradiente de
  cor (ex.: azul → laranja), em vez de cor sólida, nas direções
  diagonal, horizontal ou vertical — implementado tanto no PNG (módulo a
  módulo) quanto no SVG (`<linearGradient>` nativo).
- **Logotipo central** (até 300×300 px): redimensionado automaticamente,
  com **recorte automático de margens vazias** (se a imagem original tiver
  bastante espaço em branco ao redor do desenho, o conteúdo é ampliado
  para preencher melhor o espaço), mantendo transparência e centralização
  perfeita. Fundo branco com cantos arredondados atrás do logo, sem
  margem extra.
- **Legenda de texto** (ex.: "Aponte a Câmera"), com faixa colorida no
  topo ou embaixo do QR Code, cor de texto e de fundo configuráveis, e
  **fonte com suporte completo a acentuação em português** (Arial/Segoe UI
  no Windows, com fallback para DejaVu Sans/Liberation Sans/Helvetica —
  a fonte padrão embutida do Pillow não é usada a menos que nenhuma
  dessas esteja disponível, pois ela não cobre bem caracteres acentuados
  como "â", "ç", "ã").
- **Estilo cartão**: cantos arredondados + borda colorida envolvendo todo
  o QR Code (com ou sem legenda), ativado por padrão e desativável.
- **Marcadores de posição personalizados** ("olhos"): opção experimental
  de substituir o quadrado central dos 3 marcadores por um caractere
  (ex.: "S" do SENAI), preservando os anéis externos (usados pelos
  leitores de QR Code para localizar e alinhar o código). **Teste sempre
  em múltiplos celulares antes de imprimir em grande escala** — essa
  personalização não é protegida por correção de erro.

### Interface e produtividade
- Interface gráfica completa (CustomTkinter, modo escuro), **responsiva**
  — a pré-visualização se redimensiona dinamicamente com a janela, com
  um teto de tamanho para nunca dominar a tela.
- Botão de atalho **"🎨 Aplicar cores do SENAI"**, que configura cor,
  degradê e legenda no padrão visual oficial de uma só vez.
- **Salvar em Imagens e Abrir no Navegador**: salva automaticamente na
  pasta Imagens/Pictures do usuário, confirma o caminho salvo numa
  janela, e abre uma pré-visualização no navegador padrão do sistema.
- Modo CLI completo via `argparse` para uso em scripts/automação.
- Executável Windows (`.exe`) portátil, sem necessidade de Python
  instalado na máquina de destino.
- Tratamento de exceções, logging estruturado e tipagem completa (type
  hints) em todo o projeto.

---

## Paleta e preset do SENAI

Cores oficiais usadas (Manual de Marcas do Sistema Indústria — CNI/SESI/
SENAI/IEL, versão 2024):

| Cor | Hex | Pantone |
|---|---|---|
| Azul SENAI | `#164194` | 293 C |
| Laranja SENAI | `#EF4910` | Orange 021 C |

O botão **"🎨 Aplicar cores do SENAI"** configura automaticamente:
- QR Code com degradê diagonal azul (`#164194`) → laranja (`#EF4910`)
- Fundo branco
- Legenda "Aponte a Câmera" em texto branco, faixa no topo
- Cantos arredondados + borda azul (estilo cartão)

---

## Bibliotecas utilizadas e justificativa

| Biblioteca | Uso |
|---|---|
| `segno` | Geração do QR Code em si (leve, sem dependências binárias, segue a especificação ISO/IEC 18004, suporta exportação nativa em PNG e SVG). A matriz de módulos também é usada diretamente para o modo degradê. |
| `Pillow` | Composição do logotipo, legenda, degradê, efeito cartão sobre o QR Code, controle de DPI (≥300) e exportação em PDF. |
| `customtkinter` | Interface gráfica moderna, responsiva e com suporte nativo a modo escuro sobre o Tkinter. |
| `pyinstaller` (apenas build) | Empacotamento do projeto em um executável Windows portátil. |
| `argparse`, `pathlib`, `logging`, `dataclasses`, `typing`, `webbrowser`, `tempfile`, `datetime`, `re`, `base64` | Bibliotecas padrão do Python usadas para CLI, manipulação de caminhos, logs, modelos de dados tipados, geração de HTML de pré-visualização, manipulação de SVG/XML, etc. |

Nenhuma biblioteca adicional além das recomendadas originalmente foi
necessária — as funcionalidades de degradê, cartão e legenda foram
implementadas com `Pillow` puro (sem dependências externas novas).

---

## Observações técnicas

- O redimensionamento do logotipo usa `Image.Resampling.LANCZOS` (melhor
  qualidade), com recorte automático de bordas vazias antes de
  redimensionar (via detecção de canal alfa ou de cor de fundo sólida).
- A área máxima ocupada pelo logotipo é limitada a ~22% da largura do QR
  Code (`DEFAULT_LOGO_RATIO` em `config.py`), valor seguro para manter a
  leitura mesmo com correção de erro H.
- Para arquivos SVG com logotipo, a imagem é embutida como `<image>` em
  base64 diretamente no XML do SVG, mantendo um único arquivo vetorial
  autossuficiente.
- O degradê no PNG é renderizado módulo a módulo (sem usar o
  renderizador padrão do segno), interpolando linearmente a cor RGB de
  cada módulo escuro conforme sua posição na matriz.
- O efeito "cartão" (cantos arredondados + borda) sempre **expande** a
  imagem para acomodar a borda, nunca corta/sobrepõe o QR Code ou a
  legenda.
- Quando empacotado como `.exe` (detecção via `sys.frozen`), os
  diretórios de saída (`output/`, `landing_page/`) passam a apontar para
  a pasta onde o executável está, em vez da pasta temporária de extração
  do PyInstaller.

---

## Solução de problemas comuns

**`ModuleNotFoundError` ou `ImportError` ao rodar `main.py`**
Geralmente indica que um dos arquivos do projeto está desatualizado (uma
versão antiga misturada com arquivos novos). Feche o projeto no PyCharm,
apague a pasta local do projeto e extraia novamente o `.zip` mais recente
por completo, em vez de copiar arquivos individualmente.

**Acentos aparecendo como caixa/quadrado no texto da legenda**
Corrigido a partir da versão com fallback de fontes reais do sistema
(Arial/Segoe UI/DejaVu Sans). Se ainda ocorrer, verifique se seu Windows
tem a fonte Arial instalada (é padrão em praticamente todas as
instalações).

**QR Code não abre a loja correta em algum celular**
Confira se as URLs de Android e iOS não estão trocadas nos campos da
interface, e se a landing page publicada foi **atualizada** após
qualquer correção (republique no seu host, ex.: Netlify).

**Pré-visualização muito grande ou cortada na interface**
A pré-visualização tem um teto de tamanho (560 px) e se redimensiona
dinamicamente com a janela — isso não afeta a qualidade/resolução do
arquivo final salvo, que segue o valor definido no campo "Tamanho (px)".
