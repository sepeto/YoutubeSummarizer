import os
import shutil
from datetime import datetime

def backup_output():
    # Crear carpeta de backup con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join("output_old", f"backup_{timestamp}")
    
    # Directorios a respaldar
    dirs_to_backup = [
        "output/downloads",
        "output/transcriptions",
        "output/summaries",
        "output/logs",
        "output/usage_logs"
    ]
    
    try:
        # Crear estructura de directorios en backup
        for dir_path in dirs_to_backup:
            backup_path = os.path.join(backup_dir, dir_path.replace("output/", ""))
            os.makedirs(backup_path, exist_ok=True)
            
            # Si el directorio original existe, mover su contenido
            if os.path.exists(dir_path):
                for item in os.listdir(dir_path):
                    src = os.path.join(dir_path, item)
                    dst = os.path.join(backup_path, item)
                    shutil.move(src, dst)
                    print(f"Movido: {src} -> {dst}")
        
        print(f"\nBackup completado en: {backup_dir}")
        
    except Exception as e:
        print(f"Error durante el backup: {str(e)}")

if __name__ == "__main__":
    backup_output() 