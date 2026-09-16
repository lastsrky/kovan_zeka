# 📋 TEKNOFEST AKILLI FABRİKA — SAHA DOSYA VE REVİZYON REHBERİ
*1-2 Sayfa Hızlı Baskı & Saha El Kılavuzu (Cheat Sheet)*

---

## 📌 GENEL BAKIŞ & SİSTEM MİMARİSİ
Bu kılavuz, TEKNOFEST Akıllı Fabrika Sistemleri Programlama yarışmasında yarışma komitesi tarafından sağlanan `robotkol` ve `otonomarac` paketlerinin içindeki **tüm dosyaların görevlerini**, **revizyon anında hangi satır/parametrelerin değişeceğini** ve **olası arızalarda hangi dosyaya müdahale edileceğini** özetler.

```
[PLC (S7-1200)] --(K10 Rölesi / A5)--> [Robot Kol (Jetson + Arduino)]
                                                |
                                       (MQTT: arac/yuk)
                                                v
[Küp Algılama (MZ80)] ---------------> [Otonom Araç (Jetson + ESP)] --> [Park Alanı]
```

---

# 🤖 BÖLÜM 1: ROBOT KOL SİSTEMİ (`robotkol/`)

| Dosya Adı | Ne İşe Yarar? (Görevi) | Revizyonda Neler Değişebilir? (Parametre / Değişken) |
| :--- | :--- | :--- |
| **`arduino_robot/arduino_robot.ino`** | **Arduino Firmware:** Step motorları (`AccelStepper`), limit switch'leri, gripper servosunu ve PLC `K10` başla sinyalini (`A5`) yöneten donanım kontrol kodudur. | • **Pin Değişikliği:** `#define SINYAL_PIN A5`, `#define SERVO_PIN A1`<br>• **Homing Yönü:** `homingDir[4] = {-1, +1, -1, +1}` (Eksen yönü ters dönerse)<br>• **Limit Switch Tipleri:** NC/NO değişimi (`digitalRead(swPins[i]) == LOW`) |
| **`robot_link.py`** | **Jetson-Arduino Seri Köprüsü:** Açıları motor adımlarına (`deg_to_steps`), adımları dereceye çevirir. Seri portu dinler, güvenlik açı limitlerini denetler. | • **Seri Port:** `DEFAULT_PORT = "/dev/ttyCH341USB0"` veya `"/dev/ttyUSB0"`<br>• **Açı Limitleri:** `LIMITS_DEG` (Fiziksel çarpma engeli için min/max eklem sınırları)<br>• **Redüksiyon & Çözünürlük:** `REDUCTION = (28.4, 28.4, 28.4, 19.0)` |
| **`otonom_dongu.py`** | **Ana Robot Döngüsü (FSM):** Sonsuz otomasyon döngüsünü yürütür: `HOME` -> `GORME` -> Başla Sinyali Bekle -> Renk Oku -> `AL` -> `YUKLE` -> MQTT Renk Gönder -> Başa Dön. | • **Hareket Hız ve İvmesi:** `AyarOtonom.hiz` (1200) ve `ivme` (900)<br>• **Gripper Açıları:** `grip_ac: 31`, `grip_kapat: 110`, `grip_bekle: 0.6`<br>• **Doğrulama & Zaman Aşımı:** `dogrula: True/False`, `renk_deneme: 8`, `hareket_zaman_asimi: 25.0`<br>• **Omuz Kaldırma Payı:** `omuz_kaldir_aci: 12.5` (Küpü kaldırırken çarpmasın) |
| **`renk_algila.py`** | **HSV Kamera Renk Algılayıcı:** Konveyör çıkışındaki küpün rengini (Kırmızı, Yeşil, Mavi) tespit eder. **Kural:** Yapay zeka/YOLO yasaktır, saf OpenCV HSV kullanılır! | • **Renk Karar Mantığı:** `en_cok_renk`, `doluluk_esigi` (%40 piksel doluluğu)<br>• **Iskarta/Hatalı Küp Kuralı:** İstenmeyen renk geldiğinde dönecek değer (örn. Sarı/Siyah küp revizyonu)<br>• **Kamera İndeksi:** `cv2.VideoCapture(0)` veya `(1)` |
| **`renk_kalibrasyon.json`** | **Renk Eşik Değerleri & ROI:** Ortam ışığına göre ayarlanmış HSV min/max aralıklarını ve konveyör üstündeki odaklanılacak alanın (ROI) koordinatlarını saklar. | • **ROI (İlgi Alanı):** `"x", "y", "w", "h"` (Kamera açısı veya küp yeri kayarsa)<br>• **HSV Aralıkları:** `"RED"`, `"GREEN"`, `"BLUE"` alt ve üst bant değerleri (Saha aydınlatması değiştiğinde ilk güncellenecek yer!) |
| **`konumlar.json`** | **Fiziksel Duruş Açıları:** Robot kolun 4 ekleminin (Taban, Omuz, Dirsek, Bilek) ve Gripper açısının önceden öğretilmiş açı değerleridir. | • **`GORME`:** Konveyör üstünü gören bekleme pozisyonu açıları<br>• **`AL`:** Küpü kavrama anındaki eklem ve servo açıları<br>• **`YUKLE`:** Otonom aracın kasasına küpü bıraktığı açılar<br>• **`GECIS` / `ISKARTA`:** Yeni bir revizyonla eklenen geçiş veya ıskarta kutusu açıları |
| **`konum_yonetici.py`** | **Konum Yöneticisi:** `konumlar.json` dosyasını okur, kaydeder ve `robot_link` nesnesine hedef açıları aktarır. | • Yeni durak noktası ekleme (örn: `"ISKARTA"`, `"BEKLEME2"` vb.)<br>• JSON bozulmalarına karşı varsayılan fabrika koordinatları |
| **`arac_haberlesme.py`** | **MQTT Haberleşme Katmanı:** Robot kol ile otonom araç arasındaki kablosuz MQTT köprüsüdür. Paho-MQTT 2.x API kullanır. | • **Broker IP & Port:** `VARSAYILAN_BROKER = "127.0.0.1"` (Sahada kol IP si: örn. `192.168.1.50`)<br>• **Topic Adları:** `TOPIC_YUK = "arac/yuk"`, `TOPIC_BASLA = "robot/basla"`<br>• **Yayın Formatı:** Düz metin (`RED`/`GREEN`/`BLUE`) veya revizyonla istenirse JSON |
| **`otonom_panel.py`** | **Operatör & Ayar Arayüzü:** Tkinter ile yazılmış manuel eksen kontrolü (jog), açı öğretme, kamera ROI seçimi ve HSV canlı kalibrasyon panelidir. | • Yarışma öncesi sahada açıları canlı öğretmek ve `konumlar.json` a kaydetmek için kullanılır.<br>• PLC sinyali gelmeden tek tuşla test/simülasyon başlatmayı sağlar. |

