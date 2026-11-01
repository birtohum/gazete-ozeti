"""Özetlerden statik site üretir: site/YYYYMMDD.html (gün) + site/index.html (son gün + arşiv).
Ayrıca bulten(tarih, konular) Telegram/e-posta için düz metin döndürür.

Kullanım: python sayfa.py
"""
import html
import json
import shutil
from datetime import datetime
from pathlib import Path

from cek import VERI
from ozet import KONULAR

SITE = Path(__file__).parent / "site"
AYLAR = "Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık".split()
KONU_AD = {"vergi": "Vergi", "sgk-calisma": "SGK ve çalışma", "ticaret-sirket": "Ticaret ve şirketler",
           "dis-ticaret-gumruk": "Dış ticaret ve gümrük", "finans-banka": "Finans ve banka", "enerji": "Enerji",
           "tarim-hayvancilik": "Tarım", "saglik-ilac": "Sağlık ve ilaç", "egitim": "Eğitim",
           "kamu-personeli": "Kamu personeli", "imar-kamulastirma": "İmar ve kamulaştırma",
           "ulastirma": "Ulaştırma", "bilisim-iletisim": "Bilişim ve iletişim", "cevre": "Çevre",
           "hukuk-yargi": "Hukuk ve yargı", "teskilat-atama": "Teşkilat ve atama",
           "uluslararasi": "Uluslararası", "diger": "Diğer"}
ONEM_SIRA = {"yuksek": 0, "orta": 1, "dusuk": 2}
ONEM_AD = {"yuksek": "Geniş kitleyi etkiler", "orta": "Sektörel", "dusuk": "Kurumsal / dar kapsamlı"}
e = html.escape


def tarih_yaz(t):
    return f"{int(t[6:])} {AYLAR[int(t[4:6]) - 1]} {t[:4]}"


def gunler():
    """Gazete çıkan (en az bir maddesi olan) günler; bayramlarda fihrist boş gelir."""
    return sorted((p.parent.name for p in VERI.glob("*/ozet.json")
                   if json.loads(p.read_text(encoding="utf-8"))["maddeler"]), reverse=True)


def yukle(t):
    return json.loads((VERI / t / "ozet.json").read_text(encoding="utf-8"))


def sirali(gun):
    ok = [(i, m) for i, m in enumerate(gun["maddeler"]) if "hata" not in m["ozet"]]
    return [m for i, m in sorted(ok, key=lambda x: (ONEM_SIRA.get(x[1]["ozet"].get("onem"), 3), x[0]))]


def kart(m):
    o = m["ozet"]
    dogru = [d for d in o.get("degisiklikler", []) if d.get("dogrulandi")]
    eksik = len(o.get("degisiklikler", [])) - len(dogru)
    maddeler = "".join(
        f'<li>{e(d["ne"])}<details><summary>Metindeki dayanak</summary><blockquote>{e(d["dayanak"])}</blockquote></details></li>'
        for d in dogru)
    notlar = []
    if eksik:
        notlar.append(f"{eksik} iddia metinle doğrulanamadığı için gösterilmiyor.")
    if o.get("eksik_okuma"):
        notlar.append("Metin çok uzun; özet yalnızca baş kısmına dayanıyor.")
    if m["bilgi"].get("kaynak") == "ocr" or m["bilgi"].get("resim"):
        notlar.append("Metin taranmış görüntüden okundu; sayıları aslından kontrol edin.")
    yururluk = ""
    if o.get("yururluk") and o.get("yururluk_benzerlik", 0) >= 0.9:
        yururluk = f'<p class="meta"><b>Yürürlük:</b> {e(o["yururluk"])}</p>'
    return f"""
<article class="kart" data-konular="{' '.join(o['konular'])}" data-onem="{e(o.get('onem', ''))}">
  <div class="ust"><span class="onem {e(o.get('onem', ''))}">{ONEM_AD.get(o.get('onem'), '')}</span>
    {''.join(f'<span class="etiket">{KONU_AD[k]}</span>' for k in o['konular'])}</div>
  <h3>{e(m['baslik'])}</h3>
  <p class="tek">{e(o.get('tek_cumle', ''))}</p>
  {f'<ul>{maddeler}</ul>' if maddeler else ''}
  {f'<p class="meta"><b>Kimi etkiler:</b> {e(o["kimi_etkiler"])}</p>' if o.get('kimi_etkiler') else ''}
  {yururluk}
  {''.join(f'<p class="not">{e(n)}</p>' for n in notlar)}
  <a class="asil" href="{e(m['url'])}" target="_blank" rel="noopener">Resmî Gazete'deki aslı →</a>
</article>"""


