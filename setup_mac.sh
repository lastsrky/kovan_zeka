#!/usr/bin/env bash
# ==============================================================================
# TEKNOFEST 2026 - Akilli Fabrika (Kovan Zeka) macOS Otomatik Kurulum Scripti
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}  TEKNOFEST 2026 - Akilli Fabrika macOS Kurulumu       ${NC}"
echo -e "${BLUE}======================================================${NC}"

# 1. Python 3 Kontrolu
echo -e "\n${YELLOW}[1/4] Python 3 kontrol ediliyor...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Hata: python3 bulunamadi!${NC}"
    echo "Homebrew ile yuklemek icin terminalde calistirin: brew install python"
    exit 1
fi
echo -e "${GREEN}Bulunan surum: $(python3 --version)${NC}"

# 2. Git Kontrolu
echo -e "\n${YELLOW}[2/4] Git kontrol ediliyor...${NC}"
if ! command -v git &> /dev/null; then
    echo -e "${RED}Hata: git bulunamadi!${NC}"
    echo "Xcode Command Line Tools icin terminalde calistirin: xcode-select --install"
    exit 1
fi
echo -e "${GREEN}Git hazir: $(git --version)${NC}"

# 3. Virtualenv (Sanal Ortam)
echo -e "\n${YELLOW}[3/4] Python sanal ortami (venv) hazirlaniyor...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}Sanal ortam olusturuldu (venv/)${NC}"
else
    echo -e "${GREEN}Mevcut sanal ortam kullaniliyor (venv/)${NC}"
fi

source venv/bin/activate

echo "Pip guncelleniyor..."
pip install --upgrade pip --quiet

# 4. Bagimliliklarin Kurulumu
echo -e "\n${YELLOW}[4/4] Paketler yukleniyor (requirements.txt)...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}Paketler basariyla yuklendi!${NC}"
else
    echo -e "${RED}requirements.txt bulunamadi!${NC}"
    exit 1
fi

# 5. Dogrulama Testi
echo -e "\n${YELLOW}Kurulum dogrulaniyor...${NC}"
python3 -c "
import cv2, numpy, paho.mqtt.client, serial, yaml, PIL, pypdf
print('>> OpenCV Surumu: ' + cv2.__version__)
print('>> NumPy Surumu: ' + numpy.__version__)
print('>> Tum temel kutuphaneler macOS uzerinde basariyla calisiyor!')
"

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}  KURULUM BASARIYLA TAMAMLANDI!                      ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "\nCalismaya baslamak icin terminalde su komutu verin:"
echo -e "${BLUE}source venv/bin/activate${NC}"
echo -e "\nAntigravity IDE ile projeyi acip gelistirmeye baslayabilirsiniz!\n"