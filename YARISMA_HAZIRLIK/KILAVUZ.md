# KOVAN ZEKA — TEKNOFEST YARIŞMA SAHASI HIZLI AYAR VE MODİFİKASYON KILAVUZU
> **Hedef Kitle:** Sıfır kodlama ve yazılım tecrübesine sahip takım üyeleri, saha pilotları ve mekanik ekibi.  
> **Temel Amaç:** Yarışma günü hakemlerin talep edeceği tüm görev, hız, renk ve durma değişikliklerini sistemi çökertmeden, saniyeler içinde hatasız olarak uygulamak.

---

## İÇİNDEKİLER
1. [Giriş ve Sıfır Kodlama Felsefesi](#1-giriş-ve-sıfır-kodlama-felsefesi)
2. [Altın Kurallar (YAML ve Python Düzenleme Disiplini)](#2-altın-kurallar-yaml-ve-python-düzenleme-disiplini)
3. [Hızlı Başvuru Matrisi ("Hakem Ne Dedi?" Cheat-Sheet Tablosu)](#3-hızlı-başvuru-matrisi-hakem-ne-dedi-cheat-sheet-tablosu)
4. [Görev Bazlı Ayrıntılı Adım Adım Değişiklik Kılavuzu](#4-görev-bazlı-ayrıntılı-adım-adım-değişiklik-kılavuzu)
   - [Bölüm A: Trafik Lambası Görevi](#bölüm-a-trafik-lambası-görevi)
   - [Bölüm B: Yaya Geçidi Görevi](#bölüm-b-yaya-geçidi-görevi)
   - [Bölüm C: Renkli Park Görevi](#bölüm-c-renkli-park-görevi)
   - [Bölüm D: Seyir Hızı, Gaz ve Motor Güvenliği](#bölüm-d-seyir-hızı-gaz-ve-motor-güvenliği)
   - [Bölüm E: Direksiyon Trim ve Merkezleme (Sağa/Sola Çekme)](#bölüm-e-direksiyon-trim-ve-merkezleme-sağasola-çekme)
   - [Bölüm F: Şerit Takip PID ve Viraj Ayarları](#bölüm-f-şerit-takip-pid-ve-viraj-ayarları)
   - [Bölüm G: Sollama (Turuncu Kutu Engeli)](#bölüm-g-sollama-turuncu-kutu-engeli)
   - [Bölüm H: Robot Kol (Küp Rengi, Gripper, Güvenli Açı)](#bölüm-h-robot-kol-küp-rengi-gripper-güvenli-açı)
5. [Acil Durum Saha Teşhis Rehberi (Hızlı Sorun Çözme)](#5-acil-durum-saha-teşhis-rehberi-hızlı-sorun-çözme)
6. ["Bunu Yaparsanız Sistem Çöker" (En Sık Yapılan 7 Ölümcül Hata ve Kurtarma Yolu)](#6-bunu-yaparsanız-sistem-çöker-en-sık-yapılan-7-ölümcül-hata-ve-kurtarma-yolu)
7. [Kodlama Bilmeyenler İçin Hızlı Doğrulama ve Test Komutları](#7-kodlama-bilmeyenler-için-hızlı-doğrulama-ve-test-komutları)

---

## 1. GİRİŞ VE SIFIR KODLAMA FELSEFESİ

Yarışma sahasında hakemler anlık olarak görev kurallarını değiştirebilir:
- *"Kırmızı ışıkta 3 saniye değil 6 saniye bekleyin."*
- *"Yaya geçidine 100 cm değil 60 cm kala durun."*
- *"Robot koldan renk gelmezse yeşil alana park edin."*
- *"Aracınız şeritte çok yalpalıyor, daha sakin gitsin."*

Bu değişiklikleri yapmak için **yazılımcı olmanıza gerek yoktur**. Projemizdeki neredeyse tüm davranışlar tek bir merkezden, `otonomarac/config.yaml` dosyasından yönetilmektedir.

### Sistemdeki Kritik Dosyalar ve Görevleri:
1. **`otonomarac/config.yaml`**: Sistemin ana kumanda merkezidir. Hız, durma mesafeleri, bekleme süreleri, direksiyon ayarları ve MQTT bağlantı IP'si buradadır. Sahada yapacağınız değişikliklerin **%95'i bu dosyadadır**.
2. **`otonomarac/main.py`**: Otonom sürüşü çalıştıran ana programdır. Sahada klavye kısayollarını (`Space`, `+`, `-`, `0-9`) buradan yönetirsiniz.
3. **`otonomarac/park_zemin_renk.py`**: Park alanındaki zemin renk tonları (kırmızı, yeşil, mavi) fabrikasyon eşiklerini içerir.
4. **`otonomarac/orange_detect_depth.py`**: Sollama yapılacak turuncu kutunun renk ve boyut filtrelerini barındırır.
5. **`robotkol/otonom_dongu.py`**: 4 eksenli robot kolun hızını, tutucu (gripper) sıkma ve açma açılarını belirler.
6. **`robotkol/renk_kalibrasyon.json`**: Robot kolun konveyördeki küpün rengini ayırt etmesini sağlayan renk ayar dosyasıdır.
7. **`robotkol/konumlar.json`**: Robot kolun ezberletilmiş durak noktalarıdır (`GORME`, `AL`, `YUKLE`, `GECIS`).

---

## 2. ALTIN KURALLAR (YAML VE PYTHON DÜZENLEME DİSİPLİNİ)

`config.yaml` dosyasını düzenlerken aşağıdaki 7 kurala **istisnasız** uymalısınız. YAML formatı biçimsel hatalara karşı son derece hassastır; yanlış bir boşluk veya tuş tüm sistemin çalışmasını engeller!

```
+-------------------------------------------------------------------------------+
|                             7 ALTIN SÖZDİZİMİ KURALI                          |
|                                                                               |
|  1. ASLA TAB TUŞUNA BASMAYIN! Sadece boşluk (Space) tuşu kullanın.           |
|  2. İKİ NOKTADAN SONRA BOŞLUK: 'parametre: deger' (iki noktadan sonra 1 boşluk) |
|  3. ONDALIKLARDA NOKTA KULLANIN: '3.5' yazın, ASLA '3,5' (virgül) YAZMAYIN!    |
|  4. AÇIK/KAPALI (BOOLEAN): YAML için 'true' veya 'false' (tırnaksız, küçük)  |
|  5. RENKLER BÜYÜK HARFLE: 'RED', 'GREEN', 'BLUE' (büyük harf, tırnaksız)      |
|  6. LİSTE PARANTEZLERİNİ KORUYUN: '[0, 10]' ve baştaki tireleri (-) silmeyin  |
|  7. BÖLÜM BAŞLIKLARINA BOŞLUK KOYMAYIN: 'trafik:', 'yaya:' tam sola yaslıdır  |
+-------------------------------------------------------------------------------+
```

### Kural 1: Tab Tuşu Kesinlikle Yasaktır!
- Klavyenizdeki `Tab` tuşuna basarak içeri girinti yapmayın.
- YAML dosyasında girintiler **yalnızca iki adet Boşluk (Space) tuşu** ile yapılır.
- Yanlışlıkla `Tab` basarsanız terminal açılışta şu hatayı verir ve araç başlamaz:  
  `yaml.scanner.ScannerError: found character '\t' that cannot start any token`

### Kural 2: İki Nokta Üst Üste (`:`) ve Boşluk Kuralı
- Parametre adı ile değeri arasında mutlaka iki nokta üst üste ve **ardından tam 1 boşluk** olmalıdır.
- **DOĞRU:** `dur_s: 5.0`
- **YANLIŞ:** `dur_s:5.0` (Boşluk yok, YAML parametreyi anlayamaz)
- **YANLIŞ:** `dur_s : 5.0` (İki noktadan önce boşluk bırakılmış)

### Kural 3: Ondalıklı Sayılarda Nokta (`.`) Kullanımı
- Türkçe klavye alışkanlığıyla ondalıklı sayılarda asla virgül (`,`) kullanmayın!
- **DOĞRU:** `gecikme_s: 0.5`
- **YANLIŞ:** `gecikme_s: 0,5` (Virgül kullanılırsa program çöker)

### Kural 4: Açık/Kapalı (Boolean) Değerler
- Bir özelliği açmak veya kapatmak istediğinizde sadece küçük harflerle `true` (açık) veya `false` (kapalı) yazın.
- Asla tırnak içine almayın: `"true"` veya `"false"` yazarsanız sistem bunu yazı zanneder ve kapatamazsınız!

### Kural 5: Renk İsimleri ve Büyük Harf Hassasiyeti
- Hedef renkler daima İNGİLİZCE ve BÜYÜK HARFLERLE yazılmalıdır: `RED`, `GREEN`, `BLUE`.
- Asla `red`, `kırmızı`, `yesil`, `mavi` yazmayın.

### Kural 6: Liste Formatı ve Köşeli Parantezler
- `hue_bantlari` veya `extra_topics` gibi listeleri düzenlerken köşeli parantezleri `[ ... ]` veya satır başındaki tire işaretini `-` silmeyin.

### Kural 7: Bölüm Başlıkları Kuralı
- `trafik:`, `yaya:`, `park:`, `motor:` gibi ana başlıklar daima satırın **en soluna yaslı (0 boşluk)** olmalıdır. Bu başlıkların önüne yanlışlıkla tek bir boşluk dahi koyarsanız o bölüm kaybolur!

---

## 3. HIZLI BAŞVURU MATRİSİ ("HAKEM NE DEDİ?" CHEAT-SHEET TABLOSU)

Aşağıdaki tablo, yarışma esnasında hakemin ağzından çıkabilecek **28 farklı talimatı**, değiştirilecek tam dosyayı, parametre adını, varsayılan değerini, güvenli aralığını ve kuralını özetler:

| # | Fiziksel Belirti / Hakem Talebi | İlgili Dosya | Parametre Adı & Bölüm | Varsayılan | Güvenli Değer Aralığı | Değiştirme Kuralı & Mantığı |
|---|---|---|---|---|---|---|
| **1** | *"Kırmızı ışıkta çok uzakta/yakında duruyor"* | `otonomarac/config.yaml` | `[trafik] -> max_mesafe_cm (Satır ~376)` | `90.0` | `50.0 - 160.0` cm | Daha erken durması için sayıyı büyütün (örn. 130.0). Daha yakına sokulması için küçültün (örn. 70.0). |
| **2** | *"Kırmızı ışıkta yeşil yanmasa bile X saniye sonra kalksın"* | `otonomarac/config.yaml` | `[trafik] -> max_dur_s (Satır ~423)` | `0.0` | `3.0 - 30.0` sn | `0.0` sonsuz beklemedir. Hakem "7 sn bekle geç" derse `7.0` yazın. Yeşil yanmasa da 7 sn sonra kalkar. |
| **3** | *"Kırmızı ışığı görünce aniden durmasın, çizgiye yanaşsın"* | `otonomarac/config.yaml` | `[trafik] -> gecikme_s (Satır ~388)` | `0.5` | `0.0 - 1.5` sn | Kırmızı görüldükten sonra durmadan önce normal gazla ilerleme süresidir. Artırılırsa çizgiye daha çok yanaşır. |
| **4** | *"Yeşil ışık yandığında çok geç kalkıyor, tepkiyi hızlandırın"* | `otonomarac/config.yaml` | `[trafik] -> gec_frames (Satır ~393)` | `25` | `5 - 30` kare | Yeşilin onaylanması için gereken kare sayısıdır. `25` yerine `10` veya `12` yaparsanız yeşile anında kalkış yapar. |
| **5** | *"Trafik ışığı görevini tamamen iptal edin"* | `otonomarac/config.yaml` | `[trafik] -> enable (Satır ~341)` | `true` | `true` / `false` | `enable: false` yapın. Araç kırmızı ışıkları tamamen yok sayar, durmadan geçer. |
| **6** | *"Yaya geçidine çok uzakta/yakında duruyor"* | `otonomarac/config.yaml` | `[yaya] -> dur_mesafe_cm (Satır ~460)` | `100.0` | `50.0 - 130.0` cm | Yaya tabelasına kaç cm kala duracağını belirler. Tabelaya daha yakın durması için küçültün (örn. 70.0). |
| **7** | *"Yaya geçidinde X saniye bekleyin"* | `otonomarac/config.yaml` | `[yaya] -> dur_s (Satır ~473)` | `3.0` | `1.0 - 10.0` sn | Yaya geçidi önünde tam duruş süresidir. Hakem "5 saniye bekle" derse `dur_s: 5.0` yapın. |
| **8** | *"Yaya geçidi çizgilerini aşarken araç sapıtıyor / takılıyor"* | `otonomarac/config.yaml` | `[yaya] -> gec_s (Satır ~478)` | `3.0` | `1.5 - 5.0` sn | Zebra çizgileri kamerayı şaşırtmasın diye kör düz gitme süresidir. Geçit uzunsa süreyi uzatın (örn. 4.5). |
| **9** | *"Yaya geçidinden geçerken araç çok yavaş kalıyor"* | `otonomarac/config.yaml` | `[yaya] -> gec_pwm (Satır ~483)` | `85` | `70 - 130` PWM | Kör düz geçiş sırasındaki motor gaz gücüdür. Rampalı veya sürtünmeli geçitlerde `100` veya `110` yapın. |
| **10** | *"Park tabelasını çok uzaktan görüp erken yavaşlıyor"* | `otonomarac/config.yaml` | `[park] -> tabela_mesafe_cm (Satır ~499)` | `110.0` | `70.0 - 140.0` cm | Park moduna geçiş mesafesidir. Erken yavaşlamaması için küçültün (örn. 85.0). |
| **11** | *"Park kutusunun tam ortasına kadar gitsin, derine park etsin"* | `otonomarac/config.yaml` | `[park] -> dur_mesafe_cm (Satır ~512)` | `25.0` | `10.0 - 35.0` cm | Renkli zeminle ön tampon arası durma mesafesidir. Daha derine girmesi için küçültün (örn. 15.0). |
| **12** | *"Park alanına yaklaşırken araç çok hızlı veya savruluyor"* | `otonomarac/config.yaml` | `[park] -> park_pwm (Satır ~516)` | `80` | `60 - 100` PWM | Renkli alana yanaşma gazıdır. Yavaş ve kontrollü girmesi için `65` veya `70` yapın. |
| **13** | *"Park alanına dönerken direksiyonu çok sert/yumuşak kırıyor"* | `otonomarac/config.yaml` | `[park] -> park_k (Satır ~520)` | `0.125` | `0.08 - 0.25` | Renkli alanı ortalama direksiyon sertliğidir. Keskin dönmesi için artırın (`0.18`), yumuşatmak için düşürün (`0.10`). |
| **14** | *"Araç renkli park kutusunun üzerine çıkınca hemen dursun"* | `otonomarac/config.yaml` | `[park] -> red_kayip_frames (Satır ~524)` | `5` | `3 - 10` kare | Zemin tamponun altına girip kameradan kaybolunca stop etme eşiğidir. Erken durması için `3` yapın. |
| **15** | *"Robot koldan renk gelmezse varsayılan olarak YEŞİL'e park etsin"*| `otonomarac/config.yaml` | `[park] -> varsayilan_renk (Satır ~537)` | `RED` | `RED`, `GREEN`, `BLUE` | Ağ koparsa yedek renktir. Büyük harflerle `GREEN` veya `BLUE` yazın. |
| **16** | *"Aracın başlangıç seyir hızını artırın / azaltın"* | `otonomarac/config.yaml` | `[run] -> start_throttle (Satır ~329)` | `0.3` | `0.20 - 0.50` | Başlangıç gaz oranıdır (%30). Hızlandırmak için `0.35` veya `0.40`, yavaşlatmak için `0.25` yapın. |
| **17** | *"Aracın gidebileceği son hız tavanını sınırlandırın / yükseltin"* | `otonomarac/config.yaml` | `[motor] -> throttle_max_pwm (Satır ~309)` | `300` | `200 - 450` PWM | Motor sürücüsüne gidebilecek en yüksek PWM sınırıdır. Donanımı korur. 450 üzerine çıkmayın! |
| **18** | *"Araç düz yolda sağa çekiyor"* | `otonomarac/config.yaml` | `[motor] -> steering_center (Satır ~297)` | `110` | `95 - 125` derece | Servo merkez açısıdır. **Araç sağa çekiyorsa değeri 2-3 birim AZALTIN** (örn: `110` -> `107`). |
| **19** | *"Araç düz yolda sola çekiyor"* | `otonomarac/config.yaml` | `[motor] -> steering_center (Satır ~297)` | `110` | `95 - 125` derece | Servo merkez açısıdır. **Araç sola çekiyorsa değeri 2-3 birim ARTIRIN** (örn: `110` -> `113`). |
| **20** | *"Direksiyon virajlarda az dönüyor, tekerlekler daha çok kırılsın"*| `otonomarac/config.yaml` | `[motor] -> steering_max_delta (Satır ~301)`| `35` | `25 - 45` derece | Merkezden maksimum sağa/sola sapma açısıdır. Dönüş açısını genişletmek için `40` yapın. |
| **21** | *"Araç düz şeritte aşırı yalpalıyor (balık kuyruğu yapıyor)"* | `otonomarac/config.yaml` | `[controller] -> kp, kd (Satır ~264, ~272)`| `0.9` / `0.1` | `kp: 0.5-0.8`, `kd: 0.15-0.30` | `kp`yi düşürün (örn. `0.65`), `kd`yi artırın (örn. `0.20`). Direksiyon titremesi ve salınım anında kesilir. |
| **22** | *"Araç virajlara girerken hızını otomatik olarak daha çok kıssın"*| `otonomarac/config.yaml` | `[speed] -> speed_gain (Satır ~681)` | `0.35` | `0.15 - 0.60` | Virajda gaz kesme sertliğidir. Virajda daha çok yavaşlaması için artırın (örn. `0.45`). |
| **23** | *"Sollama yaparken öndeki turuncu kutuya çok geç tepki veriyor"* | `otonomarac/config.yaml` | `[overtake] -> trigger_distance_cm (Satır ~613)`| `110.0` | `80.0 - 160.0` cm | Sollama tetikleme mesafesidir. Kutuya daha uzaktan sağa kaçması için artırın (örn. `140.0`). |
| **24** | *"Sollama yaparken sağ şeride yeterince geçemiyor / az kayıyor"* | `otonomarac/config.yaml` | `[overtake] -> lane_shift_px (Satır ~625)` | `464.0` | `380.0 - 550.0` px | Sağ şeride geçmek için hedefe eklenen piksel ofsetidir. Sağ şeride daha çok oturması için artırın (örn. `500.0`). |
| **25** | *"Sollama manevrası yaparken savrulmasın, yavaşlasın"* | `otonomarac/config.yaml` | `[overtake] -> throttle_scale (Satır ~653)`| `0.8` | `0.6 - 1.0` | Sollama sırasındaki hız çarpanıdır. Daha yavaş sollamak için `0.70` yapın (%70 hız). |
| **26** | *"Robot kol küpü tutarken sıkıştıramıyor veya düşürüyor"* | `robotkol/otonom_dongu.py` | `[AyarOtonom] -> grip_kapat (Satır ~40)` | `110` | `95 - 125` derece | Tutucu servo kapanma açısıdır. Küpü daha sıkı kavraması için sayıyı 3-5 birim artırın (örn. `115`). |
| **27** | *"Robot kol küpü konveyörden alırken çarpmaması için kolu kaldırın"*| `robotkol/otonom_dongu.py` | `[AyarOtonom] -> omuz_kaldir_aci (Satır ~48)`| `12.5` | `10.0 - 20.0` derece| Küpü aldıktan sonra güvenli yükselme açısıdır. Çarpmayı önlemek için `15.0` veya `17.0` yapın. |
| **28** | *"Yarışma sahasındaki Wi-Fi / MQTT sunucu IP adresi değişti"* | `otonomarac/config.yaml` | `[colorlink] -> broker (Satır ~557)` | `10.50.58.31` | Geçerli IP | Yeni modem IP'sini tırnaksız olarak yazın (örn: `broker: 192.168.1.150`). |

---

## 4. GÖREV BAZLI AYRINTILI ADIM ADIM DEĞİŞİKLİK KILAVUZU

Aşağıdaki bölümlerde, her bir görev için bir metin düzenleyicide (VS Code, Not Defteri, Gedit veya Nano) dosyayı açıp nasıl değiştireceğiniz karakter karakter gösterilmiştir.

---

### BÖLÜM A: TRAFİK LAMBASI GÖREVİ
Trafik lambası görevi parkurun başlangıcında yer alır. Araç kameranın üst %60'ında kırmızı ışık arar, bulunca durur ve aynı direkte yeşil ışık yanınca otonom kalkış yapar.

- **İlgili Dosya:** `otonomarac/config.yaml`
- **İlgili Bölüm:** `[trafik]` (Satır 338 - 431)

```yaml
# otonomarac/config.yaml içindeki orijinal görünüm:
trafik:
  enable: true              # Satır ~341: Trafik ışığı görevi açık (true) veya kapalı (false)
  ust_bant: 0.60            # Satır ~345: Görüntünün üstten %60'ı taranır (yerdeki kırmızılar elenir)
  ...
  max_mesafe_cm: 90.0       # Satır ~376: Kırmızı ışık algılama mesafesi (cm)
  dur_frames: 3             # Satır ~384: Kırmızı ışığın arka arkaya kaç kare görülmesi gerektiği
  gecikme_s: 0.5            # Satır ~388: Kırmızı görüldükten sonra durmadan önce yaklaşma süresi (sn)
  gec_frames: 25            # Satır ~393: Yeşil ışığın kaç kare onaylanması gerektiği
  max_dur_s: 0.0            # Satır ~423: Emniyet zaman aşımı (0.0 = yeşil yanana kadar bekle)
  once: true                # Satır ~427: Görev tek seferliktir
```

#### Adım Adım Senaryolar:

1. **Hakem Derse ki: *"Kırmızı ışığı 90 cm değil 140 cm'den algılayıp daha uzakta dursun"***
   - `config.yaml` dosyasını açın.
   - `Ctrl + F` ile `[trafik]` altındaki `max_mesafe_cm` aratın (Satır ~376).
   - **Eski Satır:** `  max_mesafe_cm: 90.0`
   - **Yeni Satır:** `  max_mesafe_cm: 140.0`
   - *(Kural: Sadece 90.0 sayısını silin ve 140.0 yazın. Noktaya ve baştaki 2 boşluğa dokunmayın).*

2. **Hakem Derse ki: *"Yeşil ışık devresi bozuldu, kırmızıda 8 saniye bekleyip yeşili beklemeden kalkın"***
   - `config.yaml` içinde `[trafik]` altındaki `max_dur_s` aratın (Satır ~423).
   - **Eski Satır:** `  max_dur_s: 0.0`
   - **Yeni Satır:** `  max_dur_s: 8.0`
   - *(Kural: 0.0 yerine 8.0 yazın. Araç kırmızı ışıkta durduktan 8 saniye sonra yeşil yanmasa dahi emniyetten otonom olarak kalkacaktır).*

3. **Hakem Derse ki: *"Yeşil yandığında hemen kalksın, beklemesin"***
   - `[trafik]` altındaki `gec_frames: 25` satırını bulun (Satır ~393).
   - Değeri `gec_frames: 8` veya `gec_frames: 10` yapın. Böylece yeşil ışık 10 kare (yaklaşık 0.3 saniye) göründüğü an kalkış yapar.

---

### BÖLÜM B: YAYA GEÇİDİ GÖREVİ
Yaya geçidi tabelası (ID 0) görüldüğünde araç durur, belirlenen süre kadar bekler ve ardından zebra çizgileri şerit takibini bozmasın diye direksiyonu tam düz (0.0) sabitleyerek kör geçiş yapar.

- **İlgili Dosya:** `otonomarac/config.yaml`
- **İlgili Bölüm:** `[yaya]` (Satır 452 - 491)

```yaml
# otonomarac/config.yaml içindeki orijinal görünüm:
yaya:
  enable: true              # Satır ~455: Görevi açar/kapatır
  dur_mesafe_cm: 100.0      # Satır ~460: Tabelaya kaç cm kala duracağını belirler
  trigger_frames: 3         # Satır ~464: Tabelanın onaylanması için ardışık kare sayısı
  gecikme_s: 0.0            # Satır ~468: Tabela sonrası yaklaşma süresi
  dur_s: 3.0                # Satır ~473: Yaya çizgisi önünde hareketsiz bekleme süresi (saniye)
  gec_s: 3.0                # Satır ~478: Zebra çizgilerini kör düz geçme süresi (saniye)
  gec_pwm: 85               # Satır ~483: Kör geçiş sırasındaki motor PWM gücü
  once: true                # Satır ~487: Parkur boyu sadece 1 kez çalışır
```

#### Adım Adım Senaryolar:

1. **Hakem Derse ki: *"Yaya geçidinde 3 saniye değil 6 saniye bekleyin"***
   - `config.yaml` dosyasını açın.
   - `[yaya]` başlığı altındaki `dur_s: 3.0` satırını bulun (Satır ~473).
   - **Eski Satır:** `  dur_s: 3.0`
   - **Yeni Satır:** `  dur_s: 6.0`

2. **Hakem Derse ki: *"Yaya geçidi tabelasını daha yakından görsün, tabelaya 60 cm kala dursun"***
   - `[yaya]` başlığı altındaki `dur_mesafe_cm: 100.0` satırını bulun (Satır ~460).
   - Değeri `dur_mesafe_cm: 60.0` yapın.

3. **Hakem Derse ki: *"Yaya geçidi çizgileri çok uzun, araç çizgilerin ortasında kalıyor veya yavaşlıyor"***
   - Geçiş süresini uzatın (Satır ~478): `gec_s: 3.0` -> `gec_s: 4.5`
   - Geçiş motor gücünü artırın (Satır ~483): `gec_pwm: 85` -> `gec_pwm: 105`

---

### BÖLÜM C: RENKLİ PARK GÖREVİ
Park tabelası (ID 5) algılandığında araç hazırlık moduna (`AKTIF`) geçer, zemindeki hedef renkli alanı (RED / GREEN / BLUE) arar, direksiyonu o alana çevirip yaklaşır ve zemin tamponun altına girince kalıcı olarak durur (`ETTI`).

- **İlgili Dosya:** `otonomarac/config.yaml`
- **İlgili Bölüm:** `[park]` (Satır 492 - 549)

```yaml
# otonomarac/config.yaml içindeki orijinal görünüm:
park:
  enable: true              # Satır ~495: Park görevini açar
  tabela_mesafe_cm: 110.0   # Satır ~499: Park tabelasına yaklaşma eşiği (cm)
  dur_mesafe_cm: 25.0       # Satır ~512: Renkli zeminle aradaki durma mesafesi (cm)
  park_pwm: 80              # Satır ~516: Park alanına yaklaşma gazı (PWM)
  park_k: 0.125             # Satır ~520: Renkli alana yönelme direksiyon çarpanı
  red_kayip_frames: 5       # Satır ~524: Zemin tamponun altına girince durma kare toleransı
  varsayilan_renk: RED      # Satır ~537: MQTT'den renk gelmezse yedek hedef renk
  zemin_min_cm: 25.0        # Satır ~541: Geçerli zemin minimum derinlik sınırı
  zemin_max_cm: 350.0       # Satır ~545: Geçerli zemin maksimum derinlik sınırı
```

#### Adım Adım Senaryolar:

1. **Hakem Derse ki: *"Robot koldan renk bilgisi gelmedi/gelmeyecek, varsayılan olarak MAVİ (BLUE) alana park edin"***
   - `config.yaml` içinde `[park]` altındaki `varsayilan_renk` satırını bulun (Satır ~537).
   - **Eski Satır:** `  varsayilan_renk: RED`
   - **Yeni Satır:** `  varsayilan_renk: BLUE`
   - *(Kural: Mutlaka büyük harflerle BLUE yazın, tırnak işareti koymayın).*

2. **Hakem Derse ki: *"Park alanına yanaşırken araç çok hızlı gidiyor ve kutuyu ıskalıyor"***
   - Yanaşma gazını düşürün (Satır ~516): `park_pwm: 80` -> `park_pwm: 65`
   - Direksiyon yönelme hassasiyetini hafif artırın (Satır ~520): `park_k: 0.125` -> `park_k: 0.160`

3. **Hakem Derse ki: *"Park kutusunun içine daha fazla girsin, ön tampon çizginin 15 cm önünde dursun"***
   - `[park]` başlığı altındaki `dur_mesafe_cm: 25.0` satırını bulun (Satır ~512).
   - Değeri `dur_mesafe_cm: 15.0` yapın.

> ⚠️ **DİKKAT — ÇOK KRİTİK UYARI (Aynı İsimli Parametre Tuzağı):**  
> `config.yaml` dosyası içinde `dur_mesafe_cm` parametresi **İKİ AYRI YERDE** tanımlıdır:  
> 1. `yaya:` bölümünde (Satır ~460): `dur_mesafe_cm: 100.0` (Yaya geçidi durma mesafesi)  
> 2. `park:` bölümünde (Satır ~512): `dur_mesafe_cm: 25.0` (Renkli park durma mesafesi)  
> **Park mesafesini değiştirirken MUTLAKA önce `park:` başlığı altına (Satır ~492-549) indiğinizi doğrulayın!** Aksi takdirde yanlışlıkla yaya geçidi mesafesini değiştirirsiniz ve araç park yerine yaya geçidinde hatalı durur!

> **Önemli Renk Eşik Uyarısı (`park_zemin_renk.py`):**  
> Eğer pistteki zemin yeşili veya mavisi kamera tarafından hiç algılanamazsa (pencerede renk görünmüyorsa), HSV renk aralıkları `otonomarac/park_zemin_renk.py` dosyasında Satır 44-50 arasındadır:  
> - `GREEN` (Satır 44): `[((35, 40, 40), (85, 255, 255))]`  
> - `BLUE` (Satır 49): `[((100, 40, 40), (135, 255, 255))]`  
> Mavi koyu kalıyorsa Satır 49'daki `100` değerini `90` yaparak aralığı genişletebilirsiniz.

---

### BÖLÜM D: SEYİR HIZI, GAZ VE MOTOR GÜVENLİĞİ
Aracın parkur boyunca ilerleme hızı iki temel parametreye bağlıdır:
1. `run.start_throttle`: Yola çıkış gaz yüzdesidir (0.0 ile 1.0 arası).
2. `motor.throttle_max_pwm`: Motor sürücüsüne gönderilen donanımsal tavan PWM gücüdür.

- **İlgili Dosya:** `otonomarac/config.yaml`
- **İlgili Bölümler:** `[motor]` (Satır 285-321), `[run]` (Satır 322-337), `[speed]` (Satır 662-695)

#### Adım Adım Hız Ayarları:

1. **Seyir Hızını %30'dan %40'a Çıkarmak İçin:**
   - `config.yaml` içinde `[run]` altındaki `start_throttle` değerini bulun (Satır ~329).
   - **Eski Satır:** `  start_throttle: 0.3`
   - **Yeni Satır:** `  start_throttle: 0.4`

2. **Genel Motor Gücünü Donanımsal Olarak Artırmak İçin:**
   - `[motor]` altındaki `throttle_max_pwm` değerini bulun (Satır ~309).
   - **Eski Satır:** `  throttle_max_pwm: 300`
   - **Yeni Satır:** `  throttle_max_pwm: 350`
   - *(Dikkat: 450 üzerine çıkmayın, motor ve ESC aşırı ısınabilir).*

3. **Canlı Sürüş Esnasında Klavyeden Anlık Gaz Ayarı (`main.py` çalışırken):**
   - Aracın ekran penceresi seçiliyken:
     * `+` tuşuna basarak gazı %5 artırabilirsiniz.
     * `-` tuşuna basarak gazı %5 azaltabilirsiniz.
     * `3` tuşuna basarak anında %30 gaza alabilirsiniz.
     * `0` tuşuna basarak anında motoru boşa alabilirsiniz (gaz 0.0).

---

### BÖLÜM E: DİREKSİYON TRİM VE MERKEZLEME (SAĞA/SOLA ÇEKME)
Ön tekerleklerin tam düz durduğu servo açısına **Direksiyon Trim / Steering Center** denir. Mekanik montaj veya darbe sebebiyle araç düz yolda giderken bir yöne sapıyorsa bu parametre ayarlanır.

- **İlgili Dosya:** `otonomarac/config.yaml`
- **İlgili Bölüm:** `[motor]` (Satır 285-321)

```yaml
motor:
  port: /dev/ttyUSB0        # Satır ~288: Motor sürücü seri portu
  baud: 115200              # Satır ~292: Seri port haberleşme hızı
  steering_center: 110      # Satır ~297: Tam düz direksiyon servo açısı (derece)
  steering_max_delta: 35    # Satır ~301: Merkezden sağa ve sola maksimum dönüş sapması
  steering_invert: false    # Satır ~305: Direksiyon yönü ters mi?
  throttle_max_pwm: 300     # Satır ~309: Maksimum motor PWM tavanı
```

#### Düzeltme Formülü:
- **Araç DÜZ YOLDA SAĞA ÇEKİYORSA:**  
  `steering_center` (Satır ~297) değerini **2 veya 3 birim AZALTIN**.  
  *Örnek:* `steering_center: 110` -> `steering_center: 107`
- **Araç DÜZ YOLDA SOLA ÇEKİYORSA:**  
  `steering_center` (Satır ~297) değerini **2 veya 3 birim ARTIRIN**.  
  *Örnek:* `steering_center: 110` -> `steering_center: 113`
- **Araç Virajlarda Dönemiyor / Servo Sıkışıyorsa:**  
  Dönüş açısı sınırını kontrol edin. `steering_max_delta: 35` (Satır ~301) değerini `38` veya `40` yaparsanız ön tekerlekler daha fazla açıyla döner. Ancak servonun mekanik olarak zorlanmadığından emin olun.

---

### BÖLÜM F: ŞERİT TAKİP PID VE VİRAJ AYARLARI
Araç şeridi ortalamak için PID kontrolcüsü kullanır.
- `kp`: Hatanın büyüklüğüne göre verilen direksiyon tepkisinin sertliğidir.
- `kd`: Yalpalamayı ve savrulmayı frenleyen sönümleme katsayısıdır.

- **İlgili Dosya:** `otonomarac/config.yaml`
- **İlgili Bölüm:** `[controller]` (Satır 260 - 284)

```yaml
controller:
  kp: 0.9                   # Satır ~264: Oransal kazanç (direksiyon sertliği)
  ki: 0.0                   # Satır ~268: İntegral kazanç (daima 0.0 bırakılır)
  kd: 0.1                   # Satır ~272: Türevsel kazanç (savrulma önleyici)
  integral_limit: 1.0       # Satır ~276
  output_limit: 1.0         # Satır ~280
```

#### Belirti ve Çözüm:
1. **Araç Şeritte Sürekli Sağa-Sola Titriyor / Balık Kuyruğu (Yalpalama) Yapıyorsa:**  
   `kp` değeri çok yüksektir veya `kd` düşüktür.  
   - `kp: 0.9` (Satır ~264) değerini `kp: 0.65` yapın.  
   - `kd: 0.1` (Satır ~272) değerini `kd: 0.20` yapın.
2. **Araç Virajı Alamıyor, Virajdan Dışarı Fırlıyorsa:**  
   `kp` değeri düşüktür veya ileriye bakış mesafesi kısadır.  
   - `kp: 0.9` (Satır ~264) değerini `kp: 1.05` yapın.  
   - `vision:` altındaki `lookahead_ratio: 0.55` (Satır ~127) değerini `0.65` yaparak daha ileriye bakmasını sağlayın.
3. **Virajda Şeritten Çıkmamak İçin Otomatik Hız Kesme:**  
   `[speed]` altındaki `speed_gain: 0.35` (Satır ~681) değerini `speed_gain: 0.50` yaparsanız araç viraj eğimi arttıkça gazını otomatik olarak daha sert kısar.

---

### BÖLÜM G: SOLLAMA (TURUNCU KUTU ENGELİ)
Sol şeritte seyrederken öndeki turuncu kutuyu RealSense kamera ve derinlik sensörüyle algılayıp yumuşakça sağ şeride kaçma manevrasıdır.

- **İlgili Dosya:** `otonomarac/config.yaml`
- **İlgili Bölüm:** `[overtake]` (Satır 605 - 661)

```yaml
overtake:
  enable: true                  # Satır ~608: Sollama görevi açık
  trigger_distance_cm: 110.0    # Satır ~613: Kutuya kaç cm kala sağa kaçış başlasın
  lane_shift_px: 464.0          # Satır ~625: Sağ şeride geçmek için uygulanacak yatay kayma (piksel)
  shift_ramp_px: 40.0           # Satır ~629: Direksiyonun yumuşak sağa kırılma rampa hızı
  release_ramp_px: 60.0         # Satır ~633: Sağ şeride oturma rampa hızı
  min_transition_s: 0.4         # Satır ~641: Minimum şerit değiştirme süresi (sn)
  max_transition_s: 2.5         # Satır ~645: Maksimum şerit değiştirme süresi (sn)
  throttle_scale: 0.8           # Satır ~653: Sollama anındaki hız çarpanı (%80 hız)
  once: true                    # Satır ~657: Parkur boyu sadece 1 kez sollama yapar
```

#### Adım Adım Senaryolar:
1. **Kutuya Çok Geç Tepki Veriyorsa (Kutuya Yaklaşıp Çarpma Riski Varsa):**  
   `trigger_distance_cm: 110.0` (Satır ~613) değerini `trigger_distance_cm: 150.0` yapın. Araç 1.5 metre önceden sağa kaçar.
2. **Sağ Şeride Yeterince Oturamıyor / Çizginin Üstünde Kalıyorsa:**  
   `lane_shift_px: 464.0` (Satır ~625) değerini `lane_shift_px: 510.0` yapın.
3. **Manevra Sırasında Çok Hızlı Gidip Savruluyorsa:**  
   `throttle_scale: 0.8` (Satır ~653) değerini `throttle_scale: 0.65` yapın (hızı %65'e çeker).

> **Turuncu Renk Tespiti Sorunu Yaşanırsa (`orange_detect_depth.py`):**  
> Eğer pistteki ışıklandırmadan dolayı turuncu kutu hiç algılanmıyorsa `otonomarac/orange_detect_depth.py` Satır 23'teki `ORANGE_LAB_A_MIN = 130` değerini `120` seviyesine çekerek algılama hassasiyetini artırabilirsiniz.

---

### BÖLÜM H: ROBOT KOL (KÜP RENGİ, GRIPPER, GÜVENLİ AÇI)
Robot kol, konveyörden gelen küpü RealSense/USB kamerasıyla algılar, rengini (`RED`, `GREEN`, `BLUE`) belirler, küpü tutucu (gripper) ile kavrayıp otonom aracın kasasına yükler ve MQTT üzerinden araca `{"renk": "...", "komut": "basla"}` mesajı fırlatır.

#### 1. Gripper Sıkma ve Bırakma Açıları (`robotkol/otonom_dongu.py`)
- **İlgili Dosya:** `robotkol/otonom_dongu.py` (Satır 36 - 50)
- `grip_ac: 31` (Satır ~39): Tutucunun tam açık durduğu servo açısıdır.
- `grip_kapat: 110` (Satır ~40): Tutucunun küpü kavradığı servo açısıdır.
- `omuz_kaldir_aci: 12.5` (Satır ~48): Küpü aldıktan sonra konveyöre veya araç kenarına çarpmamak için kolun yukarı kalktığı güvenlik açısıdır.

*Küp gripper'dan kayıyorsa:* `grip_kapat: 110` (Satır ~40) sayısını `115` veya `118` yapın (daha sıkı sıkar).

#### 2. Küpün Rengi Yanlış Okunuyor veya `UNKNOWN` Kalıyorsa (`robotkol/renk_kalibrasyon.json`)
- **İlgili Dosya:** `robotkol/renk_kalibrasyon.json`
- `doluluk_esigi: 0.4`: Küpün kare içindeki renk piksel oranıdır (%40). Işık loşsa bunu `0.30` yapın.
- `marj: 0.12`: En güçlü renk ile ikinci renk arasındaki fark marjıdır (%12). Kolay renk tespiti için `0.08` yapabilirsiniz.
- Ayrıca `python3 otonom_panel.py` çalıştırarak grafik arayüzden kameraya bakıp rengi tek tıkla öğretebilirsiniz.

#### 3. Robot Kol Hareket Pozisyonları (`robotkol/konumlar.json`)
Robot kolun dört temel durağı vardır:
- `GORME`: Kameranın konveyöre dik baktığı bekleme konumu.
- `AL`: Küpün kavrandığı zemin konumu.
- `YUKLE`: Aracın bagajına bırakıldığı konum.
- `GECIS`: İki hareket arasında çarpmayı önleyen ara hava konumu.
Bu konumları elle değiştirmek yerine terminalden `python3 otonom_panel.py` çalıştırıp el çarkıyla kolu sürerek "KONUMU KAYDET" butonuna basmak en güvenli yoldur.

---

## 5. ACİL DURUM SAHA TEŞHİS REHBERİ (HIZLI SORUN ÇÖZME)

Yarışma esnasında bir aksaklık meydana geldiğinde aşağıdaki hızlı teşhis adımlarını takip edin:

### 1. Araç Kalkış Yapmıyor (Space Tuşuna Basıldı Ama Araç Gitmiyor)
- **Kontrol 1:** Gaz değeri sıfır olabilir. Klavyeden `3` tuşuna basarak gazı %30'a alın veya terminalde `gaz: 0.30` yazdığını görün.
- **Kontrol 2:** `config.yaml` dosyasında `colorlink.require_for_start: true` kalmış olabilir. Bu durumda araç robot koldan MQTT mesajı gelmeden asla kalkış yapmaz!
  * **Hızlı Çözüm:** Terminalden `cd otonomarac && python3 main.py --no-remote` (veya proje kökünden `python3 otonomarac/main.py --no-remote`) komutunu kullanın. Bu komut MQTT zorunluluğunu anında baypas eder.
- **Kontrol 3:** Motor sürücüsünün USB kablosu takılı mı? Terminalde `[motor] baglandi: /dev/ttyUSB0` yazısını kontrol edin. Eğer donanım yoksa tezgahta test için `cd otonomarac && python3 main.py --dummy` (veya proje kökünden `python3 otonomarac/main.py --dummy`) yazın.

### 2. Araç Şeritte Aşırı Yalpalıyor (Balık Kuyruğu Hareketi)
- **Neden:** `kp` katsayısı pist zeminine göre çok yüksektir veya direksiyon gecikmeli toparlıyordur.
- **Hızlı Çözüm:** `otonomarac/config.yaml` dosyasını açın:
  * `controller.kp: 0.9` -> `0.65` yapın.
  * `controller.kd: 0.1` -> `0.20` yapın.
  * Dosyayı kaydedip aracı yeniden başlatın.

### 3. Araç Düz Yolda Sürekli Sağa veya Sola Çekiyor
- **Neden:** Servo merkez açısı (`steering_center`) kaçmıştır.
- **Hızlı Çözüm:** `config.yaml` -> `motor:` bölümüne gidin:
  * Araç **sağa** kayıyorsa: `steering_center: 110` değerini `107` yapın.
  * Araç **sola** kayıyorsa: `steering_center: 110` değerini `113` yapın.

### 4. Kırmızı Işıkta Hiç Durmuyor veya Yeşili Görmüyor
- **Neden 1:** Mesafe yetersiz kalıyordur. `trafik.max_mesafe_cm` değerini `90.0`'dan `130.0`'a çıkarın.
- **Neden 2:** Kamera açısı çok aşağı bakıyorsa kırmızı ışık görüntünün üst %60'ına giremiyordur. `trafik.ust_bant: 0.60` değerini `0.80` yapın.
- **Neden 3:** Işık yeşile dönse de kalkmıyorsa, `trafik.max_dur_s: 6.0` yaparak süre dolunca zorla kalkmasını sağlayın.

### 5. Park Zeminini Iskalaması veya Yanlış Renge Gitmesi
- **Neden 1:** Robot koldan MQTT mesajı ulaşmamıştır ve araç varsayılan renge yöneliyordur. `config.yaml` içinde `varsayilan_renk` ayarını kontrol edin.
- **Neden 2:** Araç park alanına çok hızlı girip savruluyordur. `park_pwm: 80` değerini `park_pwm: 60` yaparak yaklaşma hızını düşürün.
- **Neden 3:** Direksiyon yönelmesi zayıf kalıyordur. `park_k: 0.125` değerini `0.18` yapın.

### 6. Robot Kol Küpü Düşürüyor veya Renk "UNKNOWN" Kalıyor
- **Neden 1:** Gripper yeterince sıkmıyordur. `robotkol/otonom_dongu.py` içindeki `grip_kapat` değerini `110`'dan `116`'ya çıkarın.
- **Neden 2:** Saha aydınlatması değiştiği için küp rengi eşik dışında kalmıştır. `robotkol/renk_kalibrasyon.json` dosyasındaki `doluluk_esigi: 0.4` değerini `0.28`'e indirin.

---

## 6. "BUNU YAPARSANIZ SİSTEM ÇÖKER" (EN SIK YAPILAN 7 ÖLÜMCÜL HATA VE KURTARMA YOLU)

Saha stresinde sıklıkla yapılan 7 kritik hata ve anında kurtarma adımları:

```
+-------------------------------------------------------------------------------+
|                        EN SIK YAPILAN 7 ÖLÜMCÜL HATA                          |
+----+--------------------------------------------+-----------------------------+
| No | Ölümcül Hata                               | Hızlı Kurtarma Yolu         |
+----+--------------------------------------------+-----------------------------+
| 1  | Satır başında TAB tuşuna basmak            | TAB'ı sil, tam 2 SPACE koy  |
| 2  | Ondalıkta virgül kullanmak (örn: 3,0)      | Virgülü silip NOKTA yap: 3.0|
| 3  | İki noktadan sonra boşluk koymamak         | 'dur_s:3.0' -> 'dur_s: 3.0' |
| 4  | Bölüm başlığını (trafik:) içerlek yazmak   | Başlığı EN SOLA (0 boşluk) çek|
| 5  | Boolean değeri tırnak içine almak ("true") | Tırnakları kaldır: true     |
| 6  | Renk adını küçük yazmak (örn: red)         | BÜYÜK HARFLE YAZ: RED       |
| 7  | Dosyayı UTF-8 dışında farklı kaydetmek     | Metin editöründen UTF-8 seç |
+----+--------------------------------------------+-----------------------------+
```

### 1. Hata: Boşluk Yerine Klavyedeki TAB Tuşuna Basmak
- **Hata Çıktısı:** `yaml.scanner.ScannerError: while scanning for the next token found character '\t'`
- **Kurtarma:** Dosyayı açın, değiştirdiğiniz satırın başına gelin, oradaki tüm boşlukları Backspace ile silin ve klavyenin Boşluk (Space) çubuğuna **tam 2 kez** basın.

### 2. Hata: Ondalıklı Sayılarda Virgül (`,`) Kullanmak
- **Hata Örneği:** `dur_s: 3,5` veya `gecikme_s: 0,5`
- **Hata Çıktısı:** `TypeError: float() argument must be a string or a real number`
- **Kurtarma:** Virgülü silip mutlaka nokta koyun: `dur_s: 3.5`.

### 3. Hata: İki Nokta Üst Üste İşaretinden Sonra Boşluk Bırakmamak
- **Hata Örneği:** `dur_s:5.0`
- **Hata Çıktısı:** YAML sözdizimi anahtar-değer ikilisini ayrıştıramaz ve dosyayı geçersiz kabul eder.
- **Kurtarma:** İki nokta üst üste işaretinin hemen sağına bir adet Boşluk (Space) ekleyin: `dur_s: 5.0`.

### 4. Hata: Bölüm Başlıklarının Önüne Yanlışlıkla Boşluk Eklemek
- **Hata Örneği:** `  trafik:` (başlık 2 boşluk içeride kalmış)
- **Hata Çıktısı:** `trafik` bölümü bir önceki bölümün alt elemanı sanılır ve Python kodu `KeyError: 'trafik'` vererek çöker.
- **Kurtarma:** `camera:`, `vision:`, `controller:`, `motor:`, `run:`, `trafik:`, `tabela:`, `yaya:`, `park:`, `colorlink:`, `overtake:`, `speed:` başlıklarını satırın en soluna (0 boşluk) yaslayın.

### 5. Hata: Boolean Değerleri Tırnak İçine Almak
- **Hata Örneği:** `enable: "false"` veya `enable: 'false'`
- **Hata Çıktısı:** Python'da içi dolu her metin `True` kabul edilir (`bool("false") == True`). Dolayısıyla özelliği kapatmak isteseniz bile sistem açık kalmaya devam eder!
- **Kurtarma:** Tırnakları tamamen silin: `enable: false`.

### 6. Hata: Renk Kodlarını Küçük Harfle veya Türkçe Yazmak
- **Hata Örneği:** `varsayilan_renk: red` veya `varsayilan_renk: kırmızı`
- **Hata Çıktısı:** Renk sözlüğü anahtarı bulamaz (`KeyError: 'red'`), araç park alanına kilitlenemez.
- **Kurtarma:** Sadece büyük harflerle `RED`, `GREEN` veya `BLUE` yazın.

### 7. Hata: Dosyayı ANSI / Windows-1254 Kodlamasıyla Kaydetmek
- **Hata Çıktısı:** `UnicodeDecodeError: 'utf-8' codec can't decode byte...`
- **Kurtarma:** Not Defteri veya editörünüzde "Farklı Kaydet" (Save As) seçeneğine tıklayın, alt kısımdaki Kodlama (Encoding) menüsünden **UTF-8** seçerek kaydedin.

---

## 7. KODLAMA BİLMEYENLER İÇİN HIZLI DOĞRULAMA VE TEST KOMUTLARI

`config.yaml` dosyasında değişiklik yaptıktan sonra, aracı piste koymadan önce terminalden aşağıdaki komutları çalıştırarak dosyanızın sağlam olduğunu 2 saniyede doğrulayabilirsiniz:

### 1. YAML Dosyasında Yasaklı "TAB" Tuşu Kontrolü
Terminalde şu komutu kopyalayıp yapıştırın ve Enter'a basın:
```bash
grep -n $'\t' otonomarac/config.yaml && echo "DIKKAT: TAB TUSU BULUNDU! Sistem coker!" || echo "MUKEMMEL: Hicbir satirda TAB tusu yok, dosya temiz."
```
- Ekranda **`MUKEMMEL...`** yazıyorsa dosyanız güvenlidir.
- Ekranda **`DIKKAT...`** yazıyorsa satır numarası belirtilir; o satırdaki Tab karakterini silin.

### 2. config.yaml Sözdizimi ve Yükleme Doğrulaması
Dosyada bir virgül, parantez veya hiyerarşi hatası olup olmadığını test etmek için şu komutları kullanabilirsiniz:

**Proje Modülü ile Doğrulama Komutu (`config_loader`):**  
Yarışma ortamında projenin kendi yükleyicisini çalıştırmak için:
```bash
python3 -c "from otonomarac.config_loader import load_config; cfg = load_config('otonomarac/config.yaml'); print('OK')"
```
- Ekranda **`OK`** çıktısını görüyorsanız dosyanız kod tarafından hatasız okunup sözlüğe dönüştürülmüştür.
- *(Not: Bu komut yarışma aracındaki aktif sanal ortamda veya `pyyaml` kütüphanesi yüklüyken doğrudan `OK` basar).*

**Sıfır Bağımlılık (Harici Kütüphanesiz) Hızlı Standart Kütüphane Kontrolü:**  
Sisteminizde `yaml` kütüphanesi yüklü olmasa dahi hiçbir harici paket gerektirmeden çalışan Python komutu:
```bash
python3 -c "
with open('otonomarac/config.yaml', 'r') as f:
    lines = f.readlines()
assert len(lines) > 500, 'Dosya eksik okunmus olabilir!'
assert not any('\t' in l for l in lines), 'Dosyada yasakli TAB karakteri var!'
print('OK: Standart kutuphane dogrulamasi basarili (TAB yok, dosya yapisi tam).')
"
```

**PyYAML Kurulu İse Doğrudan Sözlük Doğrulaması:**
```bash
python3 -c "import yaml; cfg=yaml.safe_load(open('otonomarac/config.yaml')); print('TEBRIKLER: config.yaml sozluk yapisi hatasiz yuklendi! Toplam bolum:', len(cfg))"
```
- Ekranda `TEBRIKLER... Toplam bolum: 12` çıktısını görüyorsanız sözlük ağacı kusursuzdur!

### 3. Masada / Tezgahta Donanımsız Güvenli Test (Dummy Modu)
Aracı yere koymadan, tekerlekler dönmeden algoritmayı ve pencereleri test etmek için:
```bash
cd otonomarac && python3 main.py --dummy --no-remote
```
- Bu komut motor sürücüsü aramadan (`--dummy`) ve robot koldan MQTT mesajı beklemeden (`--no-remote`) sistemi başlatır.
- `Space` tuşuna basarak otonom modu açıp kapatabilirsiniz.
- Çıkmak için ekrandayken `q` tuşuna basmanız yeterlidir.

### 4. Robot Kol Renk Ayar Dosyasını Doğrulama
```bash
python3 -m json.tool robotkol/renk_kalibrasyon.json > /dev/null && echo "renk_kalibrasyon.json HATASIZ."
```

---
*Kovan Zeka Otonom Araç ve Robotik Takımı — Başarılar Dileriz!*
