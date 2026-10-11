#!/usr/bin/env pwsh
# Social Media Auto Content System - BETA 3
# Windows PowerShell / CMD UI
# FFMPEG FIXED - No hex color, using standard color names

param(
    [Parameter(Position=0)]
    [ValidateSet("generate", "batch", "schedule", "config", "status", "help", "interactive", "diagnostics")]
    [string]$Command = "help",
    
    [Parameter()]
    [string]$Template = "motivational",
    
    [Parameter()]
    [string]$Zodiac = "leo",
    
    [Parameter()]
    [string]$Text1 = "",
    
    [Parameter()]
    [string]$Text2 = "",
    
    [Parameter()]
    [string]$Text3 = "",
    
    [Parameter()]
    [string]$Text4 = "",
    
    [Parameter()]
    [string]$Text5 = "",
    
    [Parameter()]
    [string]$Caption = "",
    
    [Parameter()]
    [string]$Hashtags = "",
    
    [Parameter()]
    [string]$Keyword = "nature beautiful",
    
    [Parameter()]
    [string]$Music = "",
    
    [Parameter()]
    [string]$Output = "",
    
    [Parameter()]
    [string]$ConfigFile = "config.json",
    
    [Parameter()]
    [switch]$Interactive = $false
)

# ============ Configuration ============

$script:ConfigPath = Join-Path $PSScriptRoot $ConfigFile
$script:OutputDir = Join-Path $PSScriptRoot "outputs"
$script:AssetsDir = Join-Path $PSScriptRoot "assets"
$script:MusicDir = Join-Path $AssetsDir "music"
$script:LogsDir = Join-Path $PSScriptRoot "logs"

# Create directories if not exists
$dirs = @($OutputDir, $AssetsDir, $MusicDir, $LogsDir)
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) { 
        New-Item -ItemType Directory -Path $dir -Force | Out-Null 
    }
}

# Template configurations with STANDARD COLOR NAMES (not hex)
$script:Templates = @{
    "zodiac_dark" = @{
        fontsize = 52
        fontcolor = "gold"
        bordercolor = "black"
        borderw = 3
        shadow = "shadowcolor=black@0.5:shadowx=3:shadowy=3"
        box = "box=1:boxcolor=black@0.6:boxborderw=10"
    }
    "motivational" = @{
        fontsize = 48
        fontcolor = "white"
        bordercolor = "black"
        borderw = 2
        shadow = "shadowcolor=black@0.5:shadowx=2:shadowy=2"
        box = "box=1:boxcolor=black@0.5:boxborderw=10"
    }
    "educational" = @{
        fontsize = 44
        fontcolor = "lightblue"
        bordercolor = "black"
        borderw = 2
        shadow = "shadowcolor=black@0.5:shadowx=2:shadowy=2"
        box = "box=1:boxcolor=black@0.6:boxborderw=10"
    }
    "quote_simple" = @{
        fontsize = 46
        fontcolor = "white"
        bordercolor = "black"
        borderw = 2
        shadow = "shadowcolor=black@0.5:shadowx=2:shadowy=2"
        box = "box=1:boxcolor=black@0.4:boxborderw=15"
    }
    "tips_daily" = @{
        fontsize = 40
        fontcolor = "lime"
        bordercolor = "black"
        borderw = 2
        shadow = "shadowcolor=black@0.5:shadowx=2:shadowy=2"
        box = "box=1:boxcolor=black@0.5:boxborderw=10"
    }
}

# Zodiac colors - STANDARD COLOR NAMES for FFmpeg Windows compatibility
$script:ZodiacColors = @{
    "aries" = "red"
    "taurus" = "green"
    "gemini" = "gold"
    "cancer" = "lightblue"
    "leo" = "orange"
    "virgo" = "yellowgreen"
    "libra" = "hotpink"
    "scorpio" = "darkred"
    "sagittarius" = "saddlebrown"
    "capricorn" = "darkslategray"
    "aquarius" = "deepskyblue"
    "pisces" = "mediumpurple"
}

