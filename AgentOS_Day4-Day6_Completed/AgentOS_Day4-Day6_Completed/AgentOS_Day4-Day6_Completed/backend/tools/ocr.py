from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path


def extract_text_from_image(image_path: str | Path, timeout: float = 6.0) -> str:
    """
    Extracts text from an image using Windows native Universal Windows Platform (UWP) OCR.
    Works natively on Windows 10 & 11 without requiring pytesseract or external binary installs.
    Returns extracted text as a string (empty string if no text is present or on failure).
    """
    try:
        p = Path(image_path).resolve()
        if not p.is_file():
            return ""
        abs_path = str(p).replace("'", "''")

        ps_code = f"""
[Windows.Media.Ocr.OcrEngine, Windows.Foundation.UniversalApiContract, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation.UniversalApiContract, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{ $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }})[0]
function Await-Async($winRtTask, $type) {{
    $m = $asTaskGeneric.MakeGenericMethod($type)
    $t = $m.Invoke($null, @($winRtTask))
    $t.Wait(-1) | Out-Null
    return $t.Result
}}
try {{
    $file = Await-Async ([Windows.Storage.StorageFile]::GetFileFromPathAsync('{abs_path}')) ([Windows.Storage.StorageFile])
    $stream = Await-Async ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await-Async ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await-Async ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if (-not $engine) {{
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('en-US'))
    }}
    if ($engine) {{
        $res = Await-Async ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        if ($res -and $res.Text) {{
            Write-Output $res.Text
        }}
    }}
}} catch {{
    Write-Error $_
}}
"""
        encoded = base64.b64encode(ps_code.encode("utf-16le")).decode("ascii")
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return res.stdout.strip()
    except Exception:
        return ""
