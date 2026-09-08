#!/usr/bin/env python3
import os
import sys
import subprocess

def main():
    print("========================================")
    print(" DIJITAL IKIZ SIMULASYONU BASLATILIYOR")
    print("========================================")
    
    # Çevre değişkenini ayarla
    env = os.environ.copy()
    env["SIMULATION_MODE"] = "1"
    
    # Otonom aracı başlat
    script_path = os.path.join("otonomarac", "main.py")
    
    if not os.path.exists(script_path):
        print(f"Hata: {script_path} bulunamadi.")
        sys.exit(1)
        
    print("Otonom arac yapay zekasi baslatiliyor...\n")
    
    # --no-remote ekleyerek testin hemen baslamasini (space tusuna basinca) sagliyoruz.
    try:
        subprocess.run([sys.executable, script_path, "--no-remote"], env=env)
    except KeyboardInterrupt:
        print("\nSimulasyon kapatildi.")
        
if __name__ == "__main__":
    main()
