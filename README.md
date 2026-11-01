# Gazete Özeti

Her gün Resmî Gazete'yi okuyup her düzenlemeyi sade Türkçeyle özetleyen ve konuya göre süzen bir araç.
Özetteki her iddia, Resmî Gazete metninden birebir alıntıyla eşleştirilip denetlenir;
doğrulanamayan iddia yayımlanmaz.

> Durum: prototip. Gerçek kullanıcıyla henüz denenmedi.

## Nasıl çalışır

```
resmigazete.gov.tr fihristi
   │  cek.py: maddeleri ayır, metni indir
   │   ├─ HTML maddeler: metin + içine resim olarak gömülü tablolar (Muse Spark ile okunur)
   │   └─ PDF maddeler: çoğu taranmış görüntü → sayfa sayfa Muse Spark ile okunur
   ▼
ozet.py: Muse Spark (muse-spark-1.3-contributor)
   │   özet + konu + önem + her değişiklik için birebir alıntı (JSON)
   │  doğrulama 1 (kod): alıntı metinde geçiyor mu? (bulanık eşleşme ≥ 0.90)
   │  doğrulama 2 (model, ayrı çağrı): alıntının çevresindeki metin iddiayı destekliyor mu?
   ▼
sayfa.py: statik site (konu süzgeci) + konuya göre bülten metni
```

## Çalıştırma

```bash
python -m venv .venv && .venv/Scripts/python -m pip install pymupdf
.venv/Scripts/python ozet.py 20261031   # çeker, özetler, doğrular
.venv/Scripts/python sayfa.py           # site/ klasörünü üretir
.venv/Scripts/python denetim.py 20      # elle denetim için rastgele 20 doğrulanmış iddia
```

Anahtar: `META_MODEL_API_KEY` ortam değişkeni (ya da `~/.pflow-anahtarlar.env`).
Harcama `kayitlar/butce.jsonl`'e yazılır; `GAZETE_TAVAN` (varsayılan 20 $) aşılınca durur.

## Ölçümler

Kapsam: 28, 30, 31 Ekim ve 1 Kasım 2026 sayıları (29 Ekim bayram, gazete yok). 37 metin; 21'i taranmış PDF.

| Ölçüm | Sonuç |
|---|---|
| Alıntısı metinde bulunan iddia | 180 / 180 |
| İki doğrulamayı da geçen (yayımlanan) iddia | 172 / 180 (%96) |
| Elle denetim: rastgele 25 yayımlanmış iddia, metinle karşılaştırıldı | 25 / 25 doğru |
| Maliyet | 0,16 $ toplam, gün başına ~0,04 $ (OCR dahil) |

Elle denetim küçük bir örneklem: 25/25, gerçek hata oranının %12'nin altında olduğunu söyler
(yaklaşık %95 güvenle); %1'in altında olduğunu söylemez. Ölçülmeyenler: özetin **eksiksizliği**
(önemli bir değişikliğin atlanıp atlanmadığı), önem sınıflamasının doğruluğu ve OCR'nin sayfa
genelindeki hata oranı.

## Bilinen sınırlar

- **Hakem ile özetleyen aynı model.** İkinci doğrulama katmanı bağımsız değil; aynı hatayı ikisi birden yapabilir.
  Elle denetim bu yüzden ayrıca yapılıyor (yukarıdaki tablo).
- **OCR.** Taranmış sayfalar modelle okunuyor; alıntı denetimi okunmuş metne karşı yapıldığından,
  OCR hatası doğrulamadan geçebilir. Sayfada bu maddeler ayrıca işaretleniyor.
- **İnce anlam farkları.** Model bazen "satıldı" der, metin "satışın onaylanmasına" der. Somut bilgiler
  (sayı, kurum, tarih) denetleniyor; fiil kipindeki bu tür kaymalar her zaman yakalanmıyor.
- **Uzun metinler.** 20 sayfadan uzun PDF'lerin yalnızca ilk 20 sayfası okunuyor (ör. 105 sayfalık uluslararası anlaşmalar).
- **İlanlar bölümü** (ihale, yargı ilanları) şimdilik kapsam dışı.
- Ücretsiz Meta kredisiyle gönderilen içerik Meta'nın ürün geliştirmesinde kullanılabilir;
  bu yüzden araç yalnızca kamuya açık gazete metnini gönderir, kullanıcı verisi göndermez.

Hukuki tavsiye değildir; karar vermeden önce aslını okuyun.
