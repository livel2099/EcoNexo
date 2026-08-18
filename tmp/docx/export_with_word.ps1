$ErrorActionPreference = 'Stop'

$docPath = (Resolve-Path 'output\docx\Respuestas_Simulacro_EcoNexo_INTA_Misiones.docx').Path
$renderDir = Join-Path (Resolve-Path 'tmp\docx').Path 'rendered-word'
New-Item -ItemType Directory -Force -Path $renderDir | Out-Null
$pdfPath = Join-Path $renderDir 'Respuestas_Simulacro_EcoNexo_INTA_Misiones.pdf'

$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $document = $word.Documents.Open($docPath, $false, $true, $false)
    $document.ExportAsFixedFormat($pdfPath, 17, $false, 0, 0, 1, 9999, 0, $true, $true, 0, $true, $true, $false)
    $document.Close($false)
    $document = $null
    $word.Quit()
    $word = $null
    Get-Item -LiteralPath $pdfPath | Select-Object FullName, Length
}
finally {
    if ($document -ne $null) {
        try { $document.Close($false) } catch {}
    }
    if ($word -ne $null) {
        try { $word.Quit() } catch {}
    }
}
