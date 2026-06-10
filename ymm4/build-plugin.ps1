param([string]$YMM4DirPath = "")
$ErrorActionPreference = "Stop"
$project = Join-Path $PSScriptRoot "BouyomiUTAU.YMM4\BouyomiUTAU.YMM4.csproj"
$args = @("build", $project, "-c", "Release")
if ($YMM4DirPath) { $args += "-p:YMM4DirPath=$YMM4DirPath" }
dotnet @args
$out = Join-Path $PSScriptRoot "BouyomiUTAU.YMM4\bin\Release\net10.0-windows10.0.19041.0"
$package = Join-Path $PSScriptRoot "BouyomiUTAU-YMM4.ymme"
Compress-Archive -Path (Join-Path $out "BouyomiUTAU.YMM4.dll") -DestinationPath ($package + ".zip") -Force
Move-Item ($package + ".zip") $package -Force
Write-Host "作成しました: $package"
