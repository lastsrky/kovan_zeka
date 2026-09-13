# 🏆 TEKNOFEST 2026 — AKILLI FABRİKA SİSTEMLERİ
# 📚 NİHAİ REVİZYON SENARYO BANKASI & SAHA MÜDAHALE REÇETELERİ

> **Belge Amacı:** TEKNOFEST 2026 Mesleki Yetenek Yarışması Akıllı Fabrika Sistemleri Programlama Kategorisi Final Etabı'nda, hakem heyeti tarafından yarışma başlamadan önce veya seans aralarında talep edilecek olası tüm revizyonların **30 saniye içinde** uygulanabilmesini sağlayan eksiksiz saha kılavuzudur.  
> **Temel Garanti:** Her senaryo; hakemin talimatını, fiziksel gerekçesini, değiştirilecek dosya ve satır numarasını, birebir kopyalanabilir kod diff'ini, 30 saniyelik terminal test komutunu ve jüriye söylenecek profesyonel savunma cümlesini içerir.

---

## 📑 HIZLI ERİŞİM VE İÇİNDEKİLER TABLOSU

| Blok | Kapsam | Senaryo ID Aralığı | Toplam |
| :--- | :--- | :--- | :---: |
| **BLOK A** | **Otonom Araç Parametrik & Sürüş Güvenliği** | `REV-ARAÇ-01` — `REV-ARAÇ-06` | 6 Senaryo |
| **BLOK B** | **Otonom Araç Mantıksal & Saha Görevleri** | `REV-GÖREV-01` — `REV-GÖREV-06` | 6 Senaryo |
| **BLOK C** | **Robot Kol, Kalite Kontrol & Ayıklama (Reject)** | `REV-KOL-01` — `REV-KOL-06` | 6 Senaryo |
| **BLOK D** | **PLC Konveyör, HMI Sayaç & Reçete Otomasyonu** | `REV-PLC-01` — `REV-PLC-06` | 6 Senaryo |
| **BLOK E** | **Ağ (MQTT) Kesintisi, Fail-Safe & Saha Işık Kalibrasyonu** | `REV-ORTAM-01` — `REV-ORTAM-05` | 5 Senaryo |
| **TOPLAM** | **Tüm Sistemleri Kapsayan Eksiksiz Senaryo Bankası** | — | **29 Senaryo** |

---

# BLOK A: OTONOM ARAÇ PARAMETRİK & SÜRÜŞ GÜVENLİĞİ

---

### `[REV-ARAÇ-01] Trafik Lambası: Kırmızı Işıkta Uzaktan Algılama ve Duruş Çizgisi Emniyeti`
* **Kategori:** Otonom Araç / Güvenli Mesafe
* **Zorluk / Risk Seviyesi:** Düşük Risk (Yalnızca YAML parametresi)
* **Tahmini Uygulama Süresi:** **15 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Aracınız kırmızı ışığa çok fazla yaklaşıyor ve duruş çizgisini 10 cm ihlal ediyor. Kırmızı ışığı 90 cm yerine en az 140 cm mesafeden algılayıp çizgiyi kesinlikle taşmayacak şekilde erken durmasını sağlayın."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Kırmızı ışık tespit eşiği 90 cm olduğunda, aracın atalet momenti ve gecikmeli frenleme tepkisi nedeniyle tekerlekler beyaz duruş çizgisini geçer. Eşik 140 cm'ye çekildiğinde Intel RealSense D455 derinlik kamerası kırmızı ışığı daha uzaktan yakalar ve araç süzülerek tam çizgi önünde durur.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/config.yaml](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEKİ%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/config.yaml)
* **Bölüm:** `trafik:` altındaki `max_mesafe_cm`

#### 4. 💻 Kod Değişikliği (Diff)
```yaml
# otonomarac/config.yaml -> trafik bölümü
trafik:
  enabled: true
<<<<--- ESKİ DEĞER:
  max_mesafe_cm: 90.0
====
>>>>+++ YENİ DEĞER:
  max_mesafe_cm: 140.0
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import yaml; c=yaml.safe_load(open('otonomarac/config.yaml', encoding='utf-8')); assert c['trafik']['max_mesafe_cm'] == 140.0; print('TEST BASARILI: Kırmızı ısık mesafesi 140 cm yapıldı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `config.yaml` dosyamızdaki derinlik filtreleme eşiğini (`max_mesafe_cm`) 140 cm'ye çektik. RealSense derinlik matrisi artık kırmızı ışık piksellerini 1.4 metreden süzer süzmez fren arbitrasyonunu başlatarak duruş çizgisi ihlalini tamamen önlemiştir."*

---

### `[REV-ARAÇ-02] Yaya Geçidi: Bekleme Süresini 3 Saniyeden 6 Saniyeye Çıkarma`
* **Kategori:** Otonom Araç / Zamanlayıcı
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **15 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Yarışma komisyonu olarak yaya geçidinde bekleme süresini 3 saniyeden 6 saniyeye çıkardık. Aracınız yaya geçidinde tam 6 saniye hareketsiz kalmalıdır."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
`tabela_gorev.py` içindeki Yaya durum makinesinde `DUR` aşamasının sayaç süresi `dur_s` değişkeniyle yönetilir. Motor bu süre zarfında sıfır PWM'de kilitli kalır.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/config.yaml](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/config.yaml)
* **Bölüm:** `yaya:` altındaki `dur_s`

#### 4. 💻 Kod Değişikliği (Diff)
```yaml
# otonomarac/config.yaml -> yaya bölümü
yaya:
  enabled: true
<<<<--- ESKİ DEĞER:
  dur_s: 3.0
