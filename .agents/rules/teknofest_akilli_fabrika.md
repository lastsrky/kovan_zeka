# TEKNOFEST 2026 Akıllı Fabrika Sistemleri - Proje ve Kod Kuralları

Bu kurallar, Antigravity AI asistanının ve ekip üyelerinin TEKNOFEST Mesleki Yetenek Yarışması Akıllı Fabrika Programlama Kategorisi Şartnamesi ve Final Senaryosu'na uygun çalışmasını sağlamak için tanımlanmıştır.

## 1. Donanım Mimarisi
- **Ana İşlemci:** NVIDIA Jetson Orin Nano Developer Kit (Otonom araç ve robot kol kontrolü).
- **Kameralar:** 2x Intel® RealSense™ D455 (Otonom araç çevre algılama ve robot kol nesne tespiti).
- **HMI Paneli:** Endüstriyel HMI (PLC ile haberleşen operatör paneli, reçete, sayaç, alarm ve E-Stop).
- **PLC & Konveyör:** S7-1200 / TIA Portal tabanlı konveyör üretim hattı simülasyonu.
- **Robot Kol:** Arduino / Seri port tabanlı nesne kavrama ve yükleme mekanizması.
- **Otonom Araç Platformu:** Görev tabanlı mobil şerit takip ve park platformu.

## 2. Final Senaryosu ve İş Akışı (Flow)
1. **Konveyör & Başlangıç:**
   - Operatör panelinden START butonuna basıldığında, konveyör girişinde küp varsa sistem çalışır ve **Yeşil Sinyal Lambası** yanar.
   - Konveyör çıkış sensörü küpü algıladığında konveyör durur, Yeşil lamba söner ve **Kırmızı Sinyal Lambası** yanar.
   - Herhangi bir anda STOP veya Acil Stop butonuna basıldığında tüm sistem anında durur.
2. **PLC -> Robot Kol Tetikleme:**
   - Konveyör çıkışında küp algılandığında ve otonom araç yükleme noktasında hazır olduğunda PLC, robot kola **BAŞLA** sinyali gönderir.
3. **Robot Kol & Renk Tespiti:**
   - **KESİN KURAL:** Robot kolda YAPAY ZEKA / MODEL KULLANILMAZ!
   - Küp rengi (kırmızı / yeşil / mavi) Intel RealSense kameradan **KLASİK GÖRÜNTÜ İŞLEME (HSV eşikleme)** ile tespit edilir.
   - Robot kol küpü konveyörden alıp otonom araca yükler.
   - Yükleme sonrası MQTT protokolü üzerinden `arac/yuk` konusuna tespit edilen renk mesajını iletir (`RED`, `GREEN`, `BLUE`).
4. **Otonom Araç & Saha Görevleri:**
   - Otonom araç MQTT üzerinden gelen renk/başla bildirimini alınca şerit takibine başlar.
   - Pistteki **TABELALARI** tespit ederek görevleri (sollama, hız sınırı, trafik ışığı vb.) yerine getirir.
   - Taşıdığı küpün rengine uygun renkteki park alanına park eder ve görevi tamamlanıp durur (tek görevliktir).
5. **Çevrim (Döngü):**
   - PLC, konveyör ve robot kol; konveyöre yeni küp geldikçe bu çevrimi sürekli tekrarlar.

## 3. Puanlama Kriterleri ve Optimizasyon Odakları (Final %85)
- **%25 Görev Doğruluğu:** Tüm bileşenlerin sırasıyla hatasız haberleşip görevi bitirmesi.
- **%10 Süre Performansı:** Kodların gecikmesiz (non-blocking) çalışması, hızlı renk/şerit tespiti.
- **%10 Sistem Kararlılığı:** İstisnaların (exception handling) yakalanması, bağlantı kopmalarında otomatik yeniden bağlanma.
- **%10 Otonom Araç:** Şerit ortalama, tabela tespit doğruluğu, doğru renkli alana park.
- **%10 PLC Senaryosu:** Sensör-lamba-motor mantığı ve çevrimin sürekliliği.
- **%10 Robot Kol:** HSV renk doğruluğu, titreşimsiz kavrama ve yükleme.
- **%10 HMI Paneli:**
  - %3 Kullanıcı dostu UX/UI tasarımı,
  - %3 PLC haberleşme hızı ve doğruluğu,
  - %2 Alarm ve E-Stop fonksiyonelliği,
  - %2 Reçete/mod seçimi ve hatasız parça/renk sayacı.
