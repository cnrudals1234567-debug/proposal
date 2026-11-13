# PPTX → 슬라이드별 PNG 미리보기 (PowerPoint 설치 필요)
# 사용: powershell -ExecutionPolicy Bypass -File tools\render_preview.ps1 -Pptx "<경로.pptx>" [-OutDir "<폴더>"]
param(
  [Parameter(Mandatory=$true)][string]$Pptx,
  [string]$OutDir
)
$Pptx = (Resolve-Path $Pptx).Path
if (-not $OutDir) { $OutDir = Join-Path (Split-Path $Pptx) ("preview_" + [IO.Path]::GetFileNameWithoutExtension($Pptx)) }
New-Item -ItemType Directory -Force $OutDir | Out-Null
$app = New-Object -ComObject PowerPoint.Application
try {
  $pres = $app.Presentations.Open($Pptx, $true, $false, $false)
  $i = 1
  foreach ($s in $pres.Slides) { $s.Export((Join-Path $OutDir ("slide_{0:D2}.png" -f $i)), "PNG", 1600, 900); $i++ }
  $pres.Close()
  "exported $($i-1) slides -> $OutDir"
} finally {
  # 사용자가 열어 둔 다른 프레젠테이션이 있으면 PowerPoint를 종료하지 않는다
  if ($app.Presentations.Count -eq 0) { $app.Quit() }
}
