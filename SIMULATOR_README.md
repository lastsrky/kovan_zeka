# TEKNOFEST 2026 Akıllı Fabrika Dijital İkiz (SITL) Simülatörü

Bu simülatör, **TEKNOFEST 2026 Mesleki Yetenek Yarışması - Akıllı Fabrika** kategorisi için geliştirilmiş, donanıma ihtiyaç duymadan yazılımlarınızı test edebileceğiniz **Yazılım Döngüde (SITL - Software-in-the-Loop)** bir sanal test ortamıdır.

---

## 🎯 Ne İşe Yarar?
1. **Fiziksel Donanım Olmadan Test:** PLC, konveyör bandı, robot kol ve otonom araç fiziksel olarak masada olmadan tüm akışı bilgisayarınızda çalıştırabilirsiniz.
2. **TEKNOFEST Orijinal Kodlarıyla Birebir Entegre:** `otonomarac/` klasörünüzdeki `LineDetector` (şerit algılama), `PIDController` (direksiyon kontrolü), `tabela` ve `trafik` modüllerini sanal kameraya bağlayıp doğrular.
3. **Resmi İletişim Protokolü:** S7-1200 PLC ladder mantığı ve MQTT resmi yarışma konuları (`arac/yuk`, `robot/basla`, vb.) eksiksiz uygulanmıştır.

---

## 🚀 Nasıl Çalıştırılır?

### 1. Görsel Arayüz (Pygame + OpenCV HUD + HMI Operatör Konsolu)
Simülatörü 1600x900 çözünürlüğünde grafik arayüzüyle başlatmak için:
```bash
python run_simulator.py
```

### 2. TEKNOFEST SITL Modunda Başlatma
Kendi yazdığınız `otonomarac` kodlarının (şerit takibi, PID) simülatördeki arabayı bizzat sürmesini istiyorsanız:
```bash
python run_simulator.py --sitl
```

### 3. Otomatik Doğrulama (Headless CI Test Modu)
Ekran açılmadan arka planda 3 farklı renkteki (Kırmızı, Yeşil, Mavi) küp için uçtan uca çevrimi test etmek için:
```bash
python run_simulator.py --headless --sitl
```

---

## 🕹️ Arayüz ve Kontroller

Simülatör ekranı 3 ana bölgeden oluşur:
1. **Sol Taraf (1040×900):** Fabrika arenası (Konveyör hattı, S1/S2 fotoselleri, sinyal kulesi, robot kol hücresi, 2 şeritli pist, yaya geçidi ve renkli park cepleri).
2. **Sağ Üst (560×420):** Çift Sanal RealSense D455 Kamera HUD'ı:
   - **CAM 1 (Robot Kol Kamerası):** Konveyör çıkışındaki küpün klasik OpenCV HSV renk tespiti ve ROI alanı.
   - **CAM 2 (Araç Kamerası):** Aracın gözünden perspektif yol görüntüsü, şerit çizgileri, tabela algılama ve 16-bit derinlik (Depth) haritası.
3. **Sağ Alt (560×480):** Endüstriyel HMI Dokunmatik Operatör Paneli:
   - **START:** PLC konveyör hattını ve çevrimi başlatır (Klavye: `Space` veya `S`).
   - **STOP:** Sistemi normal şekilde durdurur (Klavye: `X` veya `Esc`).
   - **E-STOP:** Acil Durdurma Mantar Butonu; tüm konveyör, kol ve aracı o anda dondurur (Klavye: `E`).
   - **RESET:** Acil durdurma sonrası sistemi sıfırlar (Klavye: `R`).
   - **Küp Ekle Butonları:** Konveyör girişine `RED`, `GREEN` veya `BLUE` küp bırakır (Klavye: `1`, `2`, `3`).

---

## 🧪 Test ve Kalite Güvencesi
Sistem, yarışma şartnamesinin 26 maddelik mimari envanterine göre 4 kademede test edilmiştir:
* **Birim ve Fonksiyonel Testler:** 352 test senaryosu.
* **Test Çalıştırma:**
  ```bash
  python -m unittest discover -s simulator/tests -p "test_*.py"
  ```
* **Sonuç:** `352/352 PASS` (%100 Başarı).
