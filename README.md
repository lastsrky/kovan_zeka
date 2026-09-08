# TEKNOFEST 2026 - Akilli Fabrika Sistemleri (Kovan Zeka)

Bu depo, **TEKNOFEST 2026 Mesleki Yetenek Yarismasi Akilli Fabrika Sistemleri Programlama Kategorisi** final etabi icin gelistirilen yazilim modullerini ve ekip is birligi yapilandirmasini icerir.

---

## Proje Yapisi

- .agents/rules/teknofest_akilli_fabrika.md: Antigravity AI asistani kural ve sartname kilavuzu.
- docs/: Resmi sartname (PDF) ve final notu ozeti.
- otonomarac/: Otonom arac yazilimi (kamera, serit takibi, tabela algilama, motor surucu).
- 
obotkol/: Robot kol yazilimi (HSV renk tespiti, Arduino iletisimi, MQTT arac/yuk bildirimi).
- plc/: TIA Portal v14 Konveyor PLC projesi.
- 
equirements.txt: Gerekli Python paketleri.

---

## Ekip Arkadaslari Icin Ortak Calisma Rehberi

### 1. Depoyu Klonlayin
`ash
git clone https://github.com/lastsrky/kovan_zeka.git
cd kovan_zeka
`

### 2. Antigravity IDE ile Acin
- Antigravity IDE'yi acin ve **Open Folder** diyerek bu klasoru secin.
- Antigravity, .agents/rules/ altindaki dosyalari otomatik yukler. Yapay zeka tum sartname kurallarina tam uyumlu kod onerir.

### 3. Bagimliliklari Yukleyin
`ash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
`

### 4. Git Calisma Standarti (Branching)
`ash
git checkout -b feature/gorev-adi
# Degisiklikleri yapip kaydedin
git add .
git commit -m 'feat: ilgili degisiklik'
git push origin feature/gorev-adi
`
