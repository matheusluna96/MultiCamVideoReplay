# 1) criar venv (opcional, mas recomendado)
python -m venv .venv
# Ativar:
#   Windows (PowerShell): .\.venv\Scripts\Activate.ps1
#   Windows (cmd):        .\.venv\Scripts\activate.bat
#   Linux/Mac:            source .venv/bin/activate

# 2) instalar em modo desenvolvimento
pip install -e .

# 3) executar (duas opções):
#   a) via console script instalado pelo pyproject:
dualcam-replay
#   b) via atalho Python:
python run.py
