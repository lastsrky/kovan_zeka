# TEKNOFEST Akıllı Fabrika — Olası Revizyonlar ve Müdahale Noktaları

Teknofest'in gönderdiği veya geliştirilen `otonomarac` ve `robotkol` paketleri, yarışma esnasında hakemlerin talep edebileceği ani kural değişikliklerine (revizyonlara) ve sahanın fiziksel koşullarına (ışık, zemin, pil durumu) adapte olabilmek için tasarlanmıştır. 

Aşağıda her iki klasör içindeki doküman ve kodlarda **nelerin, hangi amaçla revize edilebileceği** detaylıca listelenmiştir.

---

## 1. OTONOM ARAÇ KLASÖRÜ (`otonomarac/`) İÇİNDEKİ REVİZYONLAR

Araçtaki revizyonların **%90'ı kodlama gerektirmeden** sadece `config.yaml` dosyasındaki sayısal değerlerin değiştirilmesiyle yapılır.

### 1.1. `config.yaml` Üzerinden Yapılabilecek Revizyonlar
*   **Hız ve Motor Revizyonları (`[run]` ve `[motor]`):** Hakemler aracın daha hızlı veya daha yavaş gitmesini isterse `start_throttle` (örn: 0.3'ten 0.4'e) ve `throttle_max_pwm` değerleri revize edilir.
*   **Direksiyon ve Trim (`[motor]`):** Araç montaj kaynaklı sağa/sola çekiyorsa `steering_center` açısı (örn: 110 derece) kaydırılarak mekanik trim revizyonu yapılır. Virajlarda yeterince dönemiyorsa `steering_max_delta` artırılır.
*   **PID Şerit Takip Revizyonu (`[controller]`):** Sahanın sürtünmesi az ve araç yalpalıyorsa (balık kuyruğu), `kp` (sertlik) değeri düşürülüp `kd` (sönümleme) değeri artırılarak aracın yola oturması sağlanır.
*   **Trafik Lambası Görevi (`[trafik]`):** Hakem "kırmızı ışıkta X saniye bekle ve yeşili beklemeden kalk" derse `max_dur_s` parametresi revize edilir. Işığı algılama mesafesi (`max_mesafe_cm`) duruma göre uzatılıp kısaltılabilir.
*   **Yaya Geçidi Görevi (`[yaya]`):** Hakem bekleme süresini 3 saniyeden 5 saniyeye çıkarırsa `dur_s` revize edilir. Zebra çizgilerinde kameranın kafası karışmasın diye "kör geçiş" süresi (`gec_s`) ve geçiş gücü (`gec_pwm`) sahanın rampasına göre ayarlanır.
*   **Sollama Manevrası (`[overtake]`):** Dubayı gördüğünde sağ şeride ne kadar sert kayacağı `lane_shift_px` ile, dubaya ne kadar kala manevraya başlayacağı ise `trigger_distance_cm` ile revize edilir.
*   **Park Görevi (`[park]`):** Robot koldan MQTT üzerinden renk bilgisi gelmemesi ihtimaline karşı hakem "yedek (varsayılan) renk belirleyin" derse `varsayilan_renk` (örn: BLUE) parametresi değiştirilir. Aracın park cebine ne kadar derin gireceği `dur_mesafe_cm` ile ayarlanır.

### 1.2. Python Dosyası Bazlı Özel Revizyonlar
*   **`park_zemin_renk.py`:** Sahanın ışıklandırması nedeniyle kamera park cebindeki Yeşil veya Mavi rengi göremiyorsa, bu dosya içindeki alt ve üst HSV sınır değerleri genişletilerek renk filtreleri revize edilir.
*   **`orange_detect_depth.py`:** Sollanacak dubanın rengi yarışma günü daha açık/koyu turuncu gelirse, bu dosyadaki `ORANGE_LAB` veya HSV eşikleri değiştirilir.
*   **`main.py`:** Hakem görevlerin öncelik sırasını değiştirirse (Örneğin: "Önce trafik ışığına baksın, sonra yaya geçidine") ana döngüdeki if/else bloklarının sırası revize edilebilir.
*   **`colorlink.py`:** Eğer yarışma günü Wi-Fi kullanımı yasaklanırsa veya MQTT çökerse, kod revize edilerek aracın klavyeden veya butonla tetiklenmesi sağlanabilir.

---

## 2. ROBOT KOL KLASÖRÜ (`robotkol/`) İÇİNDEKİ REVİZYONLAR

Robot kol sistemi mekanik hassasiyet gerektirdiği için revizyonlar genellikle JSON ayar dosyalarından veya donanım katmanından yapılır.

### 2.1. Otonom Döngü ve Açı Revizyonları (`otonom_dongu.py`)
*   **Gripper (Tutucu) Ayarları:** Küp boyutu değişirse veya gripper yeterince sıkmıyorsa `grip_kapat` açısı (örn: 110 dereceden 118 dereceye) artırılır.
*   **Omuz Güvenlik Payı:** Kol küpü konveyörden alıp dönerken zemine çarpıyorsa `omuz_kaldir_aci` parametresi artırılarak havaya kalkış miktarı revize edilir.
*   **Robot Hızı:** Senaryonun hızlanması için bekleme (sleep) süreleri veya döngü hareket hızları (`AyarOtonom.hiz`) artırılabilir.

### 2.2. Kalibrasyon ve JSON Revizyonları
*   **`renk_kalibrasyon.json`:** Yarışma çadırındaki gün ışığı veya projektörler değiştikçe Kırmızı, Yeşil ve Mavi küplerin algılanması bozulur. `otonom_panel.py` arayüzü açılarak yeni HSV değerleri bu dosyaya kaydedilir. Ayrıca küpteki ışık parlamasını tolere etmek için `doluluk_esigi` (örn: %40'tan %25'e) revize edilebilir.
*   **`konumlar.json`:** Konveyör masasının boyu uzar veya otonom aracın park pozisyonu değişirse `GORME`, `AL` ve `YUKLE` açıları panelden yeniden öğretilerek bu JSON dosyasına revize edilir. Yeni görev olarak "hatalı küpü çöpe at" (ıskarta) kuralı gelirse, buraya `"ISKARTA"` adında yeni bir açı dizisi eklenebilir.

### 2.3. Arduino, Donanım ve Haberleşme Revizyonları
*   **`arduino_robot/arduino_robot.ino` (Donanım Revizyonu):** PLC panosunda Başla sinyali veren K10 rölesinin kablosu zarar görür ve hakem sinyali başka bir kanaldan verirse, Arduino içindeki `#define SINYAL_PIN A5` satırı revize edilerek (örn: `A1`) yeni pine uyarlanır. Limit switch yönleri veya servo PWM frekansları gerekirse değiştirilir.
*   **`robot_link.py`:** Robot kolun fiziksel olarak masaya çarpmasını engellemek için `LIMITS_DEG` değişkeni içindeki minimum ve maksimum eklem açıları daraltılarak yazılımsal güvenlik bariyeri revize edilir.
*   **`arac_haberlesme.py` (Ağ Revizyonu):** Yarışma komitesi "Bizim ana broker sunucumuza bağlanın" derse, `VARSAYILAN_BROKER` değişkenindeki IP adresi revize edilir. Ayrıca mesaj formatı düz metinden (RED) JSON formatına çevrilmek istenirse bu dosyadaki `publish` fonksiyonu güncellenir.
