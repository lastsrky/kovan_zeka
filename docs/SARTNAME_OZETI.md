# TEKNOFEST 2026 Mesleki Yetenek Yarışması
## Akıllı Fabrika Sistemleri Programlama Kategorisi - Final Notu Özeti

### 1. Final Senaryosu
- **Sistem Başlatma:** Start butonuna basıldığında konveyör girişinde küp varsa konveyör çalışmaya başlar ve **Yeşil Sinyal Lambası** aktif olur.
- **Konveyör Çıkışı:** Çıkıştaki sensör küpü algıladığında konveyör duraklar. Yeşil sinyal lambası söner, **Kırmızı Sinyal Lambası** yanar.
- **Robot Kol Tetikleme:** Konveyör durakladığında ve otonom araç yükleme noktasında hazır olduğunda PLC robot kola **BAŞLA** sinyali gönderir.
- **Küp Renk Tespiti:** Robot kol üzerindeki kamera ile küpün rengi tespit edilir.
  - **DİKKAT:** Robot kolda yapay zeka / derin öğrenme modeli KULLANILMAZ.
  - Renk tespiti (Kırmızı, Yeşil, Mavi) klasik görüntü işleme (**HSV uzayı**) ile yapılmalıdır.
- **Yükleme ve MQTT Bildirimi:**
  - Robot kol küpü araca yükler.
  - Küpün rengini MQTT protokolü üzerinden araca bildirir:
    - **Topic:** rac/yuk
    - **Payload:** RED / GREEN / BLUE
- **Otonom Araç Hareketi:**
  - MQTT bildirimini alan araç şerit takibine başlar.
  - Pistteki tabelaları algılayıp ilgili görevleri yerine getirir.
  - Küpün rengine uygun renkli park alanına park ederek görevini tamamlar (tek görevliktir, park edince durur).
- **Çevrim ve E-Stop:**
  - PLC, konveyör ve robot kol yeni küp geldikçe döngüyü sürdürür.
  - Herhangi bir anda Stop / Acil Stop basılırsa tüm sistem durur.
- **Yarışma Süresi:**
  - Final günü verilecek revizyonların uygulanması ve sistemin devreye alınması için süre: **40 Dakika**.
