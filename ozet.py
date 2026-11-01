"""Bir günün maddelerini özetler ve her iddiayı metne karşı doğrular.

Doğrulama iki katmanlı:
 1. Kod: modelin her iddia için verdiği "dayanak" alıntısı metinde gerçekten geçiyor mu (bulanık eşleşme).
 2. Model: alıntı, iddiayı gerçekten destekliyor mu (ayrı çağrı, yalnızca iddia + alıntı görür).
İkisini de geçemeyen iddia yayımlanmaz, "doğrulanamadı" sayılır.

Kullanım: python ozet.py YYYYMMDD
Çıktı: veri/YYYYMMDD/ozet.json
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

from api import sor
from cek import VERI, cek

KONULAR = ["vergi", "sgk-calisma", "ticaret-sirket", "dis-ticaret-gumruk", "finans-banka", "enerji",
           "tarim-hayvancilik", "saglik-ilac", "egitim", "kamu-personeli", "imar-kamulastirma",
           "ulastirma", "bilisim-iletisim", "cevre", "hukuk-yargi", "teskilat-atama", "uluslararasi", "diger"]
METIN_UST = 40000  # karakter; daha uzunu kesilir ve özette belirtilir

OZET_ISTEM = """Aşağıda Resmî Gazete'de yayımlanmış bir metin var. Hukukçu olmayan biri için sade Türkçeyle özetle.

Kurallar:
- Yalnızca metinde yazanı söyle. Tahmin, yorum, "muhtemelen" yok.
- Her değişiklik için metinden BİREBİR kopyalanmış kısa bir alıntı ver (dayanak, en fazla 250 karakter, kelimesi kelimesine).
- Metin bir değişiklik yapıyorsa eski ve yeni hâli metinde açıkça varsa ikisini de yaz; yoksa yalnızca yeni hâli yaz.
- En fazla 6 değişiklik; önemli olanları seç.
- konular yalnızca şu listeden: {konular}
- onem: "yuksek" = geniş kitleyi (çalışanlar, vergi mükellefleri, esnaf, öğrenciler vb.) doğrudan etkiliyor; "orta" = belirli bir sektörü/meslek grubunu etkiliyor; "dusuk" = kurum içi, teşkilat, tek bir taşınmaz, atama vb.

Yalnızca şu JSON'u döndür:
{{"konular": [...], "onem": "...", "tek_cumle": "en fazla 25 kelimelik özet",
  "degisiklikler": [{{"ne": "sade anlatım", "dayanak": "birebir alıntı"}}],
  "kimi_etkiler": "kısa", "yururluk": "metinde yazdığı şekliyle; yoksa boş", "yururluk_dayanak": "birebir alıntı ya da boş"}}

BAŞLIK: {baslik}
{kesik}
METİN:
{metin}"""

DOGRULA_ISTEM = """Resmî Gazete metninin özetini denetliyorsun. Her maddede bir İDDİA ve metinden alınmış bir BÖLÜM var.
BÖLÜM, İDDİA'yı destekliyor mu?
"evet": iddiadaki her somut bilgi (sayı, tarih, oran, kurum, kişi, kapsam) bölümde var; sade dille yeniden anlatım sorun değil.
"hayir": iddia bölümde olmayan somut bir bilgi ekliyor, kapsamı genişletiyor ya da bölümle çelişiyor.
Yalnızca şu JSON'u döndür: {{"sonuc": ["evet"|"hayir", ...]}}  (madde sayısı kadar)

