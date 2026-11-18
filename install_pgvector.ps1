$src = "$env:TEMP\pgvector"
$pgRoot = "C:\Program Files\PostgreSQL\18"

Copy-Item "$src\lib\vector.dll" "$pgRoot\lib\vector.dll" -Force
Copy-Item "$src\vector.control" "$pgRoot\share\extension\vector.control" -Force
Copy-Item "$src\share\extension\*.sql" "$pgRoot\share\extension\" -Force
if (-not (Test-Path "$pgRoot\include\server\extension\vector")) {
    New-Item -ItemType Directory "$pgRoot\include\server\extension\vector" -Force | Out-Null
}
Copy-Item "$src\include\server\extension\vector\*" "$pgRoot\include\server\extension\vector\" -Force

Write-Host "pgvector v0.8.7 installed into PostgreSQL 18 successfully."