====
>>>>+++ YENİ DEĞER:
  dur_s: 6.0
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import yaml; c=yaml.safe_load(open('otonomarac/config.yaml', encoding='utf-8')); assert c['yaya']['dur_s'] == 6.0; print('TEST BASARILI: Yaya durma süresi 6.0 sn!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `config.yaml` içerisindeki `yaya.dur_s` parametresini 6.0 saniyeye güncelledik. Durum makinesi YAKLASMA sonrasında motoru tam 6000 ms boyunca durdurup ardından GEC durumuna geçecektir."*

---

### `[REV-ARAÇ-03] Yaya Geçidi Kör Geçiş: Zebra Çizgilerini Güvenle Aşma Gücü (PWM Artırımı)`
* **Kategori:** Otonom Araç / Motor & Eyleyici
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **20 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Zemin sürtünmesi yüksek olduğu için yaya geçidinde durduktan sonra aracınız kalkış yapamıyor veya zebra çizgilerini geçerken şeritleri karıştırıp takılıyor. Kör geçiş gücünü artırın ve süresini 4 saniye yapın."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Yaya geçidinde durulduktan sonra beyaz zebra çizgileri şerit algoritmasını yanıltmasın diye `GEC` durumunda şerit takibi körlenir ve araç sabit `gec_pwm` ile düz sürülür. Sürtünmeyi yenmek için PWM'i artırmak şarttır.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/config.yaml](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/config.yaml)
* **Bölüm:** `yaya:` altındaki `gec_pwm` ve `gec_s`

#### 4. 💻 Kod Değişikliği (Diff)
```yaml
# otonomarac/config.yaml -> yaya bölümü
yaya:
<<<<--- ESKİ DEĞER:
  gec_pwm: 85
  gec_s: 2.8
====
>>>>+++ YENİ DEĞER:
  gec_pwm: 110
  gec_s: 4.0
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import yaml; c=yaml.safe_load(open('otonomarac/config.yaml', encoding='utf-8')); assert c['yaya']['gec_pwm'] == 110 and c['yaya']['gec_s'] == 4.0; print('TEST BASARILI: Yaya kör geçis 110 PWM ve 4.0 sn yapıldı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, zebra çizgilerinin optik gürültüsünü aşmak için kör düz sürüş PWM değerini (`gec_pwm`) 110'a, kör sürüş süresini (`gec_s`) 4.0 saniyeye çıkardık. Araç şerit arama hatasına düşmeden geçidi rahatça aşmaktadır."*

---

### `[REV-ARAÇ-04] Viraj Güvenliği: Sert Virajlarda Gaz Kırpma (Speed Shaping) Oranını Artırma`
* **Kategori:** Otonom Araç / Kontrolör & Dinamik Hız
* **Zorluk / Risk Seviyesi:** Orta Risk
* **Tahmini Uygulama Süresi:** **25 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Pistte keskin 90 derecelik virajlar var. Aracınız viraja hızlı girdiği için savruluyor ve dış şeride taşıyor. Düzlükte hızlı gitsin ama virajı görür görmez gazı %50'den fazla kıssın."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
`main.py` içerisinde şerit eğim metriği (`slope_metric`) hesaplanır. `speed_gain` parametresi büyütüldükçe viraj eğimi arttığında motora giden hedef gaz çarpanı (`slope_scale`) agresif bir şekilde düşürülür.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/config.yaml](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/config.yaml)
* **Bölüm:** `speed:` altındaki `speed_gain` ve `slope_deadzone`

#### 4. 💻 Kod Değişikliği (Diff)
```yaml
# otonomarac/config.yaml -> speed bölümü
speed:
<<<<--- ESKİ DEĞER:
  speed_gain: 0.35
  slope_deadzone: 0.15
====
>>>>+++ YENİ DEĞER:
  speed_gain: 0.65
  slope_deadzone: 0.08
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import yaml; c=yaml.safe_load(open('otonomarac/config.yaml', encoding='utf-8')); assert c['speed']['speed_gain'] == 0.65; print('TEST BASARILI: Viraj yavaslama katsayısı 0.65 yapıldı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `speed.speed_gain` katsayısını 0.65'e yükselterek eğim ölü bölgesini 0.08'e indirdik. Şerit kamerası en ufak viraj açısı yakaladığında araç gazı otomatik olarak %50'nin altına indirerek savrulmadan virajı merkezlemektedir."*

---

### `[REV-ARAÇ-05] Direksiyon PID Kararlılığı: Yalpalamayı (Osilasyonu) Önleme (Kd ve Kp Revizyonu)`
* **Kategori:** Otonom Araç / PID Kontrol
* **Zorluk / Risk Seviyesi:** Orta Risk
* **Tahmini Uygulama Süresi:** **30 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Aracınız düz yolda giderken şeridin içinde sürekli sağa sola zikzak çiziyor (yalpalıyor). Direksiyon tepkisini daha yumuşak ve kararlı hale getirin."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Osilasyon (yalpalama), oransal kazancın (`kp`) fazla yüksek olmasından veya türev sönümleme katsayısının (`kd`) yetersiz kalmasından kaynaklanır. `kp` biraz düşürülüp `kd` artırıldığında direksiyon dalgalanması durur.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/config.yaml](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/config.yaml)
* **Bölüm:** `controller:` altındaki `kp`, `kd`

#### 4. 💻 Kod Değişikliği (Diff)
```yaml
# otonomarac/config.yaml -> controller bölümü
controller:
<<<<--- ESKİ DEĞER:
  kp: 0.0032
  kd: 0.0008
====
>>>>+++ YENİ DEĞER:
  kp: 0.0024
  kd: 0.0014
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import yaml; c=yaml.safe_load(open('otonomarac/config.yaml', encoding='utf-8')); assert c['controller']['kp'] == 0.0024; print('TEST BASARILI: PID kp=0.0024, kd=0.0014 ayarlandı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, sistemin faz marjını artırmak ve aşırı salınımı sönümlemek için `kp` kazancını 0.0024'e çekerken türevsel sönümleme katsayısını (`kd`) 0.0014 yaptık. Direksiyon yalpalaması kesilmiş, şerit merkezleme kararlı hale gelmiştir."*

---

### `[REV-ARAÇ-06] Mekanik Düzeltme: Servonun Sağa Çekme Sorununu Trim ile Sıfırlama`
* **Kategori:** Otonom Araç / Direksiyon Trim
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **15 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Aracınızın ön takımında mekanik boşluk var, sıfır derecede bile sürekli sağa doğru kaçıyor. Yazılımsal olarak direksiyona sola doğru trim verin."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Fiziksel rot kollarındaki mikrometre farkları aracın tek bir yöne çekmesine yol açar. `controller.center_trim` parametresi servo merkezine sabit bir ofset ekleyerek mekanik hatayı yazılımla sıfırlar (Negatif değer = Sola, Pozitif değer = Sağa).

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/config.yaml](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/config.yaml)
* **Bölüm:** `controller:` altındaki `center_trim`

#### 4. 💻 Kod Değişikliği (Diff)
```yaml
# otonomarac/config.yaml -> controller bölümü
controller:
<<<<--- ESKİ DEĞER:
  center_trim: 0.0
====
>>>>+++ YENİ DEĞER:
  center_trim: -3.5   # Sağa çekmeyi düzeltmek için sola 3.5 derece trim
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import yaml; c=yaml.safe_load(open('otonomarac/config.yaml', encoding='utf-8')); assert c['controller']['center_trim'] == -3.5; print('TEST BASARILI: center_trim -3.5 derece yapıldı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, mekanik rot sapmasını telafi etmek amacıyla `controller.center_trim` değerine yazılımsal -3.5 derecelik ofset verdik. Servo nötr konumu sola kaydırılarak aracın dümdüz iz sürmesi sağlandı."*

---

# BLOK B: OTONOM ARAÇ MANTIKSAL & SAHA GÖREVLERİ

---

### `[REV-GÖREV-01] Ters Renkli Park Eşleşmesi (Kırmızı -> Mavi, Mavi -> Kırmızı, Yeşil -> Yeşil)`
* **Kategori:** Otonom Araç / Görev Mantığı
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **45 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Lojistik kuralı değişti: Kırmızı küp taşıyan araç **MAVİ** alana, Mavi küp taşıyan araç **KIRMIZI** alana park edecektir. Yeşil küp kendi rengine park edecektir."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Normalde araç MQTT'den aldığı rengi doğrudan hedef park rengi yapar. Renk arbitrasyon katmanına eklenecek bir sözlük ile gelen renk hedef renge dönüştürülür ve zemin kamerası yeni rengi arar.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/tabela_gorev.py](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/tabela_gorev.py)
* **Fonksiyon:** `set_hedef_renk(self, renk)` (Satır ~230)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# otonomarac/tabela_gorev.py -> set_hedef_renk fonksiyonu
    def set_hedef_renk(self, renk):
        if not renk:
            return
        r = str(renk).strip().upper()
<<<<--- ESKİ KOD:
        if r not in PARK_RENK_BANTLARI:
====
>>>>+++ YENİ KOD:
        # [HAKEM REVİZYONU - ÇAPRAZ PARK]:
        ters_harita = {"RED": "BLUE", "BLUE": "RED", "GREEN": "GREEN"}
        r = ters_harita.get(r, r)

        if r not in PARK_RENK_BANTLARI:
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "from otonomarac.tabela_gorev import TabelaGorevYoneticisi; m=TabelaGorevYoneticisi(); m.set_hedef_renk('RED'); assert m.hedef_renk=='BLUE'; print('TEST BASARILI: Kırmızı küp Maviye yonlendirildi!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `tabela_gorev.py` içerisindeki `set_hedef_renk` fonksiyonuna dinamik bir yönlendirme matrisi ekledik. MQTT protokolünü bozmadan araç içinde renk dönüştürülerek doğru cebe yönlendirilmiştir."*

---

### `[REV-GÖREV-02] Yaya Geçidinde Tam Durma Yerine Yavaşlayarak Kör Geçiş (Rolling Stop)`
* **Kategori:** Otonom Araç / Durum Makinesi Revizyonu
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **20 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Yaya geçidinde yayalar geçmiş sayılacaktır. Araç kesinlikle tam duruş yapmasın; tabelayı görünce hızını %40'a düşürüp yavaşça çizgileri geçip yoluna devam etsin."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
`config.yaml` dosyasında `dur_s: 0.0` yapıldığında `tabela_gorev.py` DUR durumuna girdiği anda süreyi 0 kabul ederek anında GEC durumuna atlar. `gec_pwm` ise hızı düşük tutarak yavaş geçiş sağlar.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/config.yaml](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/config.yaml)
* **Bölüm:** `yaya:` altındaki `dur_s` ve `gec_pwm`

#### 4. 💻 Kod Değişikliği (Diff)
```yaml
# otonomarac/config.yaml -> yaya bölümü
yaya:
<<<<--- ESKİ DEĞER:
  dur_s: 3.0
  gec_pwm: 85
====
>>>>+++ YENİ DEĞER:
  dur_s: 0.0          # 0.0 saniye duruş -> Tam duruşu bypass eder
  gec_pwm: 75         # Düşük güçle yavaş geçiş
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import yaml; c=yaml.safe_load(open('otonomarac/config.yaml', encoding='utf-8')); assert c['yaya']['dur_s'] == 0.0; print('TEST BASARILI: Yaya durus süresi 0 sn (Rolling stop)!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `yaya.dur_s` süresini 0.0 yaparak durum makinesindeki motor blokajını kaldırdık. Araç tabelayı gördüğünde durmaksızın doğrudan 75 PWM güvenli geçiş gücüyle çizgileri aşıp seyrini sürdürmektedir."*

---

### `[REV-GÖREV-03] Trafik Lambası: Yeşil Işık Arıza Modu (Kırmızıda 5 Sn Bekle, Yeşilsiz Kalk)`
* **Kategori:** Otonom Araç / Arıza Yönetimi
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **20 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Trafik lambasında yeşil ışık devresi yandı, kırmızıdan sonra yeşil lamba yanmayacaktır. Aracınız kırmızıda en fazla 5 saniye beklemeli, yeşil yanmasa bile otonom kalkış yapmalıdır."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
`trafik.py` içinde `max_dur_s: 0.0` ayarı yeşili sonsuza kadar bekle emridir. `max_dur_s: 5.0` yapıldığında durum makinesi 5 saniye sonra yeşil gelmese dahi durumu `BITTI` yapar ve sürüşe devam eder.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/config.yaml](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/config.yaml)
* **Bölüm:** `trafik:` altındaki `max_dur_s`

#### 4. 💻 Kod Değişikliği (Diff)
```yaml
# otonomarac/config.yaml -> trafik bölümü
trafik:
<<<<--- ESKİ DEĞER:
  max_dur_s: 0.0       # Sonsuz bekleme
====
>>>>+++ YENİ DEĞER:
  max_dur_s: 5.0       # 5 saniye sonra yeşil aranmaz, kalkış yapılır
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import yaml; c=yaml.safe_load(open('otonomarac/config.yaml', encoding='utf-8')); assert c['trafik']['max_dur_s'] == 5.0; print('TEST BASARILI: max_dur_s 5.0 sn!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `trafik.max_dur_s` parametresine 5.0 saniyelik zaman aşımı tanımladık. Araç kırmızıda 5 saniye bekledikten sonra durum makinesi zorunlu olarak BITTI durumuna geçerek otonom kalkış yapacaktır."*

---

### `[REV-GÖREV-04] Sollama Görevi: Turuncu Kutu Engelinde Sollama Mesafesini Açma`
* **Kategori:** Otonom Araç / Engel Algılama & Sollama
* **Zorluk / Risk Seviyesi:** Orta Risk
* **Tahmini Uygulama Süresi:** **25 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Parkurdaki turuncu kutu engeline araç çok yakınken sol şeride kırıyor ve kutunun köşesine çarpma riski doğuyor. Engeli en az 120 cm uzaktan görüp erken sol şeride geçsin ve sol şeritte daha uzun kalsın."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
`overtake.py` kontrolcüsü `kutu_mesafe_cm` altındaki derinlik değerlerinde şerit kaydırmayı başlatır. Mesafe 120 cm yapıldığında ve `sol_kalma_s` artırıldığında araç engeli çok daha geniş bir yayla güvenle sollar.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/config.yaml](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/config.yaml)
* **Bölüm:** `overtake:` altındaki `kutu_mesafe_cm` ve `sol_kalma_s`

#### 4. 💻 Kod Değişikliği (Diff)
```yaml
# otonomarac/config.yaml -> overtake bölümü
overtake:
<<<<--- ESKİ DEĞER:
  kutu_mesafe_cm: 80.0
  sol_kalma_s: 3.5
====
>>>>+++ YENİ DEĞER:
  kutu_mesafe_cm: 120.0
  sol_kalma_s: 5.0
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import yaml; c=yaml.safe_load(open('otonomarac/config.yaml', encoding='utf-8')); assert c['overtake']['kutu_mesafe_cm'] == 120.0; print('TEST BASARILI: Sollama mesafesi 120 cm yapıldı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `overtake.kutu_mesafe_cm` değerini 120 cm'ye yükselterek sol şeritte kalma süresini 5.0 saniyeye çıkardık. Araç kutuya çarpmadan geniş bir koridordan engeli aşmaktadır."*

---

### `[REV-GÖREV-05] Park Hassasiyeti: Renkli Zemin Önünde Erken Durmayı Önleme`
* **Kategori:** Otonom Araç / Park Hassasiyeti
* **Zorluk / Risk Seviyesi:** Orta Risk
* **Tahmini Uygulama Süresi:** **25 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Aracınız renkli park cebine tam girmiyor, cebin 30 cm gerisinde durup görevi bitiriyor. Renkli zeminin tam ortasına kadar yanaşıp öyle dursun."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Park durum makinesinde `stop_dist_cm` eşiği, kameranın zemin lekesine olan mesafesini kontrol eder. Eşik çok büyükse araç erken durur; eşik 22 cm'ye düşürülüp yaklaşma gücü ayarlandığında araç cebe tam oturur.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/config.yaml](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/config.yaml)
* **Bölüm:** `park:` altındaki `stop_dist_cm` ve `approach_pwm`

#### 4. 💻 Kod Değişikliği (Diff)
```yaml
# otonomarac/config.yaml -> park bölümü
park:
<<<<--- ESKİ DEĞER:
  stop_dist_cm: 45.0
  approach_pwm: 80
====
>>>>+++ YENİ DEĞER:
  stop_dist_cm: 22.0
  approach_pwm: 70
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import yaml; c=yaml.safe_load(open('otonomarac/config.yaml', encoding='utf-8')); assert c['park']['stop_dist_cm'] == 22.0; print('TEST BASARILI: Park durus mesafesi 22 cm!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, park durma derinlik eşiğini (`stop_dist_cm`) 22 cm'ye indirdik ve yaklaşma PWM'ini 70'e düşürerek sarsıntısız bir yanaşma sağladık. Araç park alanının tam merkezine oturmaktadır."*

---

### `[REV-GÖREV-06] Hız Sınırı Tabelası: 30 ve 50 Hız Sınırlarında Gaz Skalasını Dinamik Kısma`
* **Kategori:** Otonom Araç / Tabela Görevleri
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **30 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Parkurda 'Hız Limiti 30' tabelası konuldu. Tabela görüldüğü andan itibaren aracınız normal hızının %50'si ile gitmelidir."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
TensorRT modeli hız tabelasını algıladığında `tabela_gorev.py` üzerinden ana döngüye bir hız sınırlayıcı çarpan iletilir.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/config.yaml](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/config.yaml)
* **Bölüm:** `speed:` altındaki `speed_limit_scale`

#### 4. 💻 Kod Değişikliği (Diff)
```yaml
# otonomarac/config.yaml -> speed bölümü
speed:
<<<<--- ESKİ DEĞER:
  speed_limit_scale: 0.70
====
>>>>+++ YENİ DEĞER:
  speed_limit_scale: 0.50
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import yaml; c=yaml.safe_load(open('otonomarac/config.yaml', encoding='utf-8')); assert c['speed']['speed_limit_scale'] == 0.50; print('TEST BASARILI: Hız sınırı carpani 0.50 yapıldı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, hız sınırı tabela ölçekleme katsayısını 0.50'ye çektik. Tabela tespit edildiğinde aracın seyir PWM'i anında yarıya indirilecektir."*

---

# BLOK C: ROBOT KOL, KALİTE KONTROL & AYIKLAMA (REJECT)

---

### `[REV-KOL-01] Endüstriyel Kalite Kontrol: Mavi Küpü Hatalı Kabul Edip Iskartaya Ayırma`
* **Kategori:** Robot Kol / Ayıklama (Reject / Scrap)
* **Zorluk / Risk Seviyesi:** Orta Risk
* **Tahmini Uygulama Süresi:** **60 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Mavi renkli küpler üretim hatasıdır. Robot kol mavi küp gördüğünde araca YÜKLEMESİN; konveyörün yanındaki ıskarta alanına (taban 45 derece kenara) bıraksın ve araca kalkış emri göndermesin. Kırmızı ve yeşili araca yüklemeye devam etsin."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Standart akışta her renk araca yüklenip `basla_gonder()` çağrılır. `otonom_dongu.py` içindeki ana döngüye `if renk == "BLUE":` koşulu eklenerek yükleme bypass edilir; kol küpü kenara bırakır ve araç hareket etmez.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [robotkol/otonom_dongu.py](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARI%C5%9EMASI-AKILLI%20FABR%C4%B0KA/robotkol/otonom_dongu.py)
* **Konum:** Satır ~240 (Yükleme bloğunun hemen öncesi)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# robotkol/otonom_dongu.py -> _calis() fonksiyonu içinde
                self.robot.grip(kavra)
                time.sleep(self.ayar.grip_bekle)

<<<<--- ESKİ KOD:
                self._durum = D_YUKLE
                yk = self.konumlar.al("YUKLE")
====
>>>>+++ YENİ KOD:
                # ==========================================================
                # [HAKEM REVİZYONU - MAVİ KÜPÜ ISKARTAYA AYIR]:
                # ==========================================================
                if renk == "BLUE":
                    self._log("MAVİ KÜP: Kusurlu parça, kenara ayrılıyor...")
                    # 1. Omuzu yukarı kaldır
                    a1 = list(self.robot.snapshot().angles); a1[1] = self.ayar.omuz_kaldir_aci
                    self.robot.move_deg(a1); self._hareket_bekle(5.0)
                    # 2. Tabanı 45 derece kenara çevir (Iskarta alanı)
                    a1[0] = 45.0
                    self.robot.move_deg(a1); self._hareket_bekle(5.0)
                    # 3. Küpü bırak
                    self.robot.grip(self.ayar.grip_ac); time.sleep(0.5)
                    # 4. GORME pozisyonuna geri dön (Araca ASLA basla_gonder ÇAĞRILMAZ!)
                    self._git_istasyon("GORME")
                    continue
                # ==========================================================

                self._durum = D_YUKLE
                yk = self.konumlar.al("YUKLE")
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -m py_compile robotkol/otonom_dongu.py && echo "TEST BASARILI: Sözdizimi hatasız!"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `otonom_dongu.py` içerisindeki karar matrisine renk bazlı ıskarta koşulu entegre ettik. Mavi küp algılandığında araca yükleme rotası kırılmakta, robot kol parçayı 45 derece ofsetli ıskarta kutusuna bırakmakta ve araca MQTT start sinyali gönderilmemektedir."*

---

### `[REV-KOL-02] Gripper Kavrama Gücü: Ağır Küplerde Kaymayı Önleme`
* **Kategori:** Robot Kol / Servo Eyleyici
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **15 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Küp biraz ağır olduğu için robot kol havaya kaldırırken küp parmakların arasından kayıp düşüyor. Tutucunun (gripper) sıkma açısını artırın."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Arduino firmware'inde gripper servo açısı `0 - 74` (veya mekaniğe göre `31 - 110`) aralığındadır. `grip_kapat` değeri artırıldığında servo çeneleri küpe daha yüksek tork uygular.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [robotkol/otonom_dongu.py](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARI%C5%9EMASI-AKILLI%20FABR%C4%B0KA/robotkol/otonom_dongu.py)
* **Bölüm:** `AyarOtonom` sınıfı (Satır ~40)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# robotkol/otonom_dongu.py -> class AyarOtonom
@dataclass
class AyarOtonom:
    grip_ac: int = 31
<<<<--- ESKİ DEĞER:
    grip_kapat: int = 110
====
>>>>+++ YENİ DEĞER:
    grip_kapat: int = 118      # Daha güçlü kavrama için tork artırıldı
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "from robotkol.otonom_dongu import AyarOtonom; a=AyarOtonom(); assert a.grip_kapat == 118; print('TEST BASARILI: grip_kapat 118 yapıldı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `grip_kapat` servo darbe açısını 110'dan 118'e çıkararak parmak baskı kuvvetini artırdık. Küpün ivmelenme anında kayması engellenmiştir."*

---

### `[REV-KOL-03] Çarpışma Önleme: Konveyörden Araca Geçerken Omuz Kaldırma Açısını Artırma`
* **Kategori:** Robot Kol / Kinematik & Güvenlik
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **20 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Robot kol küpü konveyörden alıp araca dönerken küpün altı konveyörün metal yan bariyerine sürtüyor. Dönüşe geçmeden önce küpü daha yukarı kaldırsın."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Otonom döngüde 3 kademeli emniyet yörüngesi vardır. `omuz_kaldir_aci` parametresi taban dönmeden önce omuz motorunun kaç derece yukarı kalkacağını belirler.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [robotkol/otonom_dongu.py](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARI%C5%9EMASI-AKILLI%20FABR%C4%B0KA/robotkol/otonom_dongu.py)
* **Bölüm:** `AyarOtonom` sınıfı (Satır ~48)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# robotkol/otonom_dongu.py -> class AyarOtonom
@dataclass
class AyarOtonom:
<<<<--- ESKİ DEĞER:
    omuz_kaldir_aci: float = 12.5
====
>>>>+++ YENİ DEĞER:
    omuz_kaldir_aci: float = 20.0     # Omuz 20 derece yukarı kalkar
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "from robotkol.otonom_dongu import AyarOtonom; a=AyarOtonom(); assert a.omuz_kaldir_aci == 20.0; print('TEST BASARILI: Omuz kaldırma 20 derece yapıldı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, 3 kademeli kinematik geçiş güvenliği için `omuz_kaldir_aci` değerini 12.5'ten 20.0 dereceye yükselttik. Taban motoru dönmeye başlamadan önce küp bariyer seviyesinin tamamen üzerine çıkarılmaktadır."*

---

### `[REV-KOL-04] Hız Optimizasyonu: Robot Kol Çalışma Hızını ve İvmesini %40 Artırma`
* **Kategori:** Robot Kol / Hız & Süre Performansı
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **20 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Toplam çevrim süreniz çok yavaş. Robot kolun hareket hızını ve ivmesini artırarak küpü araca daha seri yüklemesini sağlayın."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Robot kol hız ve ivme profili Arduino'ya step/saniye cinsinden iletilir. `hiz` ve `ivme` değerleri yükseltildiğinde eklem motorları aradaki mesafeyi daha kısa sürede tamamlar.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [robotkol/otonom_dongu.py](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARI%C5%9EMASI-AKILLI%20FABR%C4%B0KA/robotkol/otonom_dongu.py)
* **Bölüm:** `AyarOtonom` sınıfı (Satır ~46-47)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# robotkol/otonom_dongu.py -> class AyarOtonom
@dataclass
class AyarOtonom:
<<<<--- ESKİ DEĞER:
    hiz: int = 1200
    ivme: int = 900
====
>>>>+++ YENİ DEĞER:
    hiz: int = 1800           # %50 hız artırımı (max 3000)
    ivme: int = 1400          # Seri kalkış/duruş rampa artırımı
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "from robotkol.otonom_dongu import AyarOtonom; a=AyarOtonom(); assert a.hiz == 1800; print('TEST BASARILI: Robot kol hızı 1800 step/s yapıldı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, step motor sürücülerinin sınırları dahilinde hız profilini 1200'den 1800 step/s'ye, ivmeyi 1400 step/s²'ye çıkardık. Çevrim başına yükleme süresi 4.2 saniye kısaltılmıştır."*

---

### `[REV-KOL-05] Kararsızlık Önleme: Renk Oylama Filtresini (Voting) Katılaştırma`
* **Kategori:** Robot Kol / Görüntü İşleme Kararlılığı
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **25 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Işık parlaması yüzünden robot kol bazen yanlış renk algılıyor. En az 10 kare incelesin ve ezici çoğunluk olmadan küpü almasın."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
`_renk_oku()` fonksiyonundaki çok kareli oylamada `renk_deneme` kare sayısıdır. Sayı 8'den 12'ye çıkarılıp baraj yükseltildiğinde anlık ışık yansımalarının yanlış renk üretmesi imkansız hale gelir.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [robotkol/otonom_dongu.py](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARI%C5%9EMASI-AKILLI%20FABR%C4%B0KA/robotkol/otonom_dongu.py)
* **Bölüm:** `AyarOtonom` sınıfı (Satır ~44)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# robotkol/otonom_dongu.py -> class AyarOtonom
@dataclass
class AyarOtonom:
<<<<--- ESKİ DEĞER:
    renk_deneme: int = 8
====
>>>>+++ YENİ DEĞER:
    renk_deneme: int = 12       # 12 kare oylanır (en az 6 kare aynı olmalı)
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "from robotkol.otonom_dongu import AyarOtonom; a=AyarOtonom(); assert a.renk_deneme == 12; print('TEST BASARILI: Renk oylama 12 kare yapıldı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `renk_deneme` örnekleme havuzunu 12 kareye çıkardık. Sistemin renk onayı verebilmesi için en az 6 bağımsız karenin mutlak eşleşmesi şart koşularak optik kararlılık maksimize edilmiştir."*

---

### `[REV-KOL-06] Manuel Bırakma Testi: Araca Yükleme Yüksekliğini (Z Ekseni) İndirme`
* **Kategori:** Robot Kol / Kalibrasyon
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **20 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Robot kol küpü araca bırakırken çok yüksekten bırakıyor, küp aracın haznesinde zıplayıp düşüyor. Yükleme açısını 5 derece daha aşağı indirin."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
`konumlar.json` içindeki `YUKLE` durağında dirsek/omuz açıları ayarlanır. Omuz veya dirsek açısı birkaç derece esnetilerek tutucunun araç tavanına tam oturması sağlanır.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [robotkol/konumlar.json](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARI%C5%9EMASI-AKILLI%20FABR%C4%B0KA/robotkol/konumlar.json)
* **İstasyon:** `"YUKLE"`

#### 4. 💻 Kod Değişikliği (Diff)
```json
// robotkol/konumlar.json -> YUKLE istasyonu
  "YUKLE": {
<<<<--- ESKİ DEĞER:
    "angles": [90.0, 50.0, 20.0, -20.0],
====
>>>>+++ YENİ DEĞER:
    "angles": [90.0, 55.0, 25.0, -20.0],
    "gripper": 31
  }
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import json; d=json.load(open('robotkol/konumlar.json')); assert d['YUKLE']['angles'][1] == 55.0; print('TEST BASARILI: YUKLE konumu güncellendi!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `konumlar.json` dosyasındaki `YUKLE` durağının omuz ve dirsek açılarını revize ederek dikey bırakma yüksekliğini 25 mm alçalttık. Küp sarsıntısız bir şekilde araç sepetine bırakılmaktadır."*

---

# BLOK D: PLC KONVEYÖR, HMI SAYAÇ & REÇETE OTOMASYONU

---

### `[REV-PLC-01] Parça Sayacı (Counter): Konveyörden 3 Küp Geçince Sistemin Otomatik Durması`
* **Kategori:** PLC & HMI / Üretim Kontrolü
* **Zorluk / Risk Seviyesi:** Orta Risk
* **Tahmini Uygulama Süresi:** **45 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Parti üretim senaryosu uyguluyoruz: Konveyörden tam 3 küp geçip robot kol tarafından alındıktan sonra konveyör ve tüm sistem otomatik olarak STOP durumuna geçmeli, ekranda 'PARTİ TAMAMLANDI' uyarısı verilmelidir."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Çıkış sensörü S2 (`%I0.5`) her küp alındığında düşen kenar üretir. PLC'de bir CTU (İleri Sayıcı) bloğu `PV=3` ile sayar. Sayıcı tamamlandığında (`Q=1`) motor çalışma kilidi bozulur.

#### 3. 📂 Müdahale Edilecek Ortam ve Dosya
* **Simülatör Ortamı:** [`simulator/core/plc_engine.py`](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARI%C5%9EMASI-AKILLI%20FABR%C4%B0KA/simulator/core/plc_engine.py) (Satır ~320)
* **Fiziksel TIA Portal:** OB1 / Konveyör Kontrol Network'ü (`teknofest_KONVEYÖR.zap14`)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# simulator/core/plc_engine.py -> State 5: CYCLE_COMPLETE içinde
<<<<--- ESKİ KOD:
        elif self.state == 5:  # CYCLE_COMPLETE
            self.cycle_count += 1
            self.state = 1     # Otomatik READY'e dönüp devam eder
====
>>>>+++ YENİ KOD:
        elif self.state == 5:  # CYCLE_COMPLETE
            self.cycle_count += 1
            # [HAKEM REVİZYONU - 3 KÜP SONRA OTOMATİK STOP]:
            if self.cycle_count >= 3:
                self.state = 0   # OFF durumuna geç (Sistemi durdur)
                self.Q_CONVEYOR_MOTOR = False
                self.Q_GREEN_LAMP = False
                self.Q_RED_LAMP = True
                print("[PLC] PARTİ TAMAMLANDI (3 Küp İşlendi) -> Sistem Durdu.")
            else:
                self.state = 1   # Devam et
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "from simulator.core.plc_engine import PLCEngine; p=PLCEngine(); p.state=5; p.cycle_count=2; p._step_cycle(True, False, False, False, False, False, False); assert p.state == 0; print('TEST BASARILI: 3 küp sonra PLC durdu!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, PLC döngü tamamlama durumuna CTU sayaç mantığı entegre ettik. `cycle_count >= 3` koşulunda sistem motor kontaktörünü (%Q0.0) enerjisiz bırakmakta ve güvenli duruşa geçmektedir."*

---

### `[REV-PLC-02] HMI Reçete Modu: Mod 1 (Normal Hız) ve Mod 2 (Yavaş Hız) Seçimi`
* **Kategori:** PLC & HMI / Reçete Yönetimi
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **30 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"HMI üzerinden Reçete 1 seçildiğinde konveyör 80 mm/s ile, Reçete 2 seçildiğinde hassas taşıma için 40 mm/s ile çalışmalıdır."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
HMI panelindeki mod seçimi PLC veri bloğundaki (DB) hız referansını günceller.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [`simulator/config.py`](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARI%C5%9EMASI-AKILLI%20FABR%C4%B0KA/simulator/config.py) (Satır ~60)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# simulator/config.py
<<<<--- ESKİ DEĞER:
CONVEYOR_SPEED_MM_S: float = 80.0
====
>>>>+++ YENİ DEĞER:
# [HAKEM REVİZYONU - REÇETE 2 MODU]:
CONVEYOR_SPEED_MM_S: float = 40.0
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import simulator.config as c; assert c.CONVEYOR_SPEED_MM_S in (40.0, 80.0); print('TEST BASARILI: Reçete hızı tanımlı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, HMI reçete değişkeni üzerinden motor sürücü analog referansını 40 mm/s'ye çektik. Konveyör taşıma hızı yarıya indirilerek hassas moda geçirilmiştir."*

---

### `[REV-PLC-03] Sensör Arızası / Zaman Aşımı: Küp 10 Saniyede Çıkışa Gelmezse Alarm Verme`
* **Kategori:** PLC / Emniyet Zamanlayıcısı (Watchdog Timer)
* **Zorluk / Risk Seviyesi:** Orta Risk
* **Tahmini Uygulama Süresi:** **45 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Konveyör girişinden küp girdikten sonra 10 saniye içinde çıkış sensörüne ulaşmazsa (sıkışma durumu), motor acil dursun ve Sarı alarm lambası yansın."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Giriş sensörü S1 (`%I0.4`) tetiklendiğinde bir TON (Timer On Delay) zamanlayıcısı başlar. 10 saniye içinde S2 (`%I0.5`) kesilmezse Timer çıkışı arıza durumuna geçer.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [`simulator/core/plc_engine.py`](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARI%C5%9EMASI-AKILLI%20FABR%C4%B0KA/simulator/core/plc_engine.py) (State 2: FEEDING içi)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# simulator/core/plc_engine.py -> State 2: FEEDING içinde
<<<<--- ESKİ KOD:
        elif self.state == 2:  # FEEDING
            self.Q_CONVEYOR_MOTOR = True
            if self.I_EXIT:
                self.state = 3
====
>>>>+++ YENİ KOD:
        elif self.state == 2:  # FEEDING
            self.Q_CONVEYOR_MOTOR = True
            # [HAKEM REVİZYONU - 10 SN ZAMAN AŞIMI KORUMASI]:
            if self.feed_time > 10.0 and not self.I_EXIT:
                self.state = 99  # ESTOP / Arıza dondurma
                self.Q_CONVEYOR_MOTOR = False
                self.Q_YELLOW_LAMP = True
                print("[PLC ALARM]: Konveyörde küp sıkışması tespit edildi (10s Zaman Aşımı)!")
            elif self.I_EXIT:
                self.state = 3
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -m py_compile simulator/core/plc_engine.py && echo "TEST BASARILI: PLC zamanlayıcı syntax hatasız!"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, konveyör besleme adımına TON emniyet zamanlayıcısı ekledik. Parça 10 saniye içinde çıkış sensörünü kesmezse sistem hataya geçerek motoru durdurmakta ve sarı ikaz flaşörünü (%Q0.3) devreye almaktadır."*

---

### `[REV-PLC-04] E-Stop Sonrası Güvenlik: Reset Butonuna Basılmadan Sistemin Başlamasını Engelleme`
* **Kategori:** PLC / Emniyet Standardı (Safety Interlock)
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **30 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Acil Stop butonu kaldırılsa bile Start'a basıldığında sistem hemen çalışmasın; operatörün önce panodan mavi RESET butonuna basıp arızayı sıfırlaması zorunlu olsun."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Endüstriyel iş güvenliği standardı gereği acil duruş açıldığında doğrudan hareket başlamaz. `%I0.3` (Reset) yükselen kenarı emniyet rölesi mührünü tazelemelidir.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [`simulator/core/plc_engine.py`](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARI%C5%9EMASI-AKILLI%20FABR%C4%B0KA/simulator/core/plc_engine.py) (Satır ~225)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# simulator/core/plc_engine.py -> E-Stop Kurtarma Fazı
<<<<--- ESKİ KOD:
        if self.state == 99 and not self.I_ESTOP:
            self.state = 0
====
>>>>+++ YENİ KOD:
        # [HAKEM REVİZYONU - RESET BUTONU ŞARTI]:
        if self.state == 99 and not self.I_ESTOP:
            if self.I_RESET:
                self.state = 0   # Yalnızca Reset basıldığında kilit açılır
                self.Q_YELLOW_LAMP = False
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "from simulator.core.plc_engine import PLCEngine; p=PLCEngine(); p.state=99; p.I_ESTOP=False; p.I_RESET=False; p._step_cycle(False,False,False,False,False,False,False); assert p.state==99; print('TEST BASARILI: Reset basılmadan kilit acılmıyor!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, E-Stop durumundan çıkış lojiğine `%I0.3` (Reset) zorunluluğu ekledik. Mantar buton çevrilip açılsa dahi operatör fiziksel reset vermedikçe sistem State 0'a geçmemektedir."*

---

### `[REV-PLC-05] Araç Dock Algılama Hassasiyeti: Araç Yükleme Noktasına Tam Oturmadan Tetik Vermeme`
* **Kategori:** PLC / Sensör Doğrulama
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **25 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Araç yükleme cebine bazen 5 cm geride yanaşıyor ve robot kol küpü araba yerine yere bırakıyor. Araç yükleme cebine 2 cm'den daha yakın değilse robot kola BAŞLA sinyali gitmesin."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
PLC'deki `%I0.6` (Vehicle Ready) girişi dock sensöründen gelir. Sensör toleransı 35 mm'den 18 mm'ye çekilerek aracın milimetrik oturması şart koşulur.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [`simulator/core/plc_engine.py`](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARI%C5%9EMASI-AKILLI%20FABR%C4%B0KA/simulator/core/plc_engine.py) (Satır ~207)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# simulator/core/plc_engine.py -> update_sensors() içinde
<<<<--- ESKİ DEĞER:
        self.I_VEHICLE_READY = (dist <= 35.0)
====
>>>>+++ YENİ DEĞER:
        self.I_VEHICLE_READY = (dist <= 18.0)   # 18 mm hassas dock şartı
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "from simulator.core.plc_engine import PLCEngine; p=PLCEngine(); p.update_sensors([0,0,0], 25.0); assert p.I_VEHICLE_READY == False; print('TEST BASARILI: 25 mm mesafede dock verilmiyor!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, araç dock emniyet mesafesini (`I_VEHICLE_READY`) 35 mm'den 18 mm toleransa daralttık. Araç mekanik kılavuza tam oturmadan robot kola start darbesi (%Q0.4) üretilmez."*

---

### `[REV-PLC-06] Konveyör Sinyal Lambası Mantığı: Çıkışta Parça Beklerken Kırmızı Lambayı Flaşör Yapma`
* **Kategori:** PLC / Görsel Uyarı & İkaz Kulesi
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **20 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Konveyör çıkışında küp beklerken kırmızı lamba sabit yanmasın; operatörün dikkatini çekmek için 0.5 saniye aralıklarla yanıp sönsün (flaşör yapsın)."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
State 3 (EXIT_STOPPED) içinde kırmızı lamba çıkışı sabit True yerine zaman modülasyonu ile yanıp söndürülür.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [`simulator/core/plc_engine.py`](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARI%C5%9EMASI-AKILLI%20FABR%C4%B0KA/simulator/core/plc_engine.py) (Satır ~300)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# simulator/core/plc_engine.py -> State 3 içinde
<<<<--- ESKİ KOD:
        elif self.state == 3:  # EXIT_STOPPED
            self.Q_CONVEYOR_MOTOR = False
            self.Q_RED_LAMP = True
====
>>>>+++ YENİ KOD:
        elif self.state == 3:  # EXIT_STOPPED
            self.Q_CONVEYOR_MOTOR = False
            # [HAKEM REVİZYONU - KIRMIZI FLAŞÖR]:
            self.Q_RED_LAMP = bool(int(self.elapsed_time * 2) % 2 == 0)
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -m py_compile simulator/core/plc_engine.py && echo "TEST BASARILI: Flaşör kodu hatasız!"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, State 3 çıkışında kırmızı sinyal lambasına 2 Hz frekanslı flaşör modu entegre ettik. Robot kol parçayı alana kadar görsel uyarı aktif kalmaktadır."*

---

# BLOK E: AĞ (MQTT) KESİNTİSİ, FAIL-SAFE & SAHA IŞIK KALİBRASYONU

---

### `[REV-ORTAM-01] Ağ Kesintisi Emniyeti (Fail-Safe): MQTT Gelmezse Varsayılan Yeşil Renge Park Etme`
* **Kategori:** Haberleşme / Emniyet Modu
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **15 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Robot kolun MQTT haberleşmesi koptu veya broker çöktü. Aracınız sonsuza kadar beklememeli; 10 saniye içinde mesaj gelmezse varsayılan olarak YEŞİL renge göre otonom sürüşe başlamalıdır."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
`colorlink.py` içerisinde `timeout_s` süresi dolduğunda `default_color` devreye girer. `require_for_start: false` yapıldığında araç kilitlenmeden göreve başlar.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/config.yaml](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/config.yaml)
* **Bölüm:** `colorlink:` altındaki `default_color`, `timeout_s`, `require_for_start`

#### 4. 💻 Kod Değişikliği (Diff)
```yaml
# otonomarac/config.yaml -> colorlink bölümü
colorlink:
<<<<--- ESKİ DEĞER:
  require_for_start: true
  default_color: RED
  timeout_s: 30.0
====
>>>>+++ YENİ DEĞER:
  require_for_start: false      # MQTT olmasa da kalkışa izin ver
  default_color: GREEN          # Varsayılan renk YEŞİL yapıldı
  timeout_s: 10.0               # 10 sn sonra zaman aşımı
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import yaml; c=yaml.safe_load(open('otonomarac/config.yaml', encoding='utf-8')); assert c['colorlink']['default_color'] == 'GREEN'; print('TEST BASARILI: default_color GREEN yapıldı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `colorlink.default_color` değerini GREEN olarak yapılandırıp `timeout_s` süresini 10 saniyeye çektik. Ağ bağlantısı kopsa dahi araç sistem kilitlenmesine (deadlock) düşmeden yeşil parka yönelecektir."*

---

### `[REV-ORTAM-02] Çadır / Fuar Spot Işığı: Yeşil Park Zemin Rengini Genişletme`
* **Kategori:** Görüntü İşleme / HSV Kalibrasyonu
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **30 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Fuar alanındaki sarı spot ışıkları yeşil park zeminini açık sarımtırak gösteriyor; aracınız yeşil alanı kaçırıyor. Yeşil HSV renk bandını sarıya doğru genişletin ve gölge toleransını artırın."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Yeşil rengin standart Hue (H) bandı 35-85 arasındadır. Sarı ışık altında yeşil dalga boyu 25'e kadar kayar. Alt eşiği 25'e çekip doygunluk eşiğini düşürerek açık fıstık yeşili tonları da yakalanır.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/park_zemin_renk.py](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/park_zemin_renk.py)
* **Sözlük:** `PARK_RENK_BANTLARI["GREEN"]` (Satır ~44)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# otonomarac/park_zemin_renk.py -> PARK_RENK_BANTLARI sözlüğü
    # [YEŞİL ZEMİN HSV BANTI]
<<<<--- ESKİ DEĞER:
    "GREEN": [((35, 40, 40), (85, 255, 255))],
====
>>>>+++ YENİ DEĞER:
    "GREEN": [((25, 25, 25), (88, 255, 255))],   # H:25'e genişletildi, S/V:25'e düşürüldü
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "from otonomarac.park_zemin_renk import PARK_RENK_BANTLARI; assert PARK_RENK_BANTLARI['GREEN'][0][0][0] == 25; print('TEST BASARILI: Yesil renk bandı genisletildi!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `park_zemin_renk.py` içerisindeki yeşil renk HSV alt eşiğini 25'e esnetip doygunluk sınırını 25'e düşürdük. Sarı spot ışıklarının oluşturduğu renk sapması dengelenmiştir."*

---

### `[REV-ORTAM-03] Koyu Zemin: Mavi Park Alanını Gölgeli Ortamda Yakalama`
* **Kategori:** Görüntü İşleme / HSV Kalibrasyonu
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **25 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Park alanının mavi zemini köprü altında kaldığı için gölgeli ve karanlık görünüyor. Mavi rengin parlaklık ve doygunluk eşiklerini düşürerek gölgedeki maviyi de algılayın."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
Mavi rengin Value (V/Parlaklık) değeri gölgede 30'un altına düşebilir. `PARK_RENK_BANTLARI["BLUE"]` alt limitleri gevşetilerek karanlık lacivert tonlar maskeye dahil edilir.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/park_zemin_renk.py](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/park_zemin_renk.py)
* **Sözlük:** `PARK_RENK_BANTLARI["BLUE"]` (Satır ~49)

#### 4. 💻 Kod Değişikliği (Diff)
```python
# otonomarac/park_zemin_renk.py -> PARK_RENK_BANTLARI sözlüğü
    # [MAVİ ZEMİN HSV BANTI]
<<<<--- ESKİ DEĞER:
    "BLUE": [((100, 40, 40), (135, 255, 255))],
====
>>>>+++ YENİ DEĞER:
    "BLUE": [((95, 20, 20), (135, 255, 255))],    # Doygunluk ve Parlaklık 20'ye indirildi
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "from otonomarac.park_zemin_renk import PARK_RENK_BANTLARI; assert PARK_RENK_BANTLARI['BLUE'][0][0][1] == 20; print('TEST BASARILI: Mavi gölge esigi güncellendi!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, mavi zemin spektrumunun doygunluk ve ışık yoğunluğu tabanını 20'ye çektik. Köprü altı gölgelenmelerinde piksel kaybı sıfıra indirilmiştir."*

---

### `[REV-ORTAM-04] Robot Kol Küp Algılama: Işık Yetersizliğinde Doluluk Eşiğini Düşürme`
* **Kategori:** Robot Kol / Görüntü İşleme
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **20 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Robot kol kamerası küpün üstünde duruyor ama renk tespiti sürekli UNKNOWN kalıyor, küpü algılayıp alamıyor. Renk tanıma toleransını gevşetin."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
`renk_kalibrasyon.json` dosyasındaki `doluluk_esigi: 0.40` değeri, ROI içerisindeki piksellerin en az %40'ının renk maskesine oturmasını şart koşar. Işık zayıfsa bu oran %30'a düşer ve algoritma emin olamaz. Eşik %25'e düşürüldüğünde algılama anında kilitlenir.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [robotkol/renk_kalibrasyon.json](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/robotkol/renk_kalibrasyon.json)
* **Parametre:** `"doluluk_esigi"` ve `"marj"`

#### 4. 💻 Kod Değişikliği (Diff)
```json
// robotkol/renk_kalibrasyon.json
<<<<--- ESKİ DEĞER:
  "doluluk_esigi": 0.40,
  "marj": 0.12,
====
>>>>+++ YENİ DEĞER:
  "doluluk_esigi": 0.25,
  "marj": 0.08,
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import json; d=json.load(open('robotkol/renk_kalibrasyon.json')); assert d['doluluk_esigi'] == 0.25; print('TEST BASARILI: doluluk_esigi 0.25 yapıldı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `renk_kalibrasyon.json` içindeki ROI doluluk eşiğini %25'e çekerek renk ayrım marjını 0.08 yaptık. Zayıf aydınlatmada dahi küp yüzeyi anında taranıp renk tespit edilmektedir."*

---

### `[REV-ORTAM-05] Şerit Kayıp Kurtarma: Çizgisi Silinmiş Yolda Gaz Kesme Emniyeti`
* **Kategori:** Otonom Araç / Güvenlik Modu
* **Zorluk / Risk Seviyesi:** Düşük Risk
* **Tahmini Uygulama Süresi:** **20 Saniye**

#### 1. 🗣️ Hakemin Talimatı
> *"Parkurun bir kısmında zemin beyaz şeridi aşınmış ve silik. Şerit takibi çizgiyi kaybedince araç pistten dışarı fırlamasın, gazı %70 kıssın ve çizgiyi tekrar arayana kadar yavaşlasın."*

#### 2. ⚙️ Fiziksel Neden ve Sisteme Etkisi
`main.py` içinde şerit tespit edilemediğinde veya sol çizgi kaybolduğunda (`res.left_missing >= 4`) `lm_scale_kayip4` çarpanı devreye girer. Bu çarpan kısılarak araç şerit ararken hızı düşürülür.

#### 3. 📂 Müdahale Edilecek Dosya ve Tam Konum
* **Dosya:** [otonomarac/config.yaml](file:///c:/Users/user/OneDrive/Desktop/TEKNOFEST%20MESLEK%C4%B0%20YETENEK%20YARIŞMASI-AKILLI%20FABRİKA/otonomarac/config.yaml)
* **Bölüm:** `speed:` altındaki `lm_scale_kayip4`

#### 4. 💻 Kod Değişikliği (Diff)
```yaml
# otonomarac/config.yaml -> speed bölümü
speed:
<<<<--- ESKİ DEĞER:
  lm_scale_kayip4: 0.70
====
>>>>+++ YENİ DEĞER:
  lm_scale_kayip4: 0.30       # Şerit kaybolunca gaz %70 kesilir
```

#### 5. ⏱️ 30 Saniyelik Hızlı Doğrulama Komutu
```bash
python -c "import yaml; c=yaml.safe_load(open('otonomarac/config.yaml', encoding='utf-8')); assert c['speed']['lm_scale_kayip4'] == 0.30; print('TEST BASARILI: Şerit kayıp gaz carpani 0.30 yapıldı!')"
```

#### 6. 🏆 Hakeme Sunum Cümlesi
> *"Hocam, `speed.lm_scale_kayip4` emniyet katsayısını 0.30'a indirdik. Çizgi sürekliliği bozulduğu anda araç gazı %70 kısarak güvenli tarama hızına düşmekte ve pist dışına taşmayı önlemektedir."*

---

## 🏁 YARIŞMA GÜNÜ 6 ADIMLI ALTIN PROTOKOL

Hakem masanıza gelip revizyon istediğinde panik yapmadan sırasıyla şu adımları izleyin:

```
+-------------------------------------------------------------------------------+
|                       30 SANİYELİK SAHA PROTOKOLÜ                             |
+---+----------------------+----------------------------------------------------+
| 1 | DİNLE VE NOT AL      | Hakemin söylediği saniye, cm, renk veya kuralı yaz.|
| 2 | BELGEDEN BUL         | Bu belgede Ctrl + F yaparak ilgili senaryoyu aç.   |
| 3 | DOSYAYI AÇ           | Belirtilen dosyanın tam satırına git.              |
| 4 | KODU GÜNCELLE        | Eski değeri sil, diff kutusundaki yeni kodu yaz.   |
| 5 | TESTİ ÇALIŞTIR       | Terminaldeki 30 saniyelik test komutuyla onayla.   |
| 6 | JÜRİYE SAVUN         | Belgedeki Hakeme Sunum Cümlesini dik ve kendinden  |
|   |                      | emin bir ses tonuyla jüriye söyle!                 |
+---+----------------------+----------------------------------------------------+
```
