param(
    [string]$Blender45 = "D:\blplugin\blendertestversion\4.5\blender-4.5.12-windows-x64\blender.exe",
    [string]$Blender50 = "D:\blplugin\blendertestversion\5.0\blender-5.0.1-windows-x64\blender.exe",
    [string]$Blender52 = "D:\blplugin\blendertestversion\5.2\blender-5.2.0-windows-x64\blender.exe",
    [switch]$SkipTests,
    [switch]$FullRenderMatrix
)

$ErrorActionPreference = "Stop"
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$manifestPath = Join-Path $projectRoot "collection_mask_exporter\blender_manifest.toml"
$manifest = Get-Content -LiteralPath $manifestPath -Raw
$versionMatch = [regex]::Match($manifest, '(?m)^version\s*=\s*"([^"]+)"')
if (-not $versionMatch.Success) {
    throw "Unable to read extension version from $manifestPath"
}
$version = $versionMatch.Groups[1].Value
$dist = Join-Path $projectRoot "dist"
$package = Join-Path $dist "collection_mask_exporter-$version.zip"
$release = Join-Path $dist "collection_mask_exporter-$version-release.zip"
$checksums = Join-Path $dist "collection_mask_exporter-$version-SHA256.txt"

function Invoke-Blender {
    param([string]$Executable, [string[]]$Arguments)
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        throw "Blender executable not found: $Executable"
    }
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Blender exited with code $LASTEXITCODE`: $Executable $Arguments"
    }
}

$matrix = @(
    @{ Label = "4.5"; Exe = $Blender45 },
    @{ Label = "5.0"; Exe = $Blender50 },
    @{ Label = "5.2"; Exe = $Blender52 }
)

Push-Location $projectRoot
try {
    if (-not $SkipTests) {
        foreach ($entry in $matrix) {
            Write-Host "== Core $($entry.Label) =="
            Invoke-Blender $entry.Exe @(
                "--background", "--factory-startup", "--python", "tests\run_core_tests.py"
            )
            Write-Host "== Translation $($entry.Label) =="
            Invoke-Blender $entry.Exe @(
                "--background", "--factory-startup", "--python", "tests\run_translation_tests.py"
            )
            Write-Host "== Panel $($entry.Label) =="
            Invoke-Blender $entry.Exe @(
                "--background", "--factory-startup", "--python", "tests\run_panel_api_tests.py"
            )
            Write-Host "== CLI $($entry.Label) =="
            Invoke-Blender $entry.Exe @(
                "--background", "--factory-startup", "--python", "tests\run_cli_tests.py"
            )
            Write-Host "== Sample project $($entry.Label) =="
            Invoke-Blender $entry.Exe @(
                "--factory-startup", "examples\CMask_Demo.blend", "--background", "--python",
                "tests\run_sample_project_tests.py"
            )
            if ($FullRenderMatrix) {
                Write-Host "== Full render $($entry.Label) =="
                Invoke-Blender $entry.Exe @(
                    "--background", "--factory-startup", "--python", "tests\run_render_tests.py"
                )
            }
        }
        foreach ($entry in $matrix | Where-Object { $_.Label -ne "4.5" }) {
            Write-Host "== Dynamic GN $($entry.Label) =="
            Invoke-Blender $entry.Exe @(
                "--background", "--factory-startup", "--python",
                "tests\run_dynamic_geometry_tests.py"
            )
        }
    }

    New-Item -ItemType Directory -Path $dist -Force | Out-Null
    Invoke-Blender $Blender52 @(
        "--command", "extension", "validate", "collection_mask_exporter"
    )
    Invoke-Blender $Blender52 @(
        "--command", "extension", "build", "--source-dir",
        "collection_mask_exporter", "--output-dir", "dist"
    )
    foreach ($entry in $matrix) {
        Invoke-Blender $entry.Exe @(
            "--command", "extension", "validate", $package
        )
    }

    $oldConfig = $env:BLENDER_USER_CONFIG
    $oldScripts = $env:BLENDER_USER_SCRIPTS
    foreach ($entry in $matrix) {
        $smokeRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
            "cmask-smoke-$($entry.Label)-" + [guid]::NewGuid().ToString("N")
        )
        try {
            Write-Host "== Clean install $($entry.Label) =="
            $env:BLENDER_USER_CONFIG = Join-Path $smokeRoot "config"
            $env:BLENDER_USER_SCRIPTS = Join-Path $smokeRoot "scripts"
            New-Item -ItemType Directory -Path $env:BLENDER_USER_CONFIG -Force | Out-Null
            New-Item -ItemType Directory -Path $env:BLENDER_USER_SCRIPTS -Force | Out-Null
            Invoke-Blender $entry.Exe @(
                "--command", "extension", "install-file", "-r", "user_default",
                "-e", $package
            )
            Invoke-Blender $entry.Exe @(
                "--background", "--python", "scripts\smoke_installed_extension.py"
            )
        }
        finally {
            $env:BLENDER_USER_CONFIG = $oldConfig
            $env:BLENDER_USER_SCRIPTS = $oldScripts
            if (Test-Path -LiteralPath $smokeRoot) {
                [System.IO.Directory]::Delete($smokeRoot, $true)
            }
        }
    }

    $stage = Join-Path ([System.IO.Path]::GetTempPath()) (
        "cmask-release-" + [guid]::NewGuid().ToString("N")
    )
    try {
        New-Item -ItemType Directory -Path $stage | Out-Null
        Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $stage
        Copy-Item -LiteralPath (Join-Path $projectRoot "CHANGELOG.md") -Destination $stage
        Copy-Item -LiteralPath (Join-Path $projectRoot "LICENSE") -Destination $stage
        Copy-Item -LiteralPath (Join-Path $projectRoot "THIRD_PARTY_LICENSES.md") -Destination $stage
        Copy-Item -LiteralPath (Join-Path $projectRoot "docs") -Destination $stage -Recurse
        Copy-Item -LiteralPath (Join-Path $projectRoot "examples") -Destination $stage -Recurse
        $stageDist = Join-Path $stage "dist"
        New-Item -ItemType Directory -Path $stageDist | Out-Null
        Copy-Item -LiteralPath $package -Destination $stageDist
        if (Test-Path -LiteralPath $release) {
            [System.IO.File]::Delete($release)
        }
        Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $release -CompressionLevel Optimal
    }
    finally {
        if (Test-Path -LiteralPath $stage) {
            [System.IO.Directory]::Delete($stage, $true)
        }
    }

    $packageHash = (Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash
    $releaseHash = (Get-FileHash -LiteralPath $release -Algorithm SHA256).Hash
    @(
        "$packageHash  $([System.IO.Path]::GetFileName($package))",
        "$releaseHash  $([System.IO.Path]::GetFileName($release))"
    ) | Set-Content -LiteralPath $checksums -Encoding ASCII

    Write-Host "Release complete"
    Write-Host $package
    Write-Host $release
    Write-Host $checksums
}
finally {
    Pop-Location
}
