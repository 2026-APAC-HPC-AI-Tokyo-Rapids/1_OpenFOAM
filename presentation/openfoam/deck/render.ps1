# Export slides of a pptx to PNG with PowerPoint itself (Windows, PowerPoint installed), for checking the deck by eye.
# usage (PowerShell): .\render.ps1 -Pptx <deck.pptx> -OutDir <dir> [-Width 1600] [-Slides "1,2,5"]
# from WSL: powershell.exe -File "$(wslpath -w render.ps1)" -Pptx "$(wslpath -w deck.pptx)" -OutDir 'C:\Users\<you>\AppData\Local\Temp\deck_png'
# PowerPoint cannot open paths longer than 255 characters, so the deck is first copied to a short path under %TEMP%.
param(
    [Parameter(Mandatory = $true)][string]$Pptx,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [int]$Width = 1600,
    [string]$Slides = ""
)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $OutDir | Out-Null
$copy = Join-Path $env:TEMP "render-deck.pptx"
Copy-Item -LiteralPath $Pptx -Destination $copy -Force
$app = New-Object -ComObject PowerPoint.Application
$open = $app.Presentations.Count
$pres = $app.Presentations.Open($copy, -1, 0, 0)
try {
    $height = [int]($Width * $pres.PageSetup.SlideHeight / $pres.PageSetup.SlideWidth)
    $list = if ($Slides -ne "") { $Slides.Split(",") | ForEach-Object { [int]$_ } } else { 1..$pres.Slides.Count }
    foreach ($i in $list) {
        $pres.Slides.Item($i).Export((Join-Path $OutDir ("slide-{0:D2}.png" -f $i)), "PNG", $Width, $height)
    }
    "exported $($list.Count) of $($pres.Slides.Count) slides to $OutDir"
}
finally {
    $pres.Close()
    if ($open -eq 0 -and $app.Presentations.Count -eq 0) { $app.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
    Remove-Item $copy -Force
}
