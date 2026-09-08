# TEKNOFEST 2026 Akıllı Fabrika Sistemleri - Proje ve Kod Kuralları

Bu kurallar, Antigravity AI asistanının ve ekip üyelerinin TEKNOFEST Mesleki Yetenek Yarışması Akıllı Fabrika Programlama Kategorisi Final Senaryosu'na uygun çalışmasını sağlamak için tanımlanmıştır.

## 1. Final Senaryosu ve İş Akışı (Flow)
1. **Konveyör & Başlangıç:**
   - Operatör panelinden START butonuna basıldığında, konveyör girişinde küp varsa sistem çalışır ve **Yeşil Sinyal Lambası** yanar.
   - Konveyör çıkış sensörü küpü algıladığında konveyör durur, Yeşil lamba söner ve **Kırmızı Sinyal Lambası** yanar.
   - Herhangi bir anda STOP veya Acil Stop butonuna basıldığında tüm sistem anında durur.
2. **PLC -> Robot Kol Tetikleme:**
   - Konveyör çıkışında küp algılandığında ve otonom araç yükleme noktasında hazır olduğunda PLC, robot kola **BAŞLA** sinyali gönderir.
3. **Robot Kol & Renk Tespiti:**
   - **KESİN KURAL:** Robot kolda YAPAY ZEKA / MODEL KULLANILMAZ!
   - Küp rengi (kırmızı / yeşil / mavi) kameradan **KLASİK GÖRÜNTÜ İŞLEME (HSV eşikleme)** ile tespit edilir.
   - Robot kol küpü konveyörden alıp otonom araca yükler.
   - Yükleme sonrası MQTT protokolü üzerinden rac/yuk konusuna tespit edilen renk mesajını iletir (RED, GREEN, BLUE).
4. **Otonom Araç & Saha Görevleri:**
   - Otonom araç MQTT üzerinden gelen renk/başla bildirimini alınca şerit takibine başlar.
   - Pistteki **TABELALARI** tespit ederek görevleri (sollama, hız sınırı, trafik ışığı vb.) yerine getirir.
   - Taşıdığı küpün rengine uygun renkteki park alanına park eder ve görevi tamamlanıp durur (tek görevliktir).
5. **Çevrim (Döngü):**
   - PLC, konveyör ve robot kol; konveyöre yeni küp geldikçe bu çevrimi sürekli tekrarlar.

## 2. Kodlama ve Mimari Standartları
- **Hızlı Devreye Alma (40 Dakika Kuralı):** Final günü revizyonlar için toplam süre 40 dakikadır. Kodlarda sabit kodlanmış (hardcoded) değerler yerine config.yaml veya parametre dosyaları kullanılmalıdır.
- **Modülerlik:** Her modül (haberleşme, görüntü işleme, motor sürme, şerit takibi) bağımsız test edilebilir olmalıdır.
- **MQTT Topic Formatı:**
  - Konu: rac/yuk
  - Mesajlar: RED, GREEN, BLUE
- **Hata Yönetimi:** Donanım bağlantısı koptuğunda (seri port, kamera, MQTT broker) kod çökmek yerine yeniden bağlanmayı denemeli ve anlamlı log üretmelidir.
