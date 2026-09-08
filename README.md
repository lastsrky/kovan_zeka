# TEKNOFEST 2026 - Akıllı Fabrika Sistemleri (Kovan Zeka)

Bu depo, **TEKNOFEST 2026 Mesleki Yetenek Yarışması Akıllı Fabrika Sistemleri Programlama Kategorisi** final etabı için geliştirilen yazılım modüllerini ve ekip iş birliği yapılandırmasını içerir.

---

## 📁 Proje Yapısı

- **`.agents/rules/teknofest_akilli_fabrika.md`**: Antigravity AI asistanı kural ve şartname kılavuzu.
- **`docs/`**: Resmi şartname (`FİNAL NOTU.pdf`) ve senaryo özeti (`SARTNAME_OZETI.md`).
- **`otonomarac/`**: Otonom araç yazılımı (kamera, şerit takibi, tabela tespiti, motor sürücü).
- **`robotkol/`**: Robot kol yazılımı (klasik HSV renk tespiti, Arduino iletişimi, MQTT araç bildirim modülü).
- **`plc/`**: TIA Portal v14 Konveyör PLC projesi (`teknofest_KONVEYÖR.zap14`).
- **`setup_mac.sh`**: macOS için tek komutla otomatik kurulum scripti.
- **`requirements.txt`**: Gerekli Python kütüphaneleri.

---

## 🍎 macOS Ekip Arkadaşları İçin Otomatik Kurulum (1 Komut)

Mac kullanan ekip üyeleri terminali açıp depo klasöründe şu komutu çalıştırmaları yeterlidir:

```bash
git clone https://github.com/lastsrky/kovan_zeka.git
cd kovan_zeka
./setup_mac.sh
```

Bu script:
1. Python 3 ve Git kontrollerini yapar.
2. Sanal ortamı (`venv/`) kurar.
3. Gerekli tüm paketleri (`requirements.txt`) yükler.
4. Kurulumu otomatik test edip doğrular.

Geliştirme yaparken ortamı aktif etmek için:
```bash
source venv/bin/activate
```

---

## 🪟 Windows Ekip Arkadaşları İçin Kurulum

```powershell
git clone https://github.com/lastsrky/kovan_zeka.git
cd kovan_zeka
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🚀 Antigravity IDE ile Çalışma
1. Antigravity IDE'yi açın.
2. **File > Open Folder** diyerek `kovan_zeka` klasörünü açın.
3. Antigravity, `.agents/rules/` altındaki yarışma kurallarını otomatik tanır ve şartnameye %100 uyumlu kod desteği sağlar.

---

## 🌿 Git Branch (Dal) Çalışma Kuralı
```bash
git checkout -b feature/gorev-adi
# Değişiklikleri yapıp commit'leyin:
git add .
git commit -m "feat: gorev aciklamasi"
git push -u origin feature/gorev-adi
```