CSS = """
:root{--bg:#f7f6f2;--yuzey:#fff;--yazi:#1d1d1b;--soluk:#66645e;--cizgi:#e3e0d8;--vurgu:#8a2b1f;
--yuksek:#8a2b1f;--orta:#7a5a12;--dusuk:#55625a;--etiket:#efece4}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--yuzey:#1f1f1c;--yazi:#ecebe6;--soluk:#a3a198;
--cizgi:#34332f;--vurgu:#e0897b;--yuksek:#e0897b;--orta:#d9b45f;--dusuk:#9db3a6;--etiket:#2a2926}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--yazi);
font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
.sar{max-width:760px;margin:0 auto;padding:24px 16px 64px}
header h1{font:600 26px/1.2 Georgia,serif;margin:0 0 4px}header p{margin:0;color:var(--soluk)}
.uyari{font-size:14px;color:var(--soluk);border-left:3px solid var(--vurgu);padding:6px 12px;margin:16px 0}
.filtre{display:flex;flex-wrap:wrap;gap:6px;margin:16px 0}
.filtre button{border:1px solid var(--cizgi);background:var(--yuzey);color:var(--yazi);border-radius:999px;
padding:4px 12px;font-size:14px;cursor:pointer}.filtre button.secili{background:var(--yazi);color:var(--bg)}
.kart{background:var(--yuzey);border:1px solid var(--cizgi);border-radius:10px;padding:16px 18px;margin:12px 0}
.kart h3{font-size:15px;font-weight:600;margin:8px 0 6px;color:var(--soluk)}
.tek{font-size:17px;margin:0 0 8px}.kart ul{margin:6px 0;padding-left:20px}.kart li{margin:4px 0}
details summary{font-size:13px;color:var(--soluk);cursor:pointer}
blockquote{margin:4px 0;padding:4px 10px;border-left:2px solid var(--cizgi);font-size:14px;color:var(--soluk)}
.ust{display:flex;flex-wrap:wrap;gap:6px;font-size:12px}
.etiket{background:var(--etiket);border-radius:4px;padding:1px 7px}
.onem{font-weight:600}.onem.yuksek{color:var(--yuksek)}.onem.orta{color:var(--orta)}.onem.dusuk{color:var(--dusuk)}
.meta{font-size:14px;margin:6px 0}.not{font-size:13px;color:var(--soluk);margin:4px 0}
.asil{font-size:14px;color:var(--vurgu)}.arsiv a{color:var(--vurgu)}
.gizli{display:none}footer{margin-top:32px;font-size:13px;color:var(--soluk)}
"""

JS = """
document.querySelectorAll('.filtre button').forEach(b=>b.onclick=()=>{
 document.querySelectorAll('.filtre button').forEach(x=>x.classList.remove('secili'));b.classList.add('secili');
 const k=b.dataset.k;document.querySelectorAll('.kart').forEach(a=>
  a.classList.toggle('gizli',!(k==='hepsi'||(k==='onemli'?a.dataset.onem!=='dusuk':a.dataset.konular.split(' ').includes(k)))));
 try{localStorage.setItem('konu',k)}catch(_){}});
try{const k=localStorage.getItem('konu');if(k){const b=document.querySelector(`.filtre button[data-k="${k}"]`);b&&b.click()}}catch(_){}
"""


def gun_sayfasi(t, arsiv):
    g = yukle(t)
    ms = sirali(g)
    var = sorted({k for m in ms for k in m["ozet"]["konular"]}, key=KONULAR.index)
    dugmeler = '<button data-k="hepsi" class="secili">Hepsi</button><button data-k="onemli">Önemliler</button>' + \
        "".join(f'<button data-k="{k}">{KONU_AD[k]}</button>' for k in var)
    toplam = sum(len(m["ozet"].get("degisiklikler", [])) for m in ms)
    dogru = sum(d.get("dogrulandi", False) for m in ms for d in m["ozet"].get("degisiklikler", []))
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gazete Özeti · {tarih_yaz(t)}</title><style>{CSS}</style></head><body><div class="sar">
<header><h1>Resmî Gazete, {tarih_yaz(t)}</h1>
<p>Sayı {e(g['sayi'] or '?')} · {len(ms)} metin · {dogru}/{toplam} iddia metinle doğrulandı</p></header>
<p class="uyari">Bu sayfa yapay zekâ ile hazırlanır. Her madde, Resmî Gazete metninden birebir alıntıyla
eşleştirilip ayrıca denetlenir; doğrulanamayan iddialar gösterilmez. Yine de hukuki karar vermeden önce
aslını okuyun.</p>
<nav class="filtre">{dugmeler}</nav>
{''.join(kart(m) for m in ms)}
<footer class="arsiv">Arşiv: {' · '.join(f'<a href="{x}.html">{tarih_yaz(x)}</a>' for x in arsiv)}</footer>
</div><script>{JS}</script></body></html>"""


def bulten(t, konular=None, sadece_onemli=False):
    """Telegram/e-posta için düz metin. konular=None ise hepsi."""
    g = yukle(t)
    satirlar = [f"📰 Resmî Gazete, {tarih_yaz(t)} (sayı {g['sayi']})", ""]
    for m in sirali(g):
        o = m["ozet"]
        if konular and not set(konular) & set(o["konular"]):
            continue
        if sadece_onemli and o.get("onem") == "dusuk":
            continue
        satirlar.append(f"• {o.get('tek_cumle', '')}")
        satirlar += [f"   – {d['ne']}" for d in o.get("degisiklikler", []) if d.get("dogrulandi")][:3]
        satirlar.append(f"   Aslı: {m['url']}")
        satirlar.append("")
    if len(satirlar) == 2:
        satirlar.append("Seçtiğiniz konularda bugün yayımlanan bir düzenleme yok.")
    return "\n".join(satirlar)


def uret():
    SITE.mkdir(exist_ok=True)
    tum = gunler()
    for t in tum:
        (SITE / f"{t}.html").write_text(gun_sayfasi(t, tum), encoding="utf-8")
    if tum:
        shutil.copy(SITE / f"{tum[0]}.html", SITE / "index.html")
    return tum


if __name__ == "__main__":
    print("üretildi:", uret(), datetime.now().strftime("%H:%M"))
