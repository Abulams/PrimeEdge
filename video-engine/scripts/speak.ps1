param(
  [Parameter(Mandatory = $true)][string]$Text,
  [Parameter(Mandatory = $true)][string]$Out,
  [int]$Rate = -2
)

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = $Rate
$synth.Volume = 100

$preferred = @(
  "Microsoft Mark",
  "Microsoft David Desktop",
  "Microsoft David",
  "Microsoft Guy",
  "Microsoft Andrew"
)
$voices = $synth.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }
foreach ($name in $preferred) {
  if ($voices -contains $name) {
    $synth.SelectVoice($name)
    break
  }
}

$dir = Split-Path -Parent $Out
if (-not (Test-Path $dir)) {
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$escaped = [System.Security.SecurityElement]::Escape($Text)
$ssmlInner = $escaped -replace "\.\.\.", "<break time='280ms'/>"
$ratePct = if ($Rate -le -1) { "-4%" } elseif ($Rate -ge 1) { "+8%" } else { "+4%" }
$ssml = @"
<speak version='1.0' xml:lang='en-US'>
  <prosody rate='$ratePct' pitch='-1st'>
    $ssmlInner
  </prosody>
</speak>
"@

$synth.SetOutputToWaveFile($Out)
try {
  $synth.SpeakSsml($ssml)
} finally {
  $synth.Dispose()
}
