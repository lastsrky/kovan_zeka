#!/usr/bin/env bash
# ==============================================================================
# TEKNOFEST 2026 - Akilli Fabrika Tek Tikla macOS Kurulumu (.command)
# Bu dosyaya cift tiklandiginda Terminal otomatik acilir ve tum kurulumu yapar.
# ==============================================================================

# Calisilan dizini bu dosyanin bulundugu yer yap
cd "$(dirname "$0")"

clear
echo "======================================================"
echo "  TEKNOFEST 2026 - Akilli Fabrika Otomatik Kurulum    "
echo "======================================================"
echo ""

# Eger dosya henuz repo icinde degilse (orn: WhatsApp'tan indirilip cift tiklandiysa)
if [ ! -f "requirements.txt" ]; then
    echo "[+] Proje dosyalari indiriliyor (GitHub)..."
    TARGET_DIR="$HOME/Desktop/kovan_zeka"
    if [ ! -d "$TARGET_DIR" ]; then
        git clone https://github.com/lastsrky/kovan_zeka.git "$TARGET_DIR"
    fi
    cd "$TARGET_DIR"
fi

# 1. Python3 Kontrolu
echo "[1/3] Python 3 kontrol ediliyor..."
if ! command -v python3 &> /dev/null; then
    echo "[!] Mac'inizde Python 3 bulunamadi."
    echo "[!] Xcode gelistirici araclari yukleniyor, lutfen acilan onay penceresine 'Yukle' deyin..."
    xcode-select --install
    echo "Yukleme bittikten sonra bu dosyaya tekrar cift tiklayin."
    read -p "Cikmak icin Enter'a basin..."
    exit 1
fi
echo "    Python hazir: $(python3 --version)"

# 2. Sanal Ortam (venv) Olusturma
echo ""
echo "[2/3] Sanal calisma ortami (venv) hazirlaniyor..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 3. Paketleri Kurma
echo ""
echo "[3/3] Proje kutuphaneleri yukleniyor (OpenCV, MQTT, NumPy vb.)..."
pip install --upgrade pip --quiet
pip install -r requirements.txt

echo ""
echo "======================================================"
echo "  TEBRIKLER! KURULUM EKSIKSIZ TAMAMLANDI!             "
echo "======================================================"
echo ""
echo "Proje konumu: $(pwd)"
echo ""
echo "Projeyi Antigravity ile acmak icin:"
echo "1. Antigravity IDE'yi acin."
echo "2. Open Folder diyerek bu klasoru secin."
echo ""
read -p "Kapatmak icin Enter'a basin..."