# 1) criar venv (opcional, mas recomendado)
python -m venv .venv

# 2) instalar em modo desenvolvimento
pip install -e .

# 3) executar (duas opções):
##   a) via console script instalado pelo pyproject:
dualcam-replay
##   b) via atalho Python:
python run.py