# Animations untuk teks
$script:Animations = @{
    "fade" = "alpha='if(lt(t,0.5), t/0.5, if(gt(5-t,0.5), 1, (5-t)/0.5))'"
    "zoom" = "fontsize='if(lt(t,0.5), 24 + (40*t/0.5), 64)'"
    "slide" = "x='if(lt(t,0.5), w + (w*t/0.5), w)'"
    "blink" = "alpha='if(mod(t,1), 1, 0.3)'"
}

# ============ Helper Functions ============

function Write-ColorText {
    param(
        [string]$Text,
        [string]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Color
}

function Show-Banner {
    Clear-Host
    Write-ColorText "============================================================" "Cyan"
    Write-ColorText "    SOCIAL MEDIA AUTO CONTENT SYSTEM - BETA 4" "Yellow"
    Write-ColorText "    Windows Command Line / PowerShell Interface" "Yellow"
    Write-ColorText "    FFMPEG Fixed | No Hex Colors | No Nuelink" "Yellow"
    Write-ColorText "============================================================" "Cyan"
    Write-Host ""
}

function Show-Menu {
    Write-ColorText "MAIN MENU:" "Green"
    Write-Host ""
    Write-Host "  1. Generate Single Video"
    Write-Host "  2. Batch Generate (Multiple Videos)"
    Write-Host "  3. Schedule Videos (Auto Post)"
    Write-Host "  4. View Configuration"
    Write-Host "  5. View Queue & History"
    Write-Host "  6. Cleanup Old Files"
    Write-Host "  7. Run Diagnostics"
    Write-Host "  8. Post to Social Media"
    Write-Host "  9. Help"
    Write-Host "  0. Exit"
    Write-Host ""
}

function Load-Config {
    if (Test-Path $script:ConfigPath) {
        try {
            $content = Get-Content $script:ConfigPath -Raw -ErrorAction SilentlyContinue
            if ($content) {
                return $content | ConvertFrom-Json
            }
        } catch {
            # Return default
        }
    }
    return $null
}

function Show-Config {
    Write-ColorText "`nCURRENT CONFIGURATION:" "Cyan"
    Write-Host ""
    Write-Host "TEMPLATES AVAILABLE:"
    Write-Host "  zodiac_dark    - Dark theme with gold text for zodiac"
    Write-Host "  motivational   - White text with black border"
    Write-Host "  educational    - Light blue text for tips"
    Write-Host "  quote_simple   - Simple quote style"
    Write-Host "  tips_daily     - Green text for daily tips"
    Write-Host ""
    Write-Host "ZODIAC COLORS (for zodiac_dark template):"
    $script:ZodiacColors.Keys | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
    Write-Host "Output Directory: $script:OutputDir"
    Write-Host "Music Directory: $script:MusicDir"
    Write-Host "Logs Directory: $script:LogsDir"
}

function Show-Help {
    Write-ColorText "`nSOCIAL MEDIA AUTO CONTENT - BETA 4 HELP" "Cyan"
    Write-Host ""
    Write-Host "USAGE:"
    Write-Host "  .\beta4_windows_cli.ps1 [command] [options]"
    Write-Host ""
    Write-Host "COMMANDS:"
    Write-Host "  generate       Generate a single video"
    Write-Host "  batch          Batch generate multiple videos from CSV"
    Write-Host "  schedule       Schedule videos for auto posting"
    Write-Host "  config         View configuration"
    Write-Host "  status         Show queue and history"
    Write-Host "  diagnostics    Run system diagnostics"
    Write-Host "  interactive    Launch interactive menu"
    Write-Host "  help           Show this help"
    Write-Host ""
    Write-Host "OPTIONS:"
    Write-Host "  -Template      Template name: zodiac_dark/motivational/educational/quote_simple/tips_daily"
    Write-Host "  -Zodiac        Zodiac sign: aries, taurus, gemini, cancer, leo, virgo, libra, scorpio, sagittarius, capricorn, aquarius, pisces"
    Write-Host "  -Text1 to -Text5  Text content lines (max 5 lines)"
    Write-Host "  -Keyword       Background video search keyword (not implemented, uses black background)"
    Write-Host "  -Music         Path to custom music file"
    Write-Host "  -Output        Output filename (without extension)"
    Write-Host ""
    Write-Host "EXAMPLES:"
    Write-Host "  .\beta4_windows_cli.ps1 interactive"
    Write-Host "  .\beta4_windows_cli.ps1 diagnostics"
    Write-Host "  .\beta4_windows_cli.ps1 generate -Template zodiac_dark -Zodiac leo -Text1 'Hello World' -Text2 'Test Video'"
    Write-Host "  .\beta4_windows_cli.ps1 generate -Text1 'Line 1' -Text2 'Line 2' -Text3 'Line 3'"
    Write-Host "  .\beta4_windows_cli.ps1 batch"
    Write-Host "  .\beta4_windows_cli.ps1 config"
    Write-Host "  .\beta4_windows_cli.ps1 status"
    Write-Host ""
    Write-Host "REQUIREMENTS:"
    Write-Host "  - FFmpeg must be installed and in PATH"
    Write-Host "  - Download from: https://ffmpeg.org/download.html"
    Write-Host "  - Add to PATH: C:\ffmpeg\bin"
    Write-Host ""
}

function Escape-FFmpegText {
    param([string]$Text)
    
    # Escape special characters for FFmpeg drawtext
    $escaped = $Text
    $escaped = $escaped -replace '\\', '\\\\'
    $escaped = $escaped -replace "'", "'\\''"
    $escaped = $escaped -replace ':', '\:'
    $escaped = $escaped -replace '=', '\='
    $escaped = $escaped -replace ';', '\;'
    $escaped = $escaped -replace '\[', '\\['
    $escaped = $escaped -replace '\]', '\\]'
    
    return $escaped
}

function Generate-Video {
    param(
        [string]$Template = "motivational",
        [string]$Zodiac = "leo",
        [string[]]$Texts,
        [string]$Keyword = "nature beautiful",
        [string]$MusicPath = "",
        [string]$OutputName = ""
    )
    
    if (-not $Texts -or $Texts.Count -eq 0) {
        Write-ColorText "No text provided!" "Red"
        return $null
    }
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $outputFile = if ($OutputName -ne "") { 
        "$OutputName.mp4" 
    } else { 
        "video_${timestamp}.mp4" 
    }
    $outputPath = Join-Path $OutputDir $outputFile
    
    Write-ColorText "`nGenerating video..." "Yellow"
    Write-Host "  Template: $Template"
    Write-Host "  Texts: $($Texts.Count) line(s)"
    Write-Host "  Output: $outputPath"
    
    # Get template configuration
    $templateConfig = $script:Templates[$Template]
    if (-not $templateConfig) {
        $templateConfig = $script:Templates["motivational"]
    }
    
    # Set text color based on zodiac if using zodiac_dark template
    $textColor = $templateConfig.fontcolor
    if ($Template -eq "zodiac_dark" -and $script:ZodiacColors.ContainsKey($Zodiac)) {
        $textColor = $script:ZodiacColors[$Zodiac]
        Write-Host "  Using zodiac color: $textColor for $Zodiac"
    }
    
    $durationPerText = 5
    $totalDuration = $Texts.Count * $durationPerText
    
    # Create temp directory for segments
    $tempDir = Join-Path $env:TEMP "video_gen_${timestamp}"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    
    $segmentFiles = @()
    $success = $true
    
    for ($i = 0; $i -lt $Texts.Count; $i++) {
        $segmentOutput = Join-Path $tempDir "segment_$i.mp4"
        $segmentFiles += $segmentOutput
        
        $escapedText = Escape-FFmpegText -Text $Texts[$i]
        
        # Build drawtext filter correctly
        # Format: drawtext=text='text':fontcolor=color:fontsize=size:x=X:y=Y
        $drawtextFilter = "drawtext=text='${escapedText}':fontcolor=${textColor}:fontsize=$($templateConfig.fontsize):x=(w-text_w)/2:y=(h-text_h)/2"
        
        # Add border
        $drawtextFilter += ":bordercolor=$($templateConfig.bordercolor):borderw=$($templateConfig.borderw)"
        
        # Add box background (semi-transparent)
        $drawtextFilter += ":box=1:boxcolor=black@0.5:boxborderw=10"
        
        # Add shadow
        $drawtextFilter += ":shadowcolor=black@0.5:shadowx=3:shadowy=3"
        
        Write-Host "  Rendering segment $($i+1)/$($Texts.Count): '$($Texts[$i].Substring(0, [Math]::Min(30, $Texts[$i].Length)))...'" -ForegroundColor Gray
        
        # FFmpeg command for one segment
        $segmentCmd = @(
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=$durationPerText",
            "-vf", $drawtextFilter,
            "-c:v", "libx264", "-preset", "ultrafast",
            "-t", $durationPerText.ToString(),
            "`"$segmentOutput`""
        ) -join " "
        
        $result = Invoke-Expression $segmentCmd 2>&1
        
        # Verify segment was created
        if (-not (Test-Path $segmentOutput)) {
            Write-ColorText "  FAILED: Could not create segment $($i+1)" "Red"
            Write-Host "  Error: $($result | Select-Object -Last 5)" -ForegroundColor Red
            $success = $false
            break
        }
        
        # Check file size (should be > 0)
        $segmentSize = (Get-Item $segmentOutput).Length
        if ($segmentSize -lt 1000) {
            Write-ColorText "  FAILED: Segment $($i+1) is too small ($segmentSize bytes)" "Red"
            $success = $false
            break
        }
    }
    
    if (-not $success) {
        Write-ColorText "[ERROR] Video generation failed during segment creation" "Red"
        Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        return $null
    }
    
    # Concatenate all segments
    Write-Host "Concatenating $($segmentFiles.Count) segments..." -ForegroundColor Gray
    
    # Create concat file list
    $concatFile = Join-Path $tempDir "concat.txt"
    $concatContent = ""
    foreach ($seg in $segmentFiles) {
        $concatContent += "file '$seg'`n"
    }
    $concatContent | Out-File -FilePath $concatFile -Encoding ASCII -Force
    
    $concatCmd = "ffmpeg -y -f concat -safe 0 -i `"$concatFile`" -c copy `"$outputPath`" 2>&1"
    Invoke-Expression $concatCmd
    
    # Add music if provided
    if ($MusicPath -and (Test-Path $MusicPath)) {
        Write-Host "Adding background music..." -ForegroundColor Gray
        
        $tempWithAudio = Join-Path $tempDir "with_audio.mp4"
        $audioCmd = "ffmpeg -y -i `"$outputPath`" -i `"$MusicPath`" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -shortest `"$tempWithAudio`" 2>&1"
        Invoke-Expression $audioCmd
        
        if (Test-Path $tempWithAudio) {
            Move-Item -Path $tempWithAudio -Destination $outputPath -Force
            Write-Host "  Music added successfully" -ForegroundColor Green
        }
    }
    
    # Cleanup temp files
    Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    
    if (Test-Path $outputPath) {
        $fileSize = [math]::Round((Get-Item $outputPath).Length / 1MB, 2)
        Write-ColorText "`n[SUCCESS] Video generated successfully!" "Green"
        Write-Host "  File: $outputPath"
        Write-Host "  Size: $fileSize MB"
        Write-Host "  Duration: $totalDuration seconds"
        return $outputPath
    } else {
        Write-ColorText "[ERROR] Video generation failed - output file not found" "Red"
        return $null
    }
}

function Batch-Generate {
    param([string]$CsvFile = "")
    
    if ($CsvFile -eq "") {
        Write-Host ""
        Write-ColorText "BATCH GENERATE MODE" "Cyan"
        Write-Host ""
        Write-Host "CSV format example:"
        Write-Host "  template,zodiac,text1,text2,text3,keyword"
        Write-Host "  zodiac_dark,leo,Leo Energy Today,Your confidence shines bright,Success is coming,sun golden"
        Write-Host "  motivational,,Believe in Yourself,Keep pushing forward,Success awaits,success motivation"
        Write-Host ""
        $csvPath = Read-Host "Enter CSV file path (or press Enter to use sample)"
        
        if ($csvPath -eq "") {
            $sampleCsv = Join-Path $PSScriptRoot "batch_sample.csv"
            $sampleContent = @'
template,zodiac,text1,text2,text3,keyword
zodiac_dark,leo,Leo Energy Today,Your confidence shines bright,Success is coming,sun golden
motivational,,Believe in Yourself,Keep pushing forward,Success awaits,success motivation
educational,,Tip 1: Be Consistent,Tip 2: Track Progress,Tip 3: Celebrate Wins,study tips
'@
            $sampleContent | Out-File -FilePath $sampleCsv -Encoding UTF8
            
            Write-ColorText "Sample CSV created at: $sampleCsv" "Yellow"
            $csvPath = $sampleCsv
        }
    } else {
        $csvPath = $CsvFile
    }
    
    if (-not (Test-Path $csvPath)) {
        Write-ColorText "CSV file not found: $csvPath" "Red"
        return
    }
    
    $batchData = Import-Csv $csvPath
    Write-ColorText "`nProcessing $($batchData.Count) videos..." "Yellow"
    
    $results = @()
    foreach ($row in $batchData) {
        $texts = @()
        if ($row.text1 -and $row.text1.Trim()) { $texts += $row.text1.Trim() }
        if ($row.text2 -and $row.text2.Trim()) { $texts += $row.text2.Trim() }
        if ($row.text3 -and $row.text3.Trim()) { $texts += $row.text3.Trim() }
        if ($row.text4 -and $row.text4.Trim()) { $texts += $row.text4.Trim() }
        if ($row.text5 -and $row.text5.Trim()) { $texts += $row.text5.Trim() }
        
        if ($texts.Count -gt 0) {
            Write-Host "`n[Row $($results.Count+1)] Generating: $($texts[0])..."
            $output = Generate-Video -Template $row.template -Zodiac $row.zodiac -Texts $texts -Keyword $row.keyword
            if ($output) {
                $results += $output
                Save-History -VideoPath $output -TextPreview $texts[0] -Template $row.template
            }
            # Small delay between videos
            Start-Sleep -Seconds 1
        }
    }
    
    Write-ColorText "`n[COMPLETE] Batch generation finished! Generated $($results.Count) videos" "Green"
}

function Save-History {
    param($VideoPath, $TextPreview, $Template)
    
    $historyFile = Join-Path $PSScriptRoot "history.json"
    $history = @()
    
    if (Test-Path $historyFile) {
        $content = Get-Content $historyFile -Raw -ErrorAction SilentlyContinue
        if ($content) {
            try {
                $history = $content | ConvertFrom-Json
            } catch {
                $history = @()
            }
        }
    }
    
    $newItem = @{
        date = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        video_path = $VideoPath
        text_preview = if ($TextPreview.Length -gt 50) { $TextPreview.Substring(0, 50) } else { $TextPreview }
        template = $Template
    }
    $history += $newItem
    
    # Keep last 100
    if ($history.Count -gt 100) {
        $history = $history | Select-Object -Last 100
    }
    
    $history | ConvertTo-Json -Depth 10 | Out-File -FilePath $historyFile -Encoding UTF8
}

function Show-History {
    $historyFile = Join-Path $PSScriptRoot "history.json"
    
    Write-ColorText "`nRECENT HISTORY:" "Cyan"
    Write-Host ""
    
    if (Test-Path $historyFile) {
        $content = Get-Content $historyFile -Raw -ErrorAction SilentlyContinue
        if ($content) {
            try {
                $history = $content | ConvertFrom-Json
                if ($history.Count -eq 0) {
                    Write-Host "  No history yet"
                } else {
                    $recentItems = $history | Select-Object -Last 10
                    foreach ($item in $recentItems) {
                        Write-Host "  $($item.date): $($item.text_preview)"
                        Write-Host "        File: $(Split-Path $item.video_path -Leaf)"
                        Write-Host ""
                    }
                }
            } catch {
                Write-Host "  Error reading history"
            }
        } else {
            Write-Host "  No history yet"
        }
    } else {
        Write-Host "  No history yet"
    }
}

function Show-Queue {
    Write-ColorText "`nAVAILABLE VIDEOS:" "Cyan"
    Write-Host ""
    
    $videos = Get-ChildItem $OutputDir -Filter "*.mp4" | Sort-Object LastWriteTime -Descending
    
    if ($videos.Count -eq 0) {
        Write-Host "  No videos found in $OutputDir"
    } else {
        foreach ($video in $videos) {
            $size = [math]::Round($video.Length / 1MB, 1)
            Write-Host "  $($video.Name) - $size MB - $($video.LastWriteTime.ToString('yyyy-MM-dd HH:mm'))"
        }
    }
}

function Cleanup-OldFiles {
    $keepDays = 7
    
    Write-ColorText "`nCleaning up files older than $keepDays days..." "Yellow"
    
    $cutoffDate = (Get-Date).AddDays(-$keepDays)
    $oldFiles = Get-ChildItem $OutputDir -Filter "*.mp4" | Where-Object { $_.LastWriteTime -lt $cutoffDate }
    
    if ($oldFiles.Count -eq 0) {
        Write-Host "No old files to delete"
    } else {
        foreach ($file in $oldFiles) {
            Write-Host "  Deleting: $($file.Name)"
            Remove-Item $file.FullName -Force -ErrorAction SilentlyContinue
        }
        Write-ColorText "Deleted $($oldFiles.Count) old files" "Green"
    }
}

function Post-To-Social {
    Write-ColorText "`nPOST TO SOCIAL MEDIA" "Cyan"
    Write-Host ""
    Write-Host "Available platforms:"
    Write-Host "  1. YouTube Shorts"
    Write-Host "  2. Instagram Reels"
    Write-Host "  3. Facebook Reels"
    Write-Host "  4. All Platforms (Manual upload)"
    Write-Host ""
    
    $choice = Read-Host "Choose platform (1-4)"
    $videoPath = Read-Host "Video path (or press Enter for latest)"
    
    if ($videoPath -eq "") {
        $latestVideo = Get-ChildItem $OutputDir -Filter "*.mp4" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latestVideo) {
            $videoPath = $latestVideo.FullName
            Write-Host "Using latest video: $videoPath"
        } else {
            Write-ColorText "No video found!" "Red"
            return
        }
    }
    
    $caption = Read-Host "Caption (optional)"
    $hashtags = Read-Host "Hashtags (optional)"
    
    Write-ColorText "`n[INFO] Social media posting via browser automation is not included." "Yellow"
    Write-Host "Please upload manually to your preferred platform."
    Write-Host ""
    Write-Host "Video: $videoPath"
    Write-Host "Caption: $caption $hashtags"
    Write-Host ""
    
    # Open folder for manual upload
    $folderPath = Split-Path $videoPath -Parent
    if (Test-Path $folderPath) {
        Write-ColorText "Opening folder for manual upload..." "Green"
        Start-Sleep -Seconds 1
        Start-Process explorer.exe -ArgumentList $folderPath
    }
}

function Run-Diagnostics {
    Write-ColorText "`nSYSTEM DIAGNOSTICS" "Cyan"
    Write-Host ""
    
    # Check FFmpeg
    Write-Host -NoNewline "FFmpeg: "
    try {
        $ffmpegOutput = & ffmpeg -version 2>&1 | Select-Object -First 1
        if ($ffmpegOutput -match "ffmpeg version") {
            Write-ColorText "OK - Installed" "Green"
            Write-Host "       $ffmpegOutput"
        } else {
            Write-ColorText "FAILED - Not found" "Red"
            Write-Host "       Please install FFmpeg from https://ffmpeg.org/download.html"
        }
    } catch {
        Write-ColorText "FAILED - Not found" "Red"
        Write-Host "       Please install FFmpeg from https://ffmpeg.org/download.html"
    }
    
    # Test simple FFmpeg command
    Write-Host -NoNewline "FFmpeg drawtext test: "
    $testOutput = Join-Path $env:TEMP "ffmpeg_test_$(Get-Random).mp4"
    $testFilter = "drawtext=text='TEST':fontcolor=white:fontsize=24:x=100:y=100"
    $testCmd = "ffmpeg -y -f lavfi -i color=c=black:s=320x240:d=1 -vf `"$testFilter`" -c:v libx264 -preset ultrafast `"$testOutput`" 2>&1"
    
    try {
        $testResult = Invoke-Expression $testCmd
        if (Test-Path $testOutput) {
            Write-ColorText "OK" "Green"
            Remove-Item $testOutput -Force -ErrorAction SilentlyContinue
        } else {
            Write-ColorText "FAILED" "Red"
            Write-Host "       drawtext filter not working"
        }
    } catch {
        Write-ColorText "FAILED" "Red"
        Write-Host "       FFmpeg command failed"
    }
    
    # Check directories
    Write-Host ""
    Write-Host "Directories:"
    $dirs = @($OutputDir, $AssetsDir, $MusicDir, $LogsDir)
    foreach ($dir in $dirs) {
        if (Test-Path $dir) {
            Write-Host "  [OK] $dir" -ForegroundColor Green
        } else {
            Write-Host "  [CREATED] $dir" -ForegroundColor Yellow
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    # Disk space
    try {
        $driveRoot = (Get-Location).Drive.Name + ":\"
        $driveInfo = Get-PSDrive -Name (Get-Location).Drive.Name
        $freeGB = [math]::Round($driveInfo.Free / 1GB, 2)
        $totalGB = [math]::Round(($driveInfo.Used + $driveInfo.Free) / 1GB, 2)
        Write-Host ""
        Write-Host "Disk space on $driveRoot : $freeGB GB free of $totalGB GB"
    } catch {
        Write-Host ""
        Write-Host "Disk space: Could not determine"
    }
    
    Write-Host ""
    Write-ColorText "FFMPEG INSTALLATION INSTRUCTIONS:" "Yellow"
    Write-Host "  1. Download FFmpeg from https://ffmpeg.org/download.html"
    Write-Host "  2. Extract to C:\ffmpeg"
    Write-Host "  3. Add C:\ffmpeg\bin to system PATH"
    Write-Host "  4. Restart PowerShell"
    Write-Host ""
}

function Interactive-Mode {
    $running = $true
    
    while ($running) {
        Show-Banner
        Show-Menu
        
        $choice = Read-Host "Select option"
        
        switch ($choice) {
            "1" {
                Write-ColorText "`nVIDEO GENERATION" "Cyan"
                Write-Host ""
                
                Write-Host "Templates:"
                Write-Host "  1. zodiac_dark"
                Write-Host "  2. motivational"
                Write-Host "  3. educational"
                Write-Host "  4. quote_simple"
                Write-Host "  5. tips_daily"
                Write-Host ""
                $templateChoice = Read-Host "Select template (1-5) [2]"
                
                switch ($templateChoice) {
                    "1" { $template = "zodiac_dark" }
                    "2" { $template = "motivational" }
                    "3" { $template = "educational" }
                    "4" { $template = "quote_simple" }
                    "5" { $template = "tips_daily" }
                    default { $template = "motivational" }
                }
                
                $zodiac = ""
                if ($template -eq "zodiac_dark") {
                    Write-Host ""
                    Write-Host "Zodiac signs:"
                    $script:ZodiacColors.Keys | ForEach-Object { Write-Host "  $_" }
                    $zodiac = Read-Host "Enter zodiac sign [leo]"
                    if ($zodiac -eq "") { $zodiac = "leo" }
                }
                
                Write-Host ""
                Write-Host "Enter text content (1-5 lines, empty line to stop):"
                $texts = @()
                for ($i = 1; $i -le 5; $i++) {
                    $line = Read-Host "  Line $i"
                    if ($line -eq "") { break }
                    $texts += $line
                }
                
                if ($texts.Count -eq 0) {
                    Write-ColorText "No text entered. Returning to menu." "Yellow"
                    Read-Host "`nPress Enter to continue"
                    continue
                }
                
                $keyword = Read-Host "Background keyword (for reference) [nature]"
                if ($keyword -eq "") { $keyword = "nature" }
                
                $musicPath = Read-Host "Music file path (optional, press Enter to skip)"
                
                $outputVideo = Generate-Video -Template $template -Zodiac $zodiac -Texts $texts -Keyword $keyword -MusicPath $musicPath
                
                if ($outputVideo) {
                    Save-History -VideoPath $outputVideo -TextPreview $texts[0] -Template $template
                    Write-Host ""
                    $postNow = Read-Host "Open folder containing video? (y/n) [y]"
                    if ($postNow -ne "n") {
                        $folderPath = Split-Path $outputVideo -Parent
                        Start-Process explorer.exe -ArgumentList $folderPath
                    }
                }
                
                Read-Host "`nPress Enter to continue"
            }
            "2" {
                Batch-Generate
                Read-Host "`nPress Enter to continue"
            }
            "3" {
                Write-ColorText "`nSCHEDULE MODE" "Cyan"
                Write-Host ""
                Write-Host "To schedule video generation:"
                Write-Host ""
                Write-Host "1. Open Windows Task Scheduler"
                Write-Host "2. Create Basic Task"
                Write-Host "3. Set trigger (time/daily/weekly)"
                Write-Host "4. Set action: Start a program"
                Write-Host "   Program: powershell.exe"
                Write-Host "   Arguments: -File `"$PSCommandPath`" batch"
                Write-Host ""
                Write-Host "Or use this command in Command Prompt:"
                Write-Host "  schtasks /create /tn `"VideoGen`" /tr `"powershell -File `"$PSCommandPath`" batch`" /sc daily /st 09:00"
                Write-Host ""
                Read-Host "Press Enter to continue"
            }
            "4" {
                Show-Config
                Read-Host "`nPress Enter to continue"
            }
            "5" {
                Show-Queue
                Show-History
                Read-Host "`nPress Enter to continue"
            }
            "6" {
                Cleanup-OldFiles
                Read-Host "`nPress Enter to continue"
            }
            "7" {
                Run-Diagnostics
                Read-Host "`nPress Enter to continue"
            }
            "8" {
                Post-To-Social
                Read-Host "`nPress Enter to continue"
            }
            "9" {
                Show-Help
                Read-Host "`nPress Enter to continue"
            }
            "0" {
                $running = $false
                Write-ColorText "`nGoodbye!" "Green"
            }
            default {
                Write-ColorText "Invalid option" "Red"
                Start-Sleep -Seconds 1
            }
        }
    }
}

# ============ Main Entry Point ============

# Ensure UTF-8 encoding for PowerShell console
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Process command line arguments
if ($Interactive -or $Command -eq "interactive") {
    Interactive-Mode
} else {
    switch ($Command) {
        "generate" {
            $texts = @()
            if ($Text1 -ne "") { $texts += $Text1 }
            if ($Text2 -ne "") { $texts += $Text2 }
            if ($Text3 -ne "") { $texts += $Text3 }
            if ($Text4 -ne "") { $texts += $Text4 }
            if ($Text5 -ne "") { $texts += $Text5 }
            
            if ($texts.Count -eq 0) {
                Write-ColorText "Error: No text provided" "Red"
                Write-ColorText "Use -Text1 'Your text' to add content" "Yellow"
                exit 1
            }
            $output = Generate-Video -Template $Template -Zodiac $Zodiac -Texts $texts -Keyword $Keyword -MusicPath $Music -OutputName $Output
            if ($output) {
                Write-ColorText "Video saved to: $output" "Green"
                Save-History -VideoPath $output -TextPreview $texts[0] -Template $Template
            }
        }
        "batch" {
            Batch-Generate -CsvFile $Output
        }
        "schedule" {
            Write-ColorText "Schedule mode - use Windows Task Scheduler" "Yellow"
            Write-Host ""
            Write-Host "Example Task Scheduler command:"
            Write-Host "  powershell -File `"$PSCommandPath`" batch"
        }
        "config" {
            Show-Config
        }
        "status" {
            Show-Queue
            Show-History
        }
        "diagnostics" {
            Run-Diagnostics
        }
        "help" {
            Show-Help
        }
        default {
            Show-Help
        }
    }
}