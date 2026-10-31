[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ports = @(3000, 8000)
$stopped = @()

foreach ($port in $ports) {
    $owners = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($ownerPid in $owners) {
        $process = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
        $commandLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $ownerPid" -ErrorAction SilentlyContinue).CommandLine
        $isNetRca = (($port -eq 3000) -and (
                ($commandLine -match "next(.cmd)?\s+dev|next-server") -or
                ($commandLine -like "*\node_modules\next\dist\server\lib\start-server.js*")
            )) -or (($port -eq 8000) -and ($commandLine -match "uvicorn\s+app\.main:app"))
        if ($process -and $isNetRca) {
            Stop-Process -Id $ownerPid
            $stopped += "port $port (PID $ownerPid, $($process.ProcessName))"
        } elseif ($process) {
            Write-Warning "Preserved unrelated listener on port $port (PID $ownerPid, $($process.ProcessName))."
        }
    }
}

if ($stopped.Count -eq 0) {
    Write-Host "No NetRCA listeners were found on ports 3000 or 8000."
} else {
    Write-Host "Stopped: $($stopped -join '; ')" -ForegroundColor Green
}
