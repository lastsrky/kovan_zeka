# KOVAN ZEKA — TEKNOFEST HAKEM GÖREV DEĞİŞİKLİĞİ VE REVİZYON TALEPLERİ ÇÖZÜM REHBERİ
> **Belge Amacı:** TEKNOFEST Robotaksi Binek Otonom Araç Yarışması final etabında, hakem heyeti tarafından yarışma başlamadan hemen önce veya tur aralarında talep edilecek kritik görev revizyonlarının adım adım çözümlerini içerir.  
> **Hedef Kitle:** Sıfır yazılım ve kodlama tecrübesine sahip takım üyeleri, saha mekanik ekibi ve pit pilotları.  
> **Temel Garanti:** Bu rehberdeki tüm çözümler, sistemin Python kaynak kodlarındaki (`main.py`, `trafik.py`, `tabela_gorev.py`, `park_zemin_renk.py`) mantıksal algoritmalara **tek bir satır dahi dokunmadan**, sadece ve sadece `KILAVUZ.md` belgesindeki parametre haritası ve `otonomarac/config.yaml` dosyası kullanılarak uygulanabilir.

---

## İÇİNDEKİLER
1. [Saha Hakem Revizyonları Yönetim Protokolü (30 Saniye Kuralı)](#1-saha-hakem-revizyonları-yönetim-protokolü-30-saniye-kuralı)
2. [HAKEM SENARYOSU 1: Trafik Lambası Arıza Modu ve Mesafe Revizyonu](#2-hakem-senaryosu-1-trafik-lambası-arıza-modu-ve-mesafe-revizyonu)
3. [HAKEM SENARYOSU 2: Yaya Geçidi Duraklama Süresi ve Kör Geçiş Gücü Artırımı](#3-hakem-senaryosu-2-yaya-geçidi-duraklama-süresi-ve-kör-geçiş-gücü-artırımı)
4. [HAKEM SENARYOSU 3: Ağ Kesintisi Durumunda Varsayılan Park Rengini YEŞİL Yapma ve Hassas Duruş](#4-hakem-senaryosu-3-ağ-kesintisi-durumunda-varsayılan-park-rengini-yeşil-yapma-ve-hassas-duruş)
5. [Kombine Jüri Senaryosu (3 Görevin Aynı Anda Değiştirilmesi Tatbikatı)](#5-kombine-jüri-senaryosu-3-görevin-aynı-anda-değiştirilmesi-tatbikatı)
6. [Sıfır Kodlama ve Adli Denetim Matrisi (Forensic Audit Proof)](#6-sıfır-kodlama-ve-adli-denetim-matrisi-forensic-audit-proof)
7. [Pist Öncesi 60 Saniyelik Son Kontrol Listesi (Pre-Flight Checklist)](#7-pist-öncesi-60-saniyelik-son-kontrol-listesi-pre-flight-checklist)

---

## 1. SAHA HAKEM REVİZYONLARI YÖNETİM PROTOKOLÜ (30 SANİYE KURALI)

Yarışma esnasında hakem masaya gelip bir parametre değişikliği istediğinde takım üyelerinin panik yapmadan şu 6 adımlı acil müdahale protokolünü izlemesi zorunludur:

```
+-----------------------------------------------------------------------------------------------+
|                       30 SANİYELİK SAHA DEĞİŞİKLİK YÖNETİM PROTOKOLÜ                          |
+----+-----------------------+------------------------------------------------------------------+
| Adım| Eylem                 | Yapılacak İşlem                                                  |
+----+-----------------------+------------------------------------------------------------------+
| 1  | Talimatı Netleştir    | Hakemin söylediği fiziksel değeri (saniye, cm, PWM, renk) not al.|
| 2  | KILAVUZ'a Bak         | KILAVUZ.md Bölüm 3 (Hızlı Başvuru Matrisi)'nden parametreyi bul. |
| 3  | Dosyayı Aç            | otonomarac/config.yaml dosyasını metin düzenleyicide aç.         |
| 4  | Ctrl + F ile Bul      | Değişecek parametre adını arat, SADECE sayıyı/kelimeyi değiştir.  |
| 5  | Kaydet ve Doğrula     | Ctrl + S ile kaydet, terminalde tek satırlık test komutunu çalıştır.|
| 6  | Aracı Piste Bırak     | cd otonomarac && python3 main.py ile otonom modu başlat.         |
+----+-----------------------+------------------------------------------------------------------+
```

---

## 2. HAKEM SENARYOSU 1: TRAFİK LAMBASI ARIZA MODU VE MESAFE REVİZYONU

### 2.1. Hakemin Birebir Ağzından Çıkan Talimat (Verbatim Request)
> *"Yarışma komitesi olarak parkurdaki trafik lambasının yeşil ışık devresinde teknik bir arıza tespit ettik. Kırmızı ışıktan sonra yeşil ışık kesinlikle yanmayacaktır. Aracınız kırmızı ışığı 90 cm yerine 140 cm mesafeden algılayıp güvenli mesafede durmalıdır. Yeşil ışık hiç yanmayacağı için aracınız kırmızıda en fazla 7.0 saniye beklemeli ve bu sürenin sonunda yeşili beklemeden otonom olarak kalkış yapıp şeridinde devam etmelidir."*

---

### 2.2. Fiziksel Neden ve Araca Etkisi
1. **Algılama Mesafesinin 90.0 cm'den 140.0 cm'ye Çıkarılması (`max_mesafe_cm`):**
   - **Fiziksel Neden:** Varsayılan 90.0 cm eşiği, aracın ışık direğine oldukça yaklaşmasını gerektirir. Yüksek seyir hızlarında bu durum ani frenlemeye (ABS sarsıntısına) ve beyaz duruş çizgisini 10-20 cm taşırarak hakemden ceza puanı almaya yol açabilir. Eşiğin 140.0 cm'ye çekilmesi, Intel RealSense D455 derinlik kamerasının kırmızı ışık piksellerini 1.4 metre mesafeden süzmesini sağlar.
   - **Araca Etkisi:** Araç kırmızı ışığı daha uzaktan güvenle algılar (`dur_frames: 3`), `gecikme_s: 0.5` boyunca yumuşak bir süzülme ile duruş çizgisine tam zamanında oturur; çizgiyi ihlal etmez.

2. **Maksimum Bekleme Süresinin 0.0'dan 7.0 Saniyeye Sınırlandırılması (`max_dur_s`):**
   - **Fiziksel Neden:** Varsayılan `max_dur_s: 0.0` ayarı, sistem mimarisinde "yeşil ışık yanana kadar sonsuza dek bekle" anlamına gelen emniyet kilididir (`trafik.py:306-320`). Piste yeşil ışık bozulduğu için araç sonsuza kadar bekleyecek ve parkuru tamamlayamayarak diskalifiye olacaktır.
   - **Araca Etkisi:** `max_dur_s: 7.0` yapıldığında durum makinesindeki dahili zamanlayıcı durulduğu anda başlar. Tam 7.0 saniye dolduğunda yeşil ışık aranması zorla sonlandırılır (`out.state = "BITTI"`), motor freni kaldırılır, şerit takip kontrolcüsü devreye girer ve araç otonom olarak kalkış yapar.

---

### 2.3. `KILAVUZ.md` Çapraz Başvurusu (Cross-References)
Bu değişikliğin dayandığı kurallar `KILAVUZ.md` belgesinde şu konumlarda birebir tanımlanmıştır:
- **Bölüm 3: Hızlı Başvuru Matrisi ("Hakem Ne Dedi?" Tablosu):**
  * **Tablo Satır No 1:** *"Kırmızı ışıkta çok uzakta/yakında duruyor"* | Dosya: `otonomarac/config.yaml` | Parametre: `[trafik] -> max_mesafe_cm (Satır ~376)` | Varsayılan: `90.0` | Güvenli Aralık: `50.0 - 160.0` cm.
  * **Tablo Satır No 2:** *"Kırmızı ışıkta yeşil yanmasa bile X saniye sonra kalksın"* | Dosya: `otonomarac/config.yaml` | Parametre: `[trafik] -> max_dur_s (Satır ~423)` | Varsayılan: `0.0` | Güvenli Aralık: `3.0 - 30.0` sn.
- **Bölüm 4: Görev Bazlı Ayrıntılı Değişiklik Kılavuzu:**
  * **Bölüm A (Trafik Lambası Görevi, Satır 338 - 431):** Madde 1 (Mesafe Ayarı, Satır ~376) ve Madde 2 (Arıza / Süre Ayarı, Satır ~423).
- **Bölüm 2: Altın Kurallar:**
  * **Kural 1:** Tab tuşu yasaktır, sadece boşluk kullanılabilir.
  * **Kural 2:** İki noktadan sonra tam 1 boşluk bırakılmalıdır.
  * **Kural 3:** Ondalıklı sayılarda virgül değil, mutlaka nokta (`.`) kullanılmalıdır (`140.0` ve `7.0`).
- **Bölüm 6: En Sık Yapılan 7 Ölümcül Hata:**
  * **Hata 2:** Ondalıkta virgül kullanmak (`140,0` yazılırsa sistem çöker).

---

### 2.4. Açılacak Dosyanın Tam Yolu
Aşağıdaki dosyayı metin düzenleyicinizde (VS Code, Not Defteri, Gedit vb.) açın:
```
/Users/memduh/.gemini/antigravity/worktrees/kovan_zeka/analyze_directory_files/otonomarac/config.yaml
```

---

### 2.5. Adım Adım Tıkla-Yaz Talimatları (Click-and-Type)

1. Dosyayı açın ve klavyeden `Ctrl + F` (Mac'te `Cmd + F`) tuşlarına basarak arama çubuğunu açın.
2. Arama çubuğuna `max_mesafe_cm` yazın ve Enter'a basın (Satır ~376).
3. `trafik:` bloğu altındaki `max_mesafe_cm: 90.0` satırını bulun (Satır ~376).
4. Fare ile sadece `90.0` sayısını seçin ve klavyeden `140.0` yazın.
5. Tekrar `Ctrl + F` yapıp `max_dur_s` yazın (Satır ~423).
6. `max_dur_s: 0.0` satırını bulun (Satır ~423).
7. Fare ile sadece `0.0` sayısını seçin ve klavyeden `7.0` yazın.
8. Dosyayı kaydetmek için `Ctrl + S` (Mac'te `Cmd + S`) tuşlarına basın.

#### Değişiklik Öncesi (BEFORE) Kod Bloğu:
```yaml
trafik:
  enable: true
  ust_bant: 0.60
  hue_bantlari:
  - [0, 10]
  - [150, 180]
  s_min: 60
  v_min: 150
  area_min: 100
  area_max: 3000
  max_aspect: 2.0
  max_mesafe_cm: 90.0
  depth_yoksa_kabul: false
  dur_frames: 3
  gecikme_s: 0.5
  gec_frames: 25
  yesil_bantlari:
  - [35, 90]
  yesil_s_min: 60
  yesil_v_min: 120
  yesil_area_min: 100
  yesil_x_tol_px: 90
  kilit_tol_px: 80
  max_dur_s: 0.0
  once: true
```

#### Değişiklik Sonrası (AFTER) Kod Bloğu:
```yaml
trafik:
  enable: true
  ust_bant: 0.60
  hue_bantlari:
  - [0, 10]
  - [150, 180]
  s_min: 60
  v_min: 150
  area_min: 100
  area_max: 3000
  max_aspect: 2.0
  max_mesafe_cm: 140.0
  depth_yoksa_kabul: false
  dur_frames: 3
  gecikme_s: 0.5
  gec_frames: 25
  yesil_bantlari:
  - [35, 90]
  yesil_s_min: 60
  yesil_v_min: 120
  yesil_area_min: 100
  yesil_x_tol_px: 90
  kilit_tol_px: 80
  max_dur_s: 7.0
  once: true
```

---

### 2.6. Karakter Düzeyinde Katı Güvenlik Uyarıları
- ⚠️ **2 Boşluk Kuralı:** `max_mesafe_cm:` ve `max_dur_s:` satırlarının solunda tam **2 adet boşluk (space)** vardır. Bu boşlukları ASLA silmeyin veya 3 boşluk yapmayın.
- ⚠️ **Tab Tuşu Yasağı:** Girinti oluşturmak için ASLA `Tab` tuşuna basmayın.
- ⚠️ **Nokta/Virgül Uyarısı:** Ondalık hanesinde ASLA virgül kullanmayın (`140,0` veya `7,0` yazarsanız sistem syntax hatasıyla kilitlenir). Mutlaka `140.0` ve `7.0` yazın.
- ⚠️ **İki Nokta ve Boşluk:** `max_mesafe_cm:` ifadesindeki iki noktayı ve sonrasındaki 1 adet boşluğu kesinlikle silmeyin.

---

### 2.7. Terminalden Doğrulama Adımları
Değişikliği yaptıktan sonra terminali açıp aşağıdaki doğrulama komutunu kopyalayıp yapıştırın:

```bash
python3 -c "
with open('otonomarac/config.yaml', 'r') as f:
    txt = f.read()
assert 'max_mesafe_cm: 140.0' in txt, 'HATA: max_mesafe_cm 140.0 olarak bulunamadi!'
assert 'max_dur_s: 7.0' in txt, 'HATA: max_dur_s 7.0 olarak bulunamadi!'
assert '\t' not in txt, 'HATA: Dosyada yasakli TAB karakteri var!'
print('MUKEMMEL: Senaryo 1 degisiklikleri (140.0 cm ve 7.0 sn) basariyla dogrulandi!')
"
```
**Beklenen Çıktı:**
```
MUKEMMEL: Senaryo 1 degisiklikleri (140.0 cm ve 7.0 sn) basariyla dogrulandi!
```

---

### 2.8. Sıfır Kodlama İspatı (Zero-Knowledge Validation)
- Bu senaryoda `trafik.py` içindeki kırmızı renk tespiti, kontur filtreleme veya durum makinesi kodlarına tek bir karakter dahi eklenmemiştir.
- Kullanıcı sadece `KILAVUZ.md` Matris Satır 1 ve 2'ye bakmış, `config.yaml` içindeki iki sayıyı güncellemiş ve hedef davranışı %100 oranında sağlamıştır.

---

## 3. HAKEM SENARYOSU 2: YAYA GEÇİDİ DURAKLAMA SÜRESİ VE KÖR GEÇİŞ GÜCÜ ARTIRIMI

### 3.1. Hakemin Birebir Ağzından Çıkan Talimat (Verbatim Request)
> *"Yaya geçidi önündeki güvenlik bekleme süresini 3.0 saniyeden 6.0 saniyeye çıkarın. Ayrıca bu parkurda yaya geçidindeki zebra çizgileri normalden daha kalın ve zemin sürtünmesi fazladır; aracınızın çizgileri aşarken şerit takibini şaşırmaması için kör düz geçiş süresini 3.0 saniyeden 4.5 saniyeye uzatın ve geçiş motor gazını (PWM) 85'ten 110'a yükseltin."*

---

### 3.2. Fiziksel Neden ve Araca Etkisi
1. **Güvenlik Bekleme Süresinin 3.0 sn'den 6.0 sn'ye Çıkarılması (`dur_s`):**
   - **Fiziksel Neden:** Hakem heyeti simüle edilen yayanın geçiş süresini uzatmıştır.
   - **Araca Etkisi:** Araç yaya tabelasını tespit edip (`dur_mesafe_cm: 100.0`) durduktan sonra motor sıfırlanır ve araç 6.0 saniye boyunca milim kıpırdamadan tam duruş sergiler (`[yaya] DUR (6.0 sn motor 0)`).
2. **Kör Geçiş Süresinin 3.0 sn'den 4.5 sn'ye Uzatılması (`gec_s`):**
   - **Fiziksel Neden:** Yaya geçidi üzerindeki kalın beyaz-siyah zebra şeritleri, kamera tabanlı şerit tespit algoritmasında (OpenCV / bağlı bileşenler) yapay dikey çizgiler gibi görünerek yanılsama yaratır. Araç zebra çizgilerinin üzerindeyken direksiyon şerit takibine bırakılırsa araç zikzak çizer ve pistten fırlar. Bu sebeple sistem zebra üzerinde `gec_s` süresince şerit algoritmasını devre dışı bırakır, direksiyonu tam düz (`steer=0.0`) kilitler ve düz gaz verir. Geçit geniş olduğu için 3.0 saniye yetersiz kalıp aracın çizgiler bitmeden şerit takibini erken açmasına sebep olurdu. 4.5 saniye ile tüm zebra alanı güvenle geride bırakılır.
3. **Kör Geçiş Motor Gücünün 85'ten 110 PWM'e Yükseltilmesi (`gec_pwm`):**
   - **Fiziksel Neden:** Yüksek zemin sürtünmesi ve kalın boya tabakası aracın düşük güçte takılmasına veya teklemesine sebep olur.
   - **Araca Etkisi:** 110 PWM, araca tekerlek kayması yaşamadan düz bir hat boyunca engeli hızla ve kararlılıkla aşacak yeterli torku sağlar (`gec_pwm: 110`).

---

### 3.3. `KILAVUZ.md` Çapraz Başvurusu (Cross-References)
- **Bölüm 3: Hızlı Başvuru Matrisi ("Hakem Ne Dedi?" Tablosu):**
  * **Tablo Satır No 7:** *"Yaya geçidinde X saniye bekleyin"* | Dosya: `otonomarac/config.yaml` | Parametre: `[yaya] -> dur_s (Satır ~473)` | Varsayılan: `3.0` | Güvenli Aralık: `1.0 - 10.0` sn.
  * **Tablo Satır No 8:** *"Yaya geçidi çizgilerini aşarken araç sapıtıyor / takılıyor"* | Dosya: `otonomarac/config.yaml` | Parametre: `[yaya] -> gec_s (Satır ~478)` | Varsayılan: `3.0` | Güvenli Aralık: `1.5 - 5.0` sn.
  * **Tablo Satır No 9:** *"Yaya geçidinden geçerken araç çok yavaş kalıyor"* | Dosya: `otonomarac/config.yaml` | Parametre: `[yaya] -> gec_pwm (Satır ~483)` | Varsayılan: `85` | Güvenli Aralık: `70 - 130` PWM.
- **Bölüm 4: Görev Bazlı Ayrıntılı Değişiklik Kılavuzu:**
  * **Bölüm B (Yaya Geçidi Görevi, Satır 452 - 491):** Madde 1 (Bekleme Süresi, Satır ~473) ve Madde 3 (Kör Geçiş Süresi ve Gazı, Satır ~478 ve ~483).
- **Bölüm 2: Altın Kurallar:**
  * **Kural 2:** İki noktadan sonra tam bir boşluk.
  * **Kural 3:** Ondalıklarda nokta (`6.0`, `4.5`), tamsayılarda nokta yok (`110`).

---

### 3.4. Açılacak Dosyanın Tam Yolu
```
/Users/memduh/.gemini/antigravity/worktrees/kovan_zeka/analyze_directory_files/otonomarac/config.yaml
```

---

### 3.5. Adım Adım Tıkla-Yaz Talimatları (Click-and-Type)

1. `otonomarac/config.yaml` dosyasını açın.
2. `Ctrl + F` ile `yaya:` başlığını aratın (Satır ~452).
3. `dur_s: 3.0` satırındaki (Satır ~473) `3.0` değerini silip `6.0` yazın.
4. Hemen altındaki `gec_s: 3.0` satırındaki (Satır ~478) `3.0` değerini silip `4.5` yazın.
5. Hemen altındaki `gec_pwm: 85` satırındaki (Satır ~483) `85` değerini silip `110` yazın.
6. `Ctrl + S` ile dosyayı kaydedin.

#### Değişiklik Öncesi (BEFORE) Kod Bloğu:
```yaml
yaya:
  enable: true
  dur_mesafe_cm: 100.0
  trigger_frames: 3
  gecikme_s: 0.0
  dur_s: 3.0
  gec_s: 3.0
  gec_pwm: 85
  once: true
```

#### Değişiklik Sonrası (AFTER) Kod Bloğu:
```yaml
yaya:
  enable: true
  dur_mesafe_cm: 100.0
  trigger_frames: 3
  gecikme_s: 0.0
  dur_s: 6.0
  gec_s: 4.5
  gec_pwm: 110
  once: true
```

---

### 3.6. Karakter Düzeyinde Katı Güvenlik Uyarıları
- ⚠️ **Sayı Türü Ayrımı:** `dur_s: 6.0` ve `gec_s: 4.5` değerlerinde **nokta vardır**; ancak `gec_pwm: 110` bir tam sayıdır, **sonuna nokta koymayın** (`110.` yazmayın).
- ⚠️ **Boşluk Disiplini:** Satır başlarındaki tam iki boşluğa dokunmayın.
- ⚠️ **Tırnak Yasağı:** Sayıları tırnak içine almayın (`"110"` veya `'6.0'` yazmayın).

---

### 3.7. Terminalden Doğrulama Adımları
Terminalde şu komutu çalıştırarak değişikliği doğrulayın:

```bash
python3 -c "
with open('otonomarac/config.yaml', 'r') as f:
    txt = f.read()
assert 'dur_s: 6.0' in txt, 'HATA: dur_s 6.0 yapilamamis!'
assert 'gec_s: 4.5' in txt, 'HATA: gec_s 4.5 yapilamamis!'
assert 'gec_pwm: 110' in txt, 'HATA: gec_pwm 110 yapilamamis!'
assert '\t' not in txt, 'HATA: Tab karakteri tespit edildi!'
print('MUKEMMEL: Senaryo 2 degisiklikleri (6.0 sn dur, 4.5 sn gec, 110 PWM) basariyla dogrulandi!')
"
```
**Beklenen Çıktı:**
```
MUKEMMEL: Senaryo 2 degisiklikleri (6.0 sn dur, 4.5 sn gec, 110 PWM) basariyla dogrulandi!
```

---

### 3.8. Sıfır Kodlama İspatı (Zero-Knowledge Validation)
- `tabela_gorev.py` içerisindeki durum makinesine (`TabelaGorevleri._step_yaya`), RealSense derinlik hesaplamasına veya şerit sıfırlama mantığına (`detector.reset_memory()`) tek satır kod eklenmemiştir.
- Değişiklik yalnızca `KILAVUZ.md` Matris Satır 7, 8 ve 9 rehberliğinde `config.yaml` üzerinden gerçekleştirilmiştir.

---

## 4. HAKEM SENARYOSU 3: AĞ KESİNTİSİ DURUMUNDA VARSAYILAN PARK RENGİNİ YEŞİL YAPMA VE HASSAS DURUŞ

### 4.1. Hakemin Birebir Ağzından Çıkan Talimat (Verbatim Request)
> *"Yarışma alanındaki frekans yoğunluğu ve Wi-Fi kopmaları sebebiyle robot kol ile araç arasındaki kablosuz MQTT haberleşmesi kesilebilir. Robot koldan renk bilgisi gelmemesi durumunda aracınız varsayılan kırmızı alan yerine YEŞİL (GREEN) alana park etmelidir. Ayrıca araç yeşil alana girerken savrulmaması ve çizgiyi taşırmaması için park yaklaşma gazını (PWM) 80'den 65'e düşürün ve durma mesafesini 25.0 cm yerine 15.0 cm yaparak kutunun tam içine hassas park edin."*

---

### 4.2. Fiziksel Neden ve Araca Etkisi
1. **Varsayılan Park Renginin RED Yerine GREEN Yapılması (`varsayilan_renk`):**
   - **Fiziksel Neden:** Normal akışta robot kol küpü yükler ve MQTT (`robot/veri`) konusu üzerinden renk adını basar. Bağlantı koptuğunda araç `tabela_gorev.py:270-300` içinde `self.colorlink.get_renk()` boş döndüğü için doğrudan `cfg['varsayilan_renk']` değerini hedef renk kabul eder. Hakemin kuralı gereği yedek rengin yeşil olması istenmektedir.
   - **Araca Etkisi:** Araç park tabelasını gördüğü an `park_zemin_renk.py:detect_park_floor()` fonksiyonuna `GREEN` renk filtresini iletir. Kameranın alt %75'inde yeşil zemin aranır, yeşil dikdörtgen bulunup merkez sapması hesaplanır ve araç yeşil cebe yönelir.
2. **Park Yaklaşma Gazının 80'den 65 PWM'e İndirilmesi (`park_pwm`):**
   - **Fiziksel Neden:** 80 PWM motor gücü, dar park cebine yaklaşırken aracın merkezkaç kuvvetiyle renk konturunu kameradan kaçırmasına ve yanal salınıma girmesine neden olabilir.
   - **Araca Etkisi:** Gaz 65 PWM'e düşürüldüğünde araç son derece yumuşak, sarsıntısız ve kontrollü biçimde yeşil zemini ortalar.
3. **Nihai Durma Mesafesinin 25.0 cm'den 15.0 cm'ye Düşürülmesi (`dur_mesafe_cm`):**
   - **Fiziksel Neden:** 25.0 cm durma eşiği aracın park cebine tam girmeden ön çizgide erken durmasına neden olabilir. Hakem aracın kutunun tam merkezine kadar oturmasını istemektedir.
   - **Araca Etkisi:** RealSense D455 derinlik sensörü ile zemin arasındaki mesafe 15.0 cm'ye inene kadar araç ilerler. Böylece araç kutunun içine tamamen girer ve `ETTI` durumuna geçerek kalıcı stop yapar.

---

### 4.3. `KILAVUZ.md` Çapraz Başvurusu (Cross-References)
- **Bölüm 3: Hızlı Başvuru Matrisi ("Hakem Ne Dedi?" Tablosu):**
  * **Tablo Satır No 11:** *"Park kutusunun tam ortasına kadar gitsin, derine park etsin"* | Dosya: `otonomarac/config.yaml` | Parametre: `[park] -> dur_mesafe_cm (Satır ~512)` | Varsayılan: `25.0` | Güvenli Aralık: `10.0 - 35.0` cm.
  * **Tablo Satır No 12:** *"Park alanına yaklaşırken araç çok hızlı veya savruluyor"* | Dosya: `otonomarac/config.yaml` | Parametre: `[park] -> park_pwm (Satır ~516)` | Varsayılan: `80` | Güvenli Aralık: `60 - 100` PWM.
  * **Tablo Satır No 15:** *"Robot koldan renk gelmezse varsayılan olarak YEŞİL'e park etsin"* | Dosya: `otonomarac/config.yaml` | Parametre: `[park] -> varsayilan_renk (Satır ~537)` | Varsayılan: `RED` | Güvenli Aralık: `RED, GREEN, BLUE`.
- **Bölüm 4: Görev Bazlı Ayrıntılı Değişiklik Kılavuzu:**
  * **Bölüm C (Renkli Park Görevi, Satır 492 - 549):** Madde 1 (Yedek Renk Seçimi, Satır ~537), Madde 2 (Yanaşma Hızı, Satır ~516) ve Madde 3 (Durma Mesafesi, Satır ~512).
- **Bölüm 2: Altın Kurallar:**
  * **Kural 5:** Renk isimleri daima İNGİLİZCE, BÜYÜK HARFLERLE ve TIRNAKSIZ yazılmalıdır: `GREEN` (Asla `green` veya `Yeşil` yazmayın).
- **Bölüm 6: En Sık Yapılan 7 Ölümcül Hata:**
  * **Hata 6:** Renk kodunu küçük harfle yazmak (`KeyError` oluşturur).

---

### 4.4. Açılacak Dosyanın Tam Yolu
```
/Users/memduh/.gemini/antigravity/worktrees/kovan_zeka/analyze_directory_files/otonomarac/config.yaml
```

---

### 4.5. Adım Adım Tıkla-Yaz Talimatları (Click-and-Type)

1. `otonomarac/config.yaml` dosyasını açın.
2. `Ctrl + F` ile `park:` başlığını aratın (Satır ~492).
3. `dur_mesafe_cm: 25.0` satırındaki (Satır ~512) `25.0` sayısını silip `15.0` yazın.  
   *(⚠️ DİKKAT: yaya bölümündeki Satır ~460'taki dur_mesafe_cm ile karıştırmayın; mutlaka park: başlığı altında olduğunuzu teyit edin).*
4. `park_pwm: 80` satırındaki (Satır ~516) `80` sayısını silip `65` yazın.
5. `varsayilan_renk: RED` satırındaki (Satır ~537) `RED` kelimesini silip BÜYÜK HARFLERLE `GREEN` yazın.
6. `Ctrl + S` ile dosyayı kaydedin.

#### Değişiklik Öncesi (BEFORE) Kod Bloğu:
```yaml
park:
  enable: true
  tabela_mesafe_cm: 110.0
  tabela_min_area_px: 400
  trigger_frames: 3
  dur_mesafe_cm: 25.0
  park_pwm: 80
  park_k: 0.125
  red_kayip_frames: 5
  ust_kirp: 0.25
  red_area_min: 300
  varsayilan_renk: RED
  zemin_min_cm: 25.0
  zemin_max_cm: 350.0
```

#### Değişiklik Sonrası (AFTER) Kod Bloğu:
```yaml
park:
  enable: true
  tabela_mesafe_cm: 110.0
  tabela_min_area_px: 400
  trigger_frames: 3
  dur_mesafe_cm: 15.0
  park_pwm: 65
  park_k: 0.125
  red_kayip_frames: 5
  ust_kirp: 0.25
  red_area_min: 300
  varsayilan_renk: GREEN
  zemin_min_cm: 25.0
  zemin_max_cm: 350.0
```

---

### 4.6. Karakter Düzeyinde Katı Güvenlik Uyarıları
- ⚠️ **Büyük Harf ve Tırnaksız Renk:** `GREEN` kelimesini mutlaka **büyük harflerle** ve **tırnak işareti olmadan** yazın (`"GREEN"` veya `green` yazmayın).
- ⚠️ **Nokta/Tamsayı Ayrımı:** `dur_mesafe_cm: 15.0` satırındaki noktayı koruyun; `park_pwm: 65` satırına nokta eklemeyin.
- ⚠️ **Boşluk Kuralı:** İki noktadan sonra tam bir boşluk olduğundan emin olun (`varsayilan_renk: GREEN`).

---

### 4.7. Terminalden Doğrulama Adımları
Terminalde şu komutu çalıştırarak kontrol edin:

```bash
python3 -c "
with open('otonomarac/config.yaml', 'r') as f:
    txt = f.read()
assert 'varsayilan_renk: GREEN' in txt, 'HATA: varsayilan_renk GREEN yapilamamis!'
assert 'park_pwm: 65' in txt, 'HATA: park_pwm 65 yapilamamis!'
assert 'dur_mesafe_cm: 15.0' in txt, 'HATA: park dur_mesafe_cm 15.0 yapilamamis!'
assert '\t' not in txt, 'HATA: Tab karakteri tespit edildi!'
print('MUKEMMEL: Senaryo 3 degisiklikleri (GREEN, 65 PWM, 15.0 cm) basariyla dogrulandi!')
"
```
**Beklenen Çıktı:**
```
MUKEMMEL: Senaryo 3 degisiklikleri (GREEN, 65 PWM, 15.0 cm) basariyla dogrulandi!
```

---

### 4.8. Sıfır Kodlama İspatı (Zero-Knowledge Validation)
- `colorlink.py` (MQTT protokolü) veya `park_zemin_renk.py` (HSV yeşil renk maskesi ve morfoloji) dosyalarına tek bir satır dahi dokunulmamıştır.
- Sistem `KILAVUZ.md` Matris Satır 11, 12 ve 15 doğrultusunda konfigürasyon üzerinden anında güncellenmiştir.

---

## 5. KOMBİNE JÜRİ SENARYOSU (3 GÖREVİN AYNI ANDA DEĞİŞTİRİLMESİ TATBİKATI)

Yarışma finallerinde jüri heyeti her üç görevi de aynı anda revize etmenizi isteyebilir. Bu durumda yapılacak toplu değişiklik ve tek seferlik doğrulama yöntemi aşağıdadır:

### 5.1. Tek Seferde Değiştirilecek Değerler Özeti:
1. `trafik.max_mesafe_cm`: `90.0` -> `140.0`
2. `trafik.max_dur_s`: `0.0` -> `7.0`
3. `yaya.dur_s`: `3.0` -> `6.0`
4. `yaya.gec_s`: `3.0` -> `4.5`
5. `yaya.gec_pwm`: `85` -> `110`
6. `park.dur_mesafe_cm`: `25.0` -> `15.0`
7. `park.park_pwm`: `80` -> `65`
8. `park.varsayilan_renk`: `RED` -> `GREEN`

### 5.2. Tek Satırlık Toplu Jüri Kabul Testi:
Değişiklikleri `config.yaml` dosyasına kaydedip şu komutu terminale yapıştırın:

```bash
python3 -c "
with open('otonomarac/config.yaml', 'r') as f:
    t = f.read()
hatalar = []
if 'max_mesafe_cm: 140.0' not in t: hatalar.append('trafik.max_mesafe_cm != 140.0')
if 'max_dur_s: 7.0' not in t: hatalar.append('trafik.max_dur_s != 7.0')
if 'dur_s: 6.0' not in t: hatalar.append('yaya.dur_s != 6.0')
if 'gec_s: 4.5' not in t: hatalar.append('yaya.gec_s != 4.5')
if 'gec_pwm: 110' not in t: hatalar.append('yaya.gec_pwm != 110')
if 'dur_mesafe_cm: 15.0' not in t: hatalar.append('park.dur_mesafe_cm != 15.0')
if 'park_pwm: 65' not in t: hatalar.append('park.park_pwm != 65')
if 'varsayilan_renk: GREEN' not in t: hatalar.append('park.varsayilan_renk != GREEN')
if '\t' in t: hatalar.append('Dosyada TAB karakteri bulundu!')

if hatalar:
    print('DIKKAT! Eksik veya hatali parametreler var:')
    for h in hatalar: print('  -', h)
    exit(1)
else:
    print('==================================================================')
    print('TEBRIKLER: TUM HAKEM TALEPLERI (8 PARAMETRE) EKSIKSIZ DOGRULANDI!')
    print('ARAC YARISMAYA VE JURI ONAYINA HAZIR.')
    print('==================================================================')
"
```

---

## 6. SIFIR KODLAMA VE ADLİ DENETİM MATRİSİ (FORENSIC AUDIT PROOF)

Aşağıdaki denetim tablosu, yapılan tüm müdahalelerin yalnızca yapılandırma katmanında gerçekleştiğini ve kaynak kod bütünlüğünün korunduğunu belgeler:

```
+---------------------------+-----------------------+--------------------+-----------------------------+
| Senaryo / Görev           | Değiştirilen Dosya    | Değişen Parametre  | DOKUNULMAYAN Kaynak Dosya   |
+---------------------------+-----------------------+--------------------+-----------------------------+
| Senaryo 1: Trafik Lambası | otonomarac/config.yaml| max_mesafe_cm      | otonomarac/trafik.py        |
|                           |                       | max_dur_s          | otonomarac/main.py          |
+---------------------------+-----------------------+--------------------+-----------------------------+
| Senaryo 2: Yaya Geçidi    | otonomarac/config.yaml| dur_s              | otonomarac/tabela_gorev.py  |
|                           |                       | gec_s              | otonomarac/tabela.py        |
|                           |                       | gec_pwm            | otonomarac/motor.py         |
+---------------------------+-----------------------+--------------------+-----------------------------+
| Senaryo 3: Renkli Park    | otonomarac/config.yaml| varsayilan_renk    | otonomarac/park_zemin_renk.py|
|                           |                       | park_pwm           | otonomarac/colorlink.py     |
|                           |                       | dur_mesafe_cm      | otonomarac/tabela_gorev.py  |
+---------------------------+-----------------------+--------------------+-----------------------------+
```
**Adli Denetim Notu:**
Hiçbir kaynak kod dosyasında (`.py`) mantıksal yapı, sınıf yapısı, fonksiyon imzası veya karar blokları (`if/else`) bozulmamıştır. Sistem, sıfır yazılım tecrübesine sahip bir operatörün yalnızca `KILAVUZ.md` okuyarak tüm yarışma sürecini yönetebileceği modüler bir mimariye sahiptir.

---

## 7. PİST ÖNCESİ 60 SANİYELİK SON KONTROL LİSTESİ (PRE-FLIGHT CHECKLIST)

Hakem talepleri uygulandıktan sonra aracı piste bırakmadan önce şu 5 maddeyi hızla teyit edin:

1. [ ] **TAB Kontrolü:** `grep -n $'\t' otonomarac/config.yaml` komutu boş döndü mü?
2. [ ] **Dosya Kaydedildi mi:** Düzenleyici penceresinde kaydedilmemiş dosya işareti (yuvarlak nokta) kalmadı mı?
3. [ ] **USB / Seri Bağlantı:** Motor sürücüsünün USB kablosu takılı mı? (`[motor] baglandi: /dev/ttyUSB0`)
4. [ ] **Kamera Lensi:** RealSense D455 derinlik kamerası lensleri temiz ve kapağı açık mı?
5. [ ] **Başlatma Modu:** Hakem kalkış emrini verdiğinde:
   - Terminalde `otonomarac/` klasörüne geçin: `cd otonomarac`
   - Eğer robot kol hazır ve MQTT açıksa: `python3 main.py` (veya proje kökünden `python3 otonomarac/main.py`)
   - Eğer uzaktan bağlantı baypas edilecekse: `python3 main.py --no-remote` (veya proje kökünden `python3 otonomarac/main.py --no-remote`)
   - Klavyeden `Space` tuşuna basıp otonom sürüşü başlatın!

---
*Kovan Zeka Otonom Araç ve Robotik Takımı — Yarışmada Başarılar Dileriz!*
