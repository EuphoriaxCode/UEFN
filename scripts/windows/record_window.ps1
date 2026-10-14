# Record a window to numbered JPEG frames with PrintWindow (works while the window is behind others).
#   powershell -File record_window.ps1 -Process UnrealEditorFortnite-Win64-Shipping -Dir C:\tmp\rec -Seconds 10 -Fps 30
# Frames are named f_00000.jpg ...; frames.txt lists each frame's capture time (s) for exact re-timing later.
param(
  [string]$Process = "UnrealEditorFortnite-Win64-Shipping",
  [string]$Dir = "$env:TEMP\rec",
  [double]$Seconds = 5,
  [double]$Fps = 30,
  [int]$Quality = 92,
  [string]$StopFile = ""
)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class RW {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
"@
[RW]::SetProcessDPIAware() | Out-Null
$p = Get-Process -Name $Process -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $p) { Write-Output "no window for $Process"; exit 1 }
$hwnd = $p.MainWindowHandle
New-Item -ItemType Directory -Force -Path $Dir | Out-Null
$enc = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" }
$ep = New-Object System.Drawing.Imaging.EncoderParameters 1
$ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality), ([long]$Quality)
$r = New-Object RW+RECT
[RW]::GetWindowRect($hwnd, [ref]$r) | Out-Null
$w = $r.R - $r.L; $h = $r.B - $r.T
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$times = New-Object System.Collections.Generic.List[string]
$i = 0
$step = 1.0 / $Fps
while ($sw.Elapsed.TotalSeconds -lt $Seconds) {
  if ($StopFile -and (Test-Path $StopFile)) { break }
  $t = $sw.Elapsed.TotalSeconds
  $hdc = $g.GetHdc()
  [RW]::PrintWindow($hwnd, $hdc, 2) | Out-Null
  $g.ReleaseHdc($hdc)
  $bmp.Save((Join-Path $Dir ("f_{0:D5}.jpg" -f $i)), $enc, $ep)
  $times.Add($t.ToString("F4", [System.Globalization.CultureInfo]::InvariantCulture))
  $i++
  $next = ($i * $step)
  $wait = $next - $sw.Elapsed.TotalSeconds
  if ($wait -gt 0) { Start-Sleep -Milliseconds ([int]($wait * 1000)) }
}
$times | Set-Content -Path (Join-Path $Dir "frames.txt")
Write-Output ("{0} frames in {1:F1}s ({2:F1} fps) {3}x{4}" -f $i, $sw.Elapsed.TotalSeconds, ($i / $sw.Elapsed.TotalSeconds), $w, $h)