---

# 🚗 BÖLÜM 2: OTONOM ARAÇ SİSTEMİ (`otonomarac/`)

| Dosya Adı | Ne İşe Yarar? (Görevi) | Revizyonda Neler Değişebilir? (Parametre / Değişken) |
| :--- | :--- | :--- |
| **`config.yaml`** | **Merkezi Beyin & Yapılandırma:** Sistemin tüm çalışma parametrelerinin (kamera, hızlar, PID katsayıları, mesafeler, eşikler) toplandığı tek dosyadır. | • **Tüm Revizyonların %80 i SADECE BU DOSYADAN YAPILIR!**<br>• Gaz/Hız değerleri (`throttle`, `max_speed`), PID (`kp, ki, kd`), Tabela bekleme süreleri (`dur_s`), Engel algılama mesafeleri (`stop_dist_m`) |
| **`config_loader.py`** | **Ayar Yükleyici:** `config.yaml` dosyasını hatasız ayrıştırır, eksik parametre varsa güvenli varsayılan değerleri atar. | • YAML sözdizimi doğrulama kuralları ve yeni eklenecek modül parametrelerinin varsayılan değerleri |
| **`main.py`** | **Araç Ana Döngüsü:** Kamera karesini alır -> Şerit bulur -> Görevleri (tabela, ışık, engel) denetler -> PID çıktısını motora aktarır. Klavye kısayollarını dinler. | • **Görev Öncelik Sıralaması:** Trafik ışığı vs. Sollama önceliği<br>• **Klavye Kontrolleri:** `Space` (otonom başlat/durdur), `+/-` (gaz), `r` (reset)<br>• **Döngü Frekansı:** FPS sınırlandırması ve acil durdurma koşulları |
| **`camera.py`** | **RealSense D435/D455 Sürücüsü:** Renkli BGR ve hizalanmış Derinlik (Depth) akışını başlatır. ROI kırpma ve piksel mesafe sorgusu (`get_depth_at`) sağlar. | • **Çözünürlük & FPS:** 640x480, 30 FPS<br>• **Kırpma Payı:** `crop_top_ratio: 0.2917` (Tavan ışıkları ve ufuk çizgisini yok saymak için)<br>• **Pozlama:** Otomatik veya manuel pozlama (`exposure_value`, `gain`) |
| **`vision.py`** | **Şerit & Çizgi Takip Motoru:** OpenCV ile beyaz/sarı şerit çizgilerini tespit eder. Ağırlıklı çizgi merkezini (centroid) bulup merkezden sapmayı (`deviation`) hesaplar. | • **Eşikleme Modu:** `binary` (sabit eşik) veya `adaptive` (ortam ışığına uyumlu)<br>• **Filtreler:** Gauss çekirdeği (`blur_ksize`), morfolojik kapanma boyutu<br>• **Piksel Ağırlıkları:** Çizginin alt/üst bölgelerine verilen önem katsayıları |
| **`controller.py`** | **PID Direksiyon Kontrolcüsü:** `vision.py` den gelen piksel sapmasını direksiyon servo açısına dönüştürür. | • **PID Katsayıları:** `kp` (anlık tepki), `ki` (kalıcı hata giderme), `kd` (salınım/yalpalama sönümleme)<br>• **Anti-Windup:** İntegral doygunluk limiti (`integral_max`), Maksimum direksiyon açısı |
| **`motor.py`** | **ESP Seri Donanım Sürücüsü:** USB üzerinden ESP8266/ESP32 karta `S <aci>`, `F <pwm>`, `B <pwm>`, `X` (dur) komutlarını gönderir. | • **Seri Port & Hız:** `port = "/dev/ttyUSB0"`, `baud = 115200`<br>• **Servo Merkez & Limit:** `servo_center: 90`, `servo_min: 60`, `servo_max: 120`<br>• **Donanımsız Test:** `--dummy` parametresi ile `DummyMotor` modunda çalıştırma |
| **`tabela.py`** | **TensorRT YOLO Tabela Tespiti:** Kameradan gelen görüntüde `tabelaguncel.engine` modelini koşturur. Bounding box, sınıf adı ve güven skoru üretir. | • **Güven Eşiği:** `confidence_threshold` (0.45 - 0.70 arası)<br>• **NMS Eşiği:** Üst üste binen kutuları eleme oranı (`iou_threshold`)<br>• **Model Dosya Yolu:** `.engine` dosyasının konumu |
| **`tabelaguncel.engine`**| **Eğitilmiş Derin Öğrenme Modeli:** 129 tabela görseliyle eğitilmiş ve Jetson TensorRT için optimize edilmiş ikili (binary) model dosyasıdır (117 MB). | • Bu dosya kod değildir, düzenlenemez. Yeni tabela seti gelirse yeniden eğitilip derlenir (veya renk tabanlı fallback yazılır). |
| **`tabela_gorev.py`** | **Tabela Görev Yönetimi:** Algılanan tabelaya göre araca ne yapacağını söyler: Dur tabelasında bekle, hız sınırına uy, sağa/sola mecburi yönü uygula. | • **Tabela Reaksiyonları:** Hangi tabelada kaç saniye durulacağı (`dur_s: 3.0`)<br>• **Hız Limitleri:** 20/30 tabelalarında gaz çarpanları (`hiz_limiti_carpan`)<br>• **Mesafe Filtresi:** Tabelaya ne kadar yaklaşınca aksiyon alınacağı (`tetik_mesafe_m`) |
| **`trafik.py`** | **Trafik Lambası Algılama:** RealSense kamerasından trafik ışığını bulur, Kırmızı/Yeşil rengini ayrıştırır. Kırmızıda durur, yeşilde devam eder. | • **Kırmızı/Yeşil Renk Eşikleri:** HSV renk aralıkları (`red_lower`, `green_upper`)<br>• **Işık Algılama Mesafesi:** `durma_mesafesi_m: 1.2` (Işığa ne kadar kala durulsun)<br>• **Kırmızı Işık Kuralı:** Asla kırmızıda geçilmez (İhlal elenme sebebidir) |
| **`orange_detect_depth.py`**| **Turuncu Duba & Engel Algılama:** Şerit üzerindeki turuncu engelleri HSV ve derinlik sensörüyle tespit eder. Mesafesini hesaplar. | • **Turuncu HSV Sınırları:** Dubanın ton aralığı<br>• **Mesafe Eşiği:** `engel_mesafe_esigi: 0.8` (Metre cinsinden engeli algılama sınırı)<br>• **Piksel Alanı:** Minimum piksel alanı (`min_area: 500`) |
| **`overtake.py`** | **Sollama Manevra Makinesi:** Engel görüldüğünde aracı sol şeride geçirir, engeli geçinceye kadar sürer ve tekrar sağ şeride döndürür. | • **Manevra Süreleri:** Sol şeride çıkış süresi, sol şeritte kalış, sağa dönüş süresi<br>• **Manevra Direksiyon Açıları:** Şerit değiştirirken verilecek sabit sapma açısı<br>• **Sollama İzni:** `sollama_etkin: true/false` (Yasak tabelası varsa iptal) |
| **`park_zemin_renk.py`** | **Park Yeri Renk Eşleştirme:** Robot koldan gelen hedef renk (`RED`/`GREEN`/`BLUE`) ile park cebindeki zemin rengini eşleştirir ve aracı park eder. | • **Zemin HSV Eşikleri:** Zemin renginin algılanma hassasiyeti<br>• **Park Durma Şartı:** Doğru rengi görünce kaç saniye içinde motorun `stop` olacağı<br>• **Tek Görev Kuralı:** Araç doğru renge park edince kilitlenir ve durur. |
| **`colorlink.py`** | **MQTT Araç İstemcisi & MZ80:** Robot kolun yayınladığı `arac/yuk` ve `robot/basla` mesajlarını dinler. MZ80 yükleme sensörü ile hareketi başlatır. | • **İKİ ŞART KURALI:** Hem MQTT renk bilgisi GELECEK hem de MZ80 sensörü küpü GÖRECEK.<br>• **Broker IP:** Robot kolun IP adresi (`broker_ip: "192.168.1.50"`)<br>• **Zaman Aşımı:** Yükleme bekleme süresi sınırı |

