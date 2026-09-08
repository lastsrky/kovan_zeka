# Original User Request

## 2026-09-08T11:49:55Z

TEKNOFEST 2026 Mesleki Yetenek Yarışması Akıllı Fabrika kategorisi için PLC konveyör hattı, HSV renk tespitli robot kol ve otonom araç (şerit takip, tabela ve renkli park) sistemlerinin donanım olmadan uçtan uca test edilebileceği Pygame ve OpenCV tabanlı bir Dijital İkiz (SITL) simülatörü geliştirilmesi.

Working directory: c:\Users\user\OneDrive\Desktop\TEKNOFEST MESLEKİ YETENEK YARIŞMASI-AKILLI FABRİKA\simulator
Integrity mode: development

## Requirements

### R1. Pygame & OpenCV 2D Fabrika ve Pist Arayüzü
Konveyör bandı, robot kol çalışma hücresi, şeritli araç pisti, trafik tabelaları ve 3 farklı renkteki (Kırmızı, Yeşil, Mavi) park ceplerini içeren kuşbakışı ve sanal kamera görünümlü 2D interaktif simülasyon arayüzü sunulmalıdır. Arayüzde HMI işlevi görecek Start, Stop, Acil Stop (E-Stop) ve Küp Ekleme kontrolleri bulunmalıdır.

### R2. PLC ve Konveyör Durum Makinesi (State Machine)
S7-1200 lojiğini birebir yansıtan, konveyör giriş sensöründen küp algılandığında Yeşil Sinyal Lambası ile bandı hareket ettiren, çıkış sensöründe küp durduğunda Kırmızı Lamba yakıp robot kola tetik sinyali gönderen ve E-Stop durumunda anında kilitlenen bir PLC motoru modellenmelidir.

### R3. Robot Kol ve HSV Renk Tespiti / MQTT Entegrasyonu
Robot kolun konveyörden küpü alma sürecinde sanal kamera çıktısını klasik OpenCV HSV renk uzayı algoritması (enk_algila.py mantığı) ile analiz ederek küp rengini (RED / GREEN / BLUE) tespit etmesi, küpü araca yükleme simülasyonunu icra etmesi ve yerel MQTT broker'a rac/yuk konusuna renk mesajını yayınlaması sağlanmalıdır.

### R4. Otonom Araç Sürüş, Şerit Takip ve Tabela/Park Motoru
MQTT yük bildirimini aldıktan sonra piste çıkan otonom aracın, sanal kamera görüş alanındaki şeritleri izlemesi, karşılaştığı tabelalara göre aksiyon alması ve robot koldan bildirilen renge ait park alanına hatasız yanaşarak görevi tamamlaması sağlanmalıdır. Mevcut otonomarac/ modüllerinin işlevleriyle uyumlu çalışmalıdır.

## Acceptance Criteria

### Uçtan Uca Çevrim Doğrulaması
- [ ] Tek bir Python komutuyla simülatör başlatılabilmeli ve görsel arayüz hatasız açılmalıdır.
- [ ] Operatör panelinden START basılıp konveyöre küp bırakıldığında; konveyör hareketi -> çıkış sensörü algılaması -> robot kol HSV renk tespiti -> MQTT rac/yuk yayını sırasıyla otomatik gerçekleşmelidir.
- [ ] Otonom araç MQTT mesajını aldığında hareketlenmeli, şerit takibi yaparak doğru renkteki park alanına park etmeli ve durmalıdır.
- [ ] Simülasyon sırasında herhangi bir anda E-Stop basıldığında tüm sistem (konveyör, kol, araç) anında donmalı; Reset sonrası güvenli duruma dönebilmelidir.
- [ ] Otomatik bir doğrulama (test) scripti ile sistemin 3 farklı renkteki (Kırmızı, Yeşil, Mavi) küp için uçtan uca çevrimi hatasız tamamladığı programatik olarak doğrulanabilmelidir.

## 2026-09-08T12:29:06Z

Sunucu/uygulama yeniden başlatıldı. Tüm yetki sende ve kullanıcı her adımı önceden onayladı. Lütfen kaldığın yerden tam hızla devam et: M1 tamamlandı/inceleniyor. M2 (S7-1200 PLC durum makinesi, konveyör sensör/lamba lojiği ve HMI paneli), M3 (Robot kol HSV renk tespiti ve MQTT) ve M4 (Otonom araç sürüş, şerit takip ve park) modüllerini tamamla, test paketini koştur ve projeyi sonlandır.

