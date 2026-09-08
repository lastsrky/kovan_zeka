# TEKNOFEST 2026 - Mesleki Yetenek Yarışması
## Akıllı Fabrika Sistemleri Programlama Kategorisi Şartnamesi

---

## 1. Yarışma Amacı ve Kapsamı
Bu yarışma; üretim hatlarında kullanılan **PLC kontrollü konveyör sistemleri**, **görüntü işleme uygulamaları**, **robotik sistemler** ve **otonom taşıma teknolojilerinin** birlikte çalıştığı endüstriyel otomasyon senaryolarına yönelik uygulamalı becerilerin geliştirilmesini hedefler.

Yarışma kapsamında:
- **Konveyör Sistemi:** PLC ile kontrol edilir.
- **Robot Kol:** Kamera (Intel RealSense D455) verisi ile nesne algılayarak (Klasik HSV) alma ve bırakma görevlerini yapar.
- **Otonom Araç:** Yalnızca görüntü işleme temelli karar mekanizmalarıyla şerit takip eder, tabelaları tanır ve yük rengine uygun alana park eder.
- **HMI Operatör Paneli:** Sistemin başlatılması, izlenmesi, durdurulması, reçete/mod seçimi ve alarm yönetimi HMI üzerinden gerçekleştirilir; HMI, PLC ile haberleşerek koordinasyon sağlar.

---

## 2. Donanım ve Ekipman Listesi (Organizasyon Tarafından Sağlanan)

| Sistem Bileşeni | Ekipman / Donanım | Açıklama |
|---|---|---|
| **Ana İşlemci** | NVIDIA Jetson Orin Nano Developer Kit | Otonom araç ve robot kol kontrol işlemleri |
| **Otonom Araç Kamera** | Intel® RealSense D455 | Görüntü işleme ve çevre algılama |
| **Robot Kol Kamera** | Intel® RealSense D455 | Nesne algılama ve konumlandırma |
| **HMI Paneli** | Endüstriyel HMI | Operatör arayüzü ve sistem takibi |
| **Konveyör Sistemi** | Endüstriyel Konveyör | PLC ile sürülen üretim hattı simülasyonu |
| **Robot Kol** | Robotik Kol Platformu | Küp alma ve araca yükleme işlemleri |
| **Otonom Araç Platformu** | Otonom Mobil Robot | Görev tabanlı hareket sistemi |
| **Bağlantı Ekipmanları** | Kablo, güç kaynakları, switch | Sistem entegrasyonu |

*Not: Yarışmacıların alana harici mekanik/elektronik malzeme getirmesi yasaktır; tüm donanım organizasyonca sağlanır.*

---

## 3. Final Değerlendirme Kriterleri ve Puan Dağılımı

Final performansı toplam puanın **%85'ini** oluşturur:

| Kriter | Puan Ağırlığı | Açıklama |
|---|---|---|
| **Görev Doğruluğu** | **%25** | Senaryonun eksiksiz ve hatasız icra edilmesi |
| **Süre Performansı** | **%10** | Görevlerin tamamlanma hızı |
| **Sistem Kararlılığı** | **%10** | Hata vermeden, takılmadan akıcı çalışma |
| **Otonom Araç Performansı**| **%10** | Şerit takibi, tabela algılama, park doğruluğu |
| **PLC Senaryo Doğruluğu** | **%10** | Sensör-motor mantığı, sinyal lambaları |
| **Robot Kol Performansı** | **%10** | HSV ile renk tespiti, kavrama ve araca bırakma |
| **HMI / Arayüz Performansı**| **%10** | Detaylar aşağıdadır |
| **TOPLAM** | **%85** | *(Kalan %15 Yarı Final Sunum puanıdır)* |

### HMI / Operatör Arayüzü Puan Detayı (%10):
- **%3:** Arayüz tasarımı ve kullanılabilirlik (UX/UI)
- **%3:** PLC ile haberleşme doğruluğu
- **%2:** Alarm ve Acil Stop (E-Stop) fonksiyonelliği
- **%2:** Reçete/mod seçimi ve sayaç doğruluğu

---

## 4. Yarışma Kuralları
- **Final Süresi:** 40 dakika (Revizyonların uygulanması ve devreye alma).
- **İnternet Erişimi:** Finalde internet serbesttir; dışarıdan uzaktan müdahale/yardım yasaktır.
- **Revizyon Bilgisayarı:** Yazılım geliştirme bilgisayarları organizasyon tarafından sağlanır.