---

# ⚡ BÖLÜM 3: HIZLI MÜDAHALE TABLOSU
### *(Yarışma Anında Hakem Söylediğinde Doğrudan İlgili Dosyayı Açın!)*

| Yarışma / Revizyon Durumu | Açılacak Dosya | Yapılacak Değişiklik |
| :--- | :--- | :--- |
| **1. Ortam ışığı değişti / Şerit çizgileri görünmüyor veya titriyor** | `otonomarac/config.yaml` | `vision -> binary_thresh` değerini artır/azalt veya `threshold_mode: adaptive` yap. |
| **2. Robot kol küp rengini yanlış okuyor (Kırmızı/Mavi karışıyor)** | `robotkol/renk_kalibrasyon.json` | İlgili rengin HSV bantlarını açılan `otonom_panel.py` ile yeniden kaydet. |
| **3. Robot kol küpü tutarken konveyöre çarpıyor veya düşürüyor** | `robotkol/konumlar.json` | `AL` durağının `angles` (omuz/dirsek) ve `gripper` kapanma açısını güncelle. |
| **4. Araç virajlarda şeritten çıkıyor veya yalpalanıyor** | `otonomarac/config.yaml` | `controller -> kp` (dönüş gücü) ve `kd` (yalpalama sönümleme) katsayılarını ayarla. |
| **5. Araç dur tabelasında çok az / çok fazla bekliyor** | `otonomarac/config.yaml` | `tabela -> dur_bekleme_suresi` değerini istenen süreye (örn. 3.0 -> 5.0) çek. |
| **6. Kırmızı ışıkta durmuyor / yeşilde kalkmıyor** | `otonomarac/config.yaml` | `trafik -> red_min_pixels` eşiğini düşür veya `stop_distance_m` mesafesini artır. |
| **7. Araç küp yüklendiği halde hareket etmiyor** | `otonomarac/colorlink.py` | MQTT IP bağlantısını kontrol et; MZ80 sensör pin lojiğini (`HIGH/LOW`) doğrula. |
| **8. Sollama manevrası sırasında dubaya çarpıyor** | `otonomarac/config.yaml` | `overtake -> lateral_duration` (sol şeride çıkış süresini) ve algılama mesafesini artır. |
| **9. Robot kol PLC den sinyal geldiği halde başlamıyor** | `robotkol/arduino_robot/arduino_robot.ino` | `SINYAL_PIN A5` giriş voltajını ve optokuplör/röle `K10` kontağını kontrol et. |
| **10. Yanlış renkteki park cebine giriyor** | `otonomarac/config.yaml` | `park -> hsv_tolerans` ve `colorlink` üzerinden alınan küp rengi kontrol edilir. |

---

# 🔌 BÖLÜM 4: SAHA DONANIM & PORT KONTROL LİSTESİ
- **Robot Kol Seri Port:** `/dev/ttyCH341USB0` (Baudrate: `115200`)
- **Otonom Araç ESP Port:** `/dev/ttyUSB0` (Baudrate: `115200`)
- **MQTT Port & Protokol:** Port `1883`, Mosquitto 2.0.11, WebSocket kapalı, Anonymous: `true`
- **PLC Robot Kol Tetikleme:** PLC Çıkış `%Q1.1` -> Röle `K10` -> Arduino Pin `A5` + `GND`
- **Otonom Araç Küp Doğrulama:** Dijital MZ80 Mesafe Sensörü (Küp var = LOW / LED Yanar)
