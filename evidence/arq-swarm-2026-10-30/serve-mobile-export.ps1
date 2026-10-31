$ErrorActionPreference = 'Stop'
$root = 'C:\ommd3076\Proejcts\nmit-hackathon\.runtime\swarm-mobile-export'
Set-Location $root
python -m http.server 8082 --bind 127.0.0.1 --directory $root
