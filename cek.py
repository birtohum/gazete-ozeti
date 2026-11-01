"""Bir günün Resmî Gazete'sini çeker: fihristi maddelere ayırır, her maddenin metnini indirir.

Kullanım: python cek.py [YYYYMMDD]   (tarih verilmezse bugün)
Çıktı: veri/YYYYMMDD/maddeler.json
"""
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pymupdf

from api import resim, sor

KOK = "https://www.resmigazete.gov.tr/eskiler"
SAYFA_UST = 20  # çok uzun PDF'lerin yalnızca başı okunur
VERI = Path(__file__).parent / "veri"
UA = {"User-Agent": "Mozilla/5.0 (gazete-ozet; kisisel proje)"}


def indir(url, deneme=3):
    for i in range(deneme):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception as h:
            if i == deneme - 1 or getattr(h, "code", None) == 404:
                raise
            time.sleep(3 * (i + 1))


def duz(s):
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)  # Word'ün <!--[if gte mso]> çöpü
    s = re.sub(r"<(script|style|xml)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</tr>|</div>", "\n", s, flags=re.I)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")
    s = re.sub(r"[ \t\r]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n\n", s).strip()


def fihrist(tarih, ek=""):
    """Fihristteki maddeleri bölüm başlıklarıyla birlikte sırayla döndürür. ek: "" ya da mükerrer için "M1".."""
    yol = f"{KOK}/{tarih[:4]}/{tarih[4:6]}/{tarih}{ek}.htm"
    ham = indir(yol).decode("windows-1254", errors="replace")
    tarih += ek
    sayi = re.search(r"(\d{5})\s*Say", duz(ham))
    maddeler, bolum = [], ""
    # Bölüm başlıkları bağlantısız büyük harf satırlar; maddeler '––' ile başlayan bağlantılar.
    for parca in re.split(r"(<a[^>]+href=\"[^\"]+\"[^>]*>.*?</a>)", ham, flags=re.S | re.I):
        m = re.match(r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", parca, flags=re.S | re.I)
        if not m:
            for satir in duz(parca).split("\n"):
                satir = satir.strip()
                if len(satir) > 3 and satir == satir.upper() and re.search(r"[A-ZÇĞİÖŞÜ]{3}", satir):
                    bolum = re.sub(r"\s+", " ", satir)
            continue
        href, baslik = m.group(1), re.sub(r"\s+", " ", duz(m.group(2))).strip("–- \u0096")
        if not re.match(rf"{tarih}-\d+\.(htm|pdf)$", href) or not baslik:
            continue  # tam sayı pdf'i, ilan bölümleri ve kurlar atlanır
        maddeler.append({"no": f"{ek}-{re.search(r'-(\d+)', href).group(1)}" if ek else int(re.search(r"-(\d+)\.", href).group(1)),
                         "mukerrer": ek, "bolum": bolum,
                         "baslik": baslik, "url": f"{KOK}/{tarih[:4]}/{tarih[4:6]}/{href}"})
    return (sayi.group(1) if sayi else None), maddeler


OCR_ISTEM = ("Bu, Resmî Gazete'nin taranmış bir sayfası. Sayfadaki metni aynen, eksiksiz ve "
             "satır sırasıyla yaz. Tabloları satır satır, hücreleri ' | ' ile ayırarak yaz. "
             "Yorum, özet ya da açıklama ekleme; okunamayan yeri [okunamadı] diye işaretle.")


def ocr(sayfa):
    return sor([{"type": "text", "text": OCR_ISTEM}, resim(sayfa.get_pixmap(dpi=150).tobytes("png"))],
               etiket="ocr")


def htm_metin(url, ham):
    """HTML maddelerde tablolar çoğu zaman resim olarak gömülü: onları da okuyup yerine koyar."""
    srcs = list(dict.fromkeys(re.findall(r'<img[^>]+src="([^"]+)"', ham, flags=re.I)))
    okunan = {}
    for src in srcs:
        veri = indir(url.rsplit("/", 1)[0] + "/" + src)
        if len(veri) < 5000:  # süs/çizgi resimleri
            continue
        tur = "png" if src.lower().endswith(".png") else "jpeg"
        okunan[src] = sor([{"type": "text", "text": OCR_ISTEM.replace("taranmış bir sayfası",
                                                                       "içindeki bir tablo/resim")},
                           resim(veri, tur)], etiket="ocr-resim")
    ham = re.sub(r'<img[^>]+src="([^"]+)"[^>]*>',
                 lambda m: f"\n[RESİMDEN OKUNDU]\n{okunan[m.group(1)]}\n[/RESİM]\n" if m.group(1) in okunan else " ",
                 ham, flags=re.I)
    return duz(ham), {"kaynak": "htm", "resim": len(okunan)}


def metin(url):
    """(metin, bilgi) döndürür. Taranmış PDF'ler Spark ile okunur; ilk SAYFA_UST sayfa."""
    veri = indir(url)
    if not url.endswith(".pdf"):
        return htm_metin(url, veri.decode("windows-1254", errors="replace"))
    with pymupdf.open(stream=veri, filetype="pdf") as d:
        gomulu = "\n".join(s.get_text() for s in d).strip()
        if len(gomulu) > 300 * len(d):  # metin katmanı varsa onu kullan
            return gomulu, {"kaynak": "pdf", "sayfa": len(d)}
        sayfalar = list(d)[:SAYFA_UST]
        with ThreadPoolExecutor(8) as h:
            parcalar = list(h.map(ocr, sayfalar))
        return "\n\n".join(parcalar), {"kaynak": "ocr", "sayfa": len(d), "okunan": len(sayfalar)}


def cek(tarih):
    hedef = VERI / tarih / "maddeler.json"
    if hedef.exists():
        return json.loads(hedef.read_text(encoding="utf-8"))
    sayi, maddeler = fihrist(tarih)
    for i in range(1, 10):  # mükerrer sayılar: tarihM1.htm, M2... ilk 404'te biter
        try:
            maddeler += fihrist(tarih, f"M{i}")[1]
        except urllib.error.HTTPError:
            break
    for m in maddeler:
        m["metin"], m["bilgi"] = metin(m["url"])
        time.sleep(0.5)
    sonuc = {"tarih": tarih, "sayi": sayi, "maddeler": maddeler}
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    return sonuc


if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else date.today().strftime("%Y%m%d")
    s = cek(t)
    print(f"{t} sayı {s['sayi']}: {len(s['maddeler'])} madde")
    for m in s["maddeler"]:
        print(f"  {m['no']:>2} [{m['bolum'][:25]}] {m['baslik'][:80]}  ({len(m['metin'])} kr, {m['bilgi']})")