{satirlar}"""
BAGLAM = 700  # hakeme alıntının iki yanından verilen karakter


def norm(s):
    s = s.replace("İ", "i").replace("I", "ı").lower()
    s = re.sub(r"[“”\"'’‘`´]", "", s)
    s = re.sub(r"-\s*\n\s*", "", s)  # satır sonu tirelemesi
    return re.sub(r"\s+", " ", s).strip()


def metinde_mi(alinti, metin):
    """Alıntı metinde birebir ya da çok yakın (OCR/boşluk farkı) geçiyor mu. 0..1 benzerlik döndürür."""
    a, m = norm(alinti), norm(metin)
    if not a:
        return 0.0
    if a in m:
        return 1.0
    # alıntının ilk 20 karakterine en çok benzeyen pencereleri dene
    en_iyi, n = 0.0, len(a)
    tohum = a[:20]
    adaylar = [i for i in range(0, max(1, len(m) - n + 1)) if m.startswith(tohum[:8], i)] or range(0, max(1, len(m) - n + 1), max(1, n // 4))
    for i in adaylar:
        en_iyi = max(en_iyi, SequenceMatcher(None, a, m[i:i + n + 10]).ratio())
        if en_iyi > 0.97:
            break
    return en_iyi


def baglam(alinti, metin):
    """Alıntının özgün metindeki yerini ilk kelimelerinden bulup çevresini döndürür."""
    kelimeler = re.findall(r"\w+", alinti)[:6]
    m = re.search(r"\W+".join(map(re.escape, kelimeler)), metin, flags=re.I) if kelimeler else None
    i = m.start() if m else 0
    return metin[max(0, i - BAGLAM): i + len(alinti) + BAGLAM]


def json_al(s):
    s = re.sub(r"^```(json)?|```$", "", s.strip(), flags=re.M).strip()
    return json.loads(s[s.find("{"): s.rfind("}") + 1])


def ozetle(madde):
    metin = madde["metin"]
    kesik = ""
    if len(metin) > METIN_UST:
        metin, kesik = metin[:METIN_UST], "(NOT: Metin çok uzun, yalnızca başı veriliyor.)\n"
    if madde.get("bilgi", {}).get("okunan", 0) < madde.get("bilgi", {}).get("sayfa", 0):
        kesik += f"(NOT: {madde['bilgi']['sayfa']} sayfanın yalnızca ilk {madde['bilgi']['okunan']} sayfası okundu.)\n"
    for deneme in range(3):
        try:
            o = json_al(sor(OZET_ISTEM.format(konular=", ".join(KONULAR), baslik=madde["baslik"],
                                              kesik=kesik, metin=metin), json_mod=True, etiket="ozet"))
            break
        except (json.JSONDecodeError, ValueError):
            if deneme == 2:
                return {"hata": "özet JSON'u okunamadı"}
    o["konular"] = [k for k in o.get("konular", []) if k in KONULAR] or ["diger"]
    o["eksik_okuma"] = bool(kesik)

    # 1. katman: alıntılar metinde var mı
    for d in o.get("degisiklikler", []):
        d["alinti_benzerlik"] = round(metinde_mi(d.get("dayanak", ""), madde["metin"]), 3)
    if o.get("yururluk_dayanak"):
        o["yururluk_benzerlik"] = round(metinde_mi(o["yururluk_dayanak"], madde["metin"]), 3)

    # 2. katman: alıntı iddiayı destekliyor mu
    adaylar = [d for d in o.get("degisiklikler", []) if d["alinti_benzerlik"] >= 0.9]
    if adaylar:
        satirlar = "\n\n".join(f"{i + 1}. İDDİA: {d['ne']}\n   BÖLÜM: «{baglam(d['dayanak'], madde['metin'])}»"
                               for i, d in enumerate(adaylar))
        try:
            sonuc = json_al(sor(DOGRULA_ISTEM.format(satirlar=satirlar), json_mod=True, etiket="dogrula"))["sonuc"]
        except Exception:
            sonuc = []
        for d, s in zip(adaylar, sonuc):
            d["destek"] = s
    for d in o.get("degisiklikler", []):
        d["dogrulandi"] = d["alinti_benzerlik"] >= 0.9 and d.get("destek") == "evet"
    return o


def gun(tarih):
    veri = cek(tarih)
    hedef = VERI / tarih / "ozet.json"
    eski = {}
    if hedef.exists():
        eski = {m["no"]: m for m in json.loads(hedef.read_text(encoding="utf-8"))["maddeler"]}
    with ThreadPoolExecutor(6) as h:
        ozetler = list(h.map(lambda m: eski.get(m["no"], {}).get("ozet") or ozetle(m), veri["maddeler"]))
    sonuc = {"tarih": tarih, "sayi": veri["sayi"], "maddeler": [
        {k: m[k] for k in ("no", "bolum", "baslik", "url", "bilgi")} | {"ozet": o}
        for m, o in zip(veri["maddeler"], ozetler)]}
    hedef.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    return sonuc


if __name__ == "__main__":
    s = gun(sys.argv[1])
    toplam = dogru = 0
    for m in s["maddeler"]:
        o = m["ozet"]
        if "hata" in o:
            print(m["no"], "HATA", o["hata"]); continue
        dd = o.get("degisiklikler", [])
        toplam += len(dd); dogru += sum(d["dogrulandi"] for d in dd)
        print(f"{m['no']:>2} [{o['onem']:<6}] {','.join(o['konular'])}: {o['tek_cumle']}")
        for d in dd:
            print(f"     {'✓' if d['dogrulandi'] else '✗'} ({d['alinti_benzerlik']}, {d.get('destek', '-')}) {d['ne'][:110]}")
    print(f"\ndoğrulanan iddia: {dogru}/{toplam}")
