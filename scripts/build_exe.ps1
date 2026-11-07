$ErrorActionPreference = "Stop"
pyinstaller --noconfirm --clean --noconsole --name SimuladorEpidemias --paths src src\epidemia\main.py
# Quando o aplicativo passar a ler dados (RNF10), acrescentar:
#   --add-data "data\processed;data\processed"
Write-Host "Executavel em dist\SimuladorEpidemias\SimuladorEpidemias.exe"
