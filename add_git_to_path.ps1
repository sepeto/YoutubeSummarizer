# Obtener el PATH actual
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")

# Añadir Git al PATH si no está ya
$gitPath = "C:\Program Files\Git\cmd"
if ($currentPath -notlike "*$gitPath*") {
    $newPath = "$currentPath;$gitPath"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "Git añadido al PATH del usuario"
} else {
    Write-Host "Git ya está en el PATH"
}

# Refrescar el PATH en la sesión actual
$env:Path = [Environment]::GetEnvironmentVariable("Path", "User")

Write-Host "`nPara que los cambios surtan efecto, necesitas cerrar y volver a abrir PowerShell" 