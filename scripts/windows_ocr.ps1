param(
    [Parameter(Mandatory = $true)]
    [string]$ImagePath,
    [ValidateSet('ru', 'en-US')]
    [string]$Language = 'ru',
    [int]$CropX = 0,
    [int]$CropY = 0,
    [int]$CropWidth = 0,
    [int]$CropHeight = 0,
    [ValidateRange(1, 4)]
    [int]$Scale = 1
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.FileAccessMode, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.IRandomAccessStream, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

$asTaskMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 } |
    Select-Object -First 1

function Await-WinRt {
    param($Operation, [Type]$ResultType)
    $task = $asTaskMethod.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.Wait()
    return $task.Result
}

$resolved = (Resolve-Path -LiteralPath $ImagePath).Path
$ocrPath = $resolved
$temporaryPath = $null
$sourceWidth = 0
$sourceHeight = 0

if ($CropWidth -gt 0 -or $CropHeight -gt 0 -or $Scale -gt 1) {
    Add-Type -AssemblyName System.Drawing
    $sourceImage = [System.Drawing.Bitmap]::new($resolved)
    try {
        $sourceWidth = $sourceImage.Width
        $sourceHeight = $sourceImage.Height
        if ($CropWidth -le 0) { $CropWidth = $sourceWidth - $CropX }
        if ($CropHeight -le 0) { $CropHeight = $sourceHeight - $CropY }
        if ($CropX -lt 0 -or $CropY -lt 0 -or
            $CropX + $CropWidth -gt $sourceWidth -or $CropY + $CropHeight -gt $sourceHeight) {
            throw 'OCR crop is outside the source image'
        }
        $target = [System.Drawing.Bitmap]::new($CropWidth * $Scale, $CropHeight * $Scale)
        try {
            $graphics = [System.Drawing.Graphics]::FromImage($target)
            try {
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $graphics.DrawImage(
                    $sourceImage,
                    [System.Drawing.Rectangle]::new(0, 0, $target.Width, $target.Height),
                    [System.Drawing.Rectangle]::new($CropX, $CropY, $CropWidth, $CropHeight),
                    [System.Drawing.GraphicsUnit]::Pixel
                )
            }
            finally { $graphics.Dispose() }
            $temporaryPath = Join-Path ([IO.Path]::GetTempPath()) ("fc24-ocr-{0}.png" -f [guid]::NewGuid())
            $target.Save($temporaryPath, [System.Drawing.Imaging.ImageFormat]::Png)
            $ocrPath = $temporaryPath
        }
        finally { $target.Dispose() }
    }
    finally { $sourceImage.Dispose() }
}

$file = Await-WinRt ([Windows.Storage.StorageFile]::GetFileFromPathAsync($ocrPath)) ([Windows.Storage.StorageFile])
$stream = Await-WinRt ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await-WinRt ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await-WinRt ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$languageObject = New-Object Windows.Globalization.Language($Language)
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($languageObject)
if ($null -eq $engine) { throw "Windows OCR language is unavailable: $Language" }
$result = Await-WinRt ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

$lines = foreach ($line in $result.Lines) {
    $words = foreach ($word in $line.Words) {
        [ordered]@{
            text = $word.Text
            x = [math]::Round($CropX + ($word.BoundingRect.X / $Scale), 2)
            y = [math]::Round($CropY + ($word.BoundingRect.Y / $Scale), 2)
            width = [math]::Round($word.BoundingRect.Width / $Scale, 2)
            height = [math]::Round($word.BoundingRect.Height / $Scale, 2)
        }
    }
    [ordered]@{ text = $line.Text; words = @($words) }
}

[ordered]@{
    path = $resolved
    language = $Language
    width = if ($sourceWidth) { $sourceWidth } else { [int]$decoder.PixelWidth }
    height = if ($sourceHeight) { $sourceHeight } else { [int]$decoder.PixelHeight }
    crop = [ordered]@{ x = $CropX; y = $CropY; width = $CropWidth; height = $CropHeight; scale = $Scale }
    text = $result.Text
    lines = @($lines)
} | ConvertTo-Json -Depth 6 -Compress

$stream.Dispose()
$bitmap.Dispose()
if ($temporaryPath) { Remove-Item -LiteralPath $temporaryPath -Force }
