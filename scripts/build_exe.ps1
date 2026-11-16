$ErrorActionPreference = "Stop"

$addDataArgs = @()
$processedDir = "data\processed"

# Adiciona data/processed condicionalmente à existência de arquivos de dados (RNF10)
if ((Test-Path $processedDir) -and (Get-ChildItem -Path $processedDir -File | Where-Object { $_.Name -ne ".gitkeep" })) {
    Write-Host "Incluindo dados de $processedDir no pacote executavel..."
    $addDataArgs += "--add-data", "${processedDir};${processedDir}"
} else {
    Write-Host "Nenhum arquivo de dados processados encontrado em $processedDir (M4 pendente). Prosseguindo sem --add-data."
}

pyinstaller --noconfirm --clean --noconsole --name SimuladorEpidemias --paths src @addDataArgs src\epidemia\main.py
if ($LASTEXITCODE -ne 0) {
    throw "Falha na compilacao com PyInstaller (codigo de saida: $LASTEXITCODE)."
}

Write-Host "Executavel gerado em dist\SimuladorEpidemias\SimuladorEpidemias.exe"
