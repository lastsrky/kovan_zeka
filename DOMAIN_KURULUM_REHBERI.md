# 🌐 TEKNOFEST Arama Motoru & Saha Portalı — Domain Kurulum Rehberi

Bu rehber, projenizdeki arama motorunu, revizyon bankasını ve kılavuzları kendi satın aldığınız alan adına (**domain**) bağlamanız için hazırlanmıştır.

---

## 🚀 1. YÖNTEM: GitHub Pages ile Ücretsiz Yayınlama (Önerilen)

GitHub Pages; sunucu masrafı olmadan, dünyanın en hızlı sunucularından sitenizi ücretsiz ve otomatik SSL (https) sertifikalı olarak yayınlar.

### Adım 1: Alan Adınızı `CNAME` Dosyasına Yazın
1. Projedeki **`CNAME`** dosyasını açın.
2. İçindeki `ornekalanadi.com` yazısını silip kendi gerçek alan adınızı yazın ve kaydedin:
   - Eğer ana alan adı kullanacaksanız: `siteniz.com`
   - Eğer alt alan adı (subdomain) kullanacaksanız: `arama.siteniz.com`
3. Dosyayı GitHub'a gönderin (push edin).

---

### Adım 2: GitHub Pages'i Aktif Edin
1. GitHub reponuza gidin: `https://github.com/lastsrky/kovan_zeka`
2. Üst menüden **Settings** (Ayarlar) sekmesine tıklayın.
3. Sol menüden **Pages** seçeneğine tıklayın.
4. **Branch** kısmında `None` yerine **`main`** seçip **Save** butonuna basın.
5. Sayfayı yenilediğinizde **Custom domain** kutusunda `CNAME` dosyasındaki alan adınızın otomatik geldiğini göreceksiniz.
6. Altındaki **Enforce HTTPS** seçeneğini işaretleyin (Ücretsiz yeşil kilit SSL verir).

---

### Adım 3: Domain Firmanızda DNS Yönlendirmesi Yapın
Domaini aldığınız firmanın (GoDaddy, Natro, Turhost, IHS, Cloudflare vb.) **DNS Yönetimi** sayfasına girin ve şu kaydı ekleyin:

#### Durum A: Alt Alan Adı Kullanacaksanız (Örn: `arama.siteniz.com`)
| Kayıt Türü | Ad / Host / İsim | Hedef / Değer / Değer | TTL |
| :--- | :--- | :--- | :--- |
| **CNAME** | `arama` | `lastsrky.github.io` | Otomatik / 3600 |

#### Durum B: Ana Alan Adı Kullanacaksanız (Örn: `siteniz.com`)
Domain yönetiminde 4 adet GitHub IP adresi için **A Kaydı** ekleyin:
| Kayıt Türü | Ad / Host / İsim | Hedef / IP Adresi | TTL |
| :--- | :--- | :--- | :--- |
| **A** | `@` | `185.199.108.153` | Otomatik / 3600 |
| **A** | `@` | `185.199.109.153` | Otomatik / 3600 |
| **A** | `@` | `185.199.110.153` | Otomatik / 3600 |
| **A** | `@` | `185.199.111.153` | Otomatik / 3600 |

*(DNS kayıtlarının dünyada yayılması 5 ila 30 dakika sürebilir; ardından siteniz doğrudan yayına girer).*

---

## 📁 2. YÖNTEM: Klasik cPanel / Web Hosting Kullanımı

Eğer hali hazırda aylık/yıllık ücretini ödediğiniz bir web hosting paketiniz (cPanel, Plesk vb.) varsa:

1. cPanel panelinize giriş yapın.
2. **Dosya Yöneticisi (File Manager)** -> **`public_html`** klasörüne girin.
3. Projemizde oluşturulan **`index.html`** dosyasını buraya yükleyin (varsa eski index dosyasını silin veya yedekleyin).
4. İşlem tamam! Siteniz hiçbir sunucu ayarı yapmadan doğrudan `https://alanadiniz.com` adresinde açılacaktır.

---

## 🔄 İleride Dosyalar Güncellenirse Ne Yapmalısınız?
Eğer `REVIZYON_SENARYO_BANKASI.md` veya kodlarda yeni bir değişiklik yaparsanız, tek bir komutla web sitesini güncelleyebilirsiniz:

```powershell
python build_static_site.py
git add index.html
git commit -m "update: Web portali guncellendi"
git push origin main
```
Web siteniz anında en güncel verilerle güncellenecektir!
