"""Özetlerden statik site üretir: site/YYYYMMDD.html (gün) + site/index.html (son gün + arşiv).
Görünüm bir gazete ön sayfası gibi: en geniş etkili düzenleme manşette, diğerleri sütunlarda.
Ayrıca bulten(tarih, konular) Telegram/e-posta için düz metin döndürür.

Kullanım: python sayfa.py
"""
import html
import json
import shutil
from datetime import date, datetime
from pathlib import Path

from cek import VERI
from ozet import KONULAR

SITE = Path(__file__).parent / "site"
AYLAR = "Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık".split()
GUNLER = "Pazartesi Salı Çarşamba Perşembe Cuma Cumartesi Pazar".split()
KONU_AD = {"vergi": "Vergi", "sgk-calisma": "SGK ve çalışma", "ticaret-sirket": "Ticaret ve şirketler",
           "dis-ticaret-gumruk": "Dış ticaret ve gümrük", "finans-banka": "Finans ve banka", "enerji": "Enerji",
           "tarim-hayvancilik": "Tarım", "saglik-ilac": "Sağlık ve ilaç", "egitim": "Eğitim",
           "kamu-personeli": "Kamu personeli", "imar-kamulastirma": "İmar ve kamulaştırma",
           "ulastirma": "Ulaştırma", "bilisim-iletisim": "Bilişim ve iletişim", "cevre": "Çevre",
           "hukuk-yargi": "Hukuk ve yargı", "teskilat-atama": "Teşkilat ve atama",
           "uluslararasi": "Uluslararası", "diger": "Diğer"}
ONEM_SIRA = {"yuksek": 0, "orta": 1, "dusuk": 2}
ONEM_AD = {"yuksek": "Geniş kitleyi etkiler", "orta": "Sektörel", "dusuk": "Kurumsal"}
e = html.escape


def tarih_yaz(t, gun_adi=False):
    s = f"{int(t[6:])} {AYLAR[int(t[4:6]) - 1]} {t[:4]}"
    if gun_adi:
        s += ", " + GUNLER[date(int(t[:4]), int(t[4:6]), int(t[6:])).weekday()]
    return s


def gunler():
    """Gazete çıkan (en az bir maddesi olan) günler; bayramlarda fihrist boş gelir."""
    return sorted((p.parent.name for p in VERI.glob("*/ozet.json")
                   if json.loads(p.read_text(encoding="utf-8"))["maddeler"]), reverse=True)


def yukle(t):
    return json.loads((VERI / t / "ozet.json").read_text(encoding="utf-8"))


def sirali(gun):
    ok = [(i, m) for i, m in enumerate(gun["maddeler"]) if "hata" not in m["ozet"]]
    return [m for i, m in sorted(ok, key=lambda x: (ONEM_SIRA.get(x[1]["ozet"].get("onem"), 3),
                                                    -sum(d.get("dogrulandi", False) for d in x[1]["ozet"].get("degisiklikler", [])),
                                                    x[0]))]


def kart(m, mansetmi=False):
    o = m["ozet"]
    hepsi = o.get("degisiklikler", [])
    dogru = [d for d in hepsi if d.get("dogrulandi")]
    maddeler = "".join(
        f'<li><span>{e(d["ne"])}</span> <button class="dayanak" aria-expanded="false" title="Resmî Gazete metnindeki dayanağı göster">§</button>'
        f'<span class="alinti" hidden>“{e(d["dayanak"].strip(chr(34)+"“”"))}”</span></li>' for d in dogru)
    notlar = []
    if o.get("eksik_okuma"):
        notlar.append("Metin çok uzun; özet yalnızca baş kısmına dayanıyor.")
    if m["bilgi"].get("kaynak") == "ocr" or m["bilgi"].get("resim"):
        notlar.append("Metin taranmış görüntüden okundu; sayıları aslından kontrol edin.")
    yururluk = ""
    if o.get("yururluk") and o.get("yururluk_benzerlik", 0) >= 0.9:
        yururluk = f'<p class="meta"><b>Yürürlük</b> {e(o["yururluk"])}</p>'
    onem = o.get("onem", "")
    rozet = (f'<span class="rozet">✓ {len(dogru)} iddia metinle doğrulandı'
             + (f", {len(hepsi) - len(dogru)} doğrulanamadığı için gizlendi" if len(hepsi) > len(dogru) else "") + "</span>") if hepsi else ""
    return f"""
<article class="kart{' manset' if mansetmi else ''}" data-konular="{' '.join(o['konular'])}" data-onem="{e(onem)}">
  <p class="ust"><span class="onem {e(onem)}">{ONEM_AD.get(onem, '')}</span> · {' · '.join(KONU_AD[k] for k in o['konular'])}</p>
  <h2>{e(o.get('tek_cumle', '') or m['baslik'])}</h2>
  <p class="baslik">{e(m['baslik'])}</p>
  {f'<ul class="degisim">{maddeler}</ul>' if maddeler else ''}
  {f'<p class="meta"><b>Kimi etkiler</b> {e(o["kimi_etkiler"])}</p>' if o.get('kimi_etkiler') else ''}
  {yururluk}
  {''.join(f'<p class="not">{e(n)}</p>' for n in notlar)}
  <p class="alt">{rozet}<a href="{e(m['url'])}" target="_blank" rel="noopener">Aslını oku ↗</a></p>
</article>"""


CSS = """
:root{--kagit:#f6f1e7;--yuzey:#fffdf8;--yazi:#1b1915;--soluk:#6b665c;--cizgi:#1b1915;--ince:#d9d1c1;--vurgu:#a3271a;
--orta:#8a6512;--dusuk:#5b6a60;--isaret:#fde58a}
@media (prefers-color-scheme:dark){:root{--kagit:#15140f;--yuzey:#1d1b16;--yazi:#efe9dc;--soluk:#a8a192;--cizgi:#efe9dc;
--ince:#38342b;--vurgu:#f08a76;--orta:#e0b85c;--dusuk:#9fb6a8;--isaret:#5e4d12}}
*{box-sizing:border-box}
body{margin:0;background:var(--kagit);color:var(--yazi);font:17px/1.6 "Source Serif 4",Georgia,serif}
.sar{max-width:1100px;margin:0 auto;padding:0 16px 64px}
a{color:var(--vurgu)}
.kunye{text-align:center;padding:26px 0 0}
.kunye .ust-yazi{font:600 .72rem/1 Inter,system-ui,sans-serif;letter-spacing:.2em;text-transform:uppercase;color:var(--soluk)}
.kunye h1{font:900 clamp(2.8rem,9vw,5.6rem)/1 "Playfair Display",Georgia,serif;letter-spacing:-.01em;margin:.12em 0 .1em}
.tarih{display:flex;justify-content:space-between;align-items:center;gap:10px;border-top:3px double var(--cizgi);border-bottom:1px solid var(--cizgi);
padding:8px 0;font:600 .82rem/1.3 Inter,system-ui,sans-serif;text-transform:uppercase;letter-spacing:.06em}
.tarih a{text-decoration:none;color:var(--yazi)}.tarih .bos{opacity:.3}
.sayilar{display:flex;justify-content:center;flex-wrap:wrap;gap:6px 26px;padding:14px 0;border-bottom:1px solid var(--ince);font:500 .9rem Inter,system-ui,sans-serif;color:var(--soluk)}
.sayilar b{font:800 1.5rem "Playfair Display",Georgia,serif;color:var(--yazi);margin-right:5px}
.filtre{position:sticky;top:0;z-index:2;background:var(--kagit);display:flex;gap:6px;padding:12px 0;border-bottom:1px solid var(--ince);overflow-x:auto;scrollbar-width:thin}
.filtre button{font:600 .82rem Inter,system-ui,sans-serif;border:1px solid var(--ince);background:var(--yuzey);color:var(--yazi);border-radius:99px;padding:6px 12px;cursor:pointer;min-height:34px;white-space:nowrap;flex:0 0 auto}
.filtre button small{opacity:.55;margin-left:4px}
.filtre button.secili{background:var(--yazi);color:var(--kagit);border-color:var(--yazi)}
.sayfa{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 36px;margin-top:8px}
.kart{padding:22px 0;border-bottom:1px solid var(--ince)}
.kart.manset{grid-column:1/-1;border-bottom:3px double var(--cizgi);padding:26px 0 24px}
.kart .ust{font:700 .72rem/1.3 Inter,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--soluk);margin:0 0 6px}
.onem.yuksek{color:var(--vurgu)}.onem.orta{color:var(--orta)}.onem.dusuk{color:var(--dusuk)}
.kart h2{font:800 1.45rem/1.18 "Playfair Display",Georgia,serif;margin:0 0 6px}
.kart.manset h2{font-size:clamp(1.9rem,4.4vw,3rem);line-height:1.08;max-width:24ch}
.kart .baslik{font-style:italic;color:var(--soluk);font-size:.92rem;margin:0 0 10px}
.kart.manset .baslik{font-size:1rem}
.degisim{margin:0;padding:0;list-style:none}
.kart.manset .degisim{columns:2;column-gap:36px}
.degisim li{position:relative;padding:5px 0 5px 18px;break-inside:avoid}
.degisim li::before{content:"";position:absolute;left:2px;top:.85em;width:7px;height:7px;background:var(--vurgu);transform:rotate(45deg)}
.dayanak{font:700 .8rem Georgia,serif;border:1px solid var(--ince);background:var(--yuzey);color:var(--vurgu);border-radius:5px;width:24px;height:22px;cursor:pointer;vertical-align:1px;padding:0}
.dayanak[aria-expanded="true"]{background:var(--vurgu);color:var(--yuzey);border-color:var(--vurgu)}
.alinti{display:block;margin:6px 0 4px;padding:8px 12px;background:var(--yuzey);border-left:3px solid var(--vurgu);font-size:.9rem;color:var(--soluk)}
.alinti[hidden]{display:none}
.alinti mark{background:var(--isaret);color:inherit}
.fazla{font-size:.88rem;color:var(--soluk);margin:4px 0 0}
.meta{font-size:.92rem;margin:8px 0 0}.meta b{font:700 .7rem Inter,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;margin-right:6px;color:var(--soluk)}
.not{font-size:.85rem;color:var(--soluk);margin:6px 0 0;font-style:italic}
.alt{display:flex;flex-wrap:wrap;justify-content:space-between;gap:6px 14px;align-items:center;margin:12px 0 0;font:500 .8rem Inter,system-ui,sans-serif}
.rozet{color:var(--dusuk)}
.alt a{font-weight:700}
.gizli{display:none}
.nasil{margin:40px 0 0;padding:20px 22px;background:var(--yuzey);border:1px solid var(--ince);font-size:.95rem}
.nasil h3{font:800 1.2rem "Playfair Display",Georgia,serif;margin:0 0 6px}
.nasil p{margin:6px 0}
.arsiv{margin:26px 0 0;font:500 .88rem Inter,system-ui,sans-serif}
.arsiv h3{font:800 1.1rem "Playfair Display",Georgia,serif;margin:0 0 8px}
.arsiv nav{display:flex;flex-wrap:wrap;gap:6px}
.arsiv a{border:1px solid var(--ince);background:var(--yuzey);padding:5px 10px;text-decoration:none;color:var(--yazi)}
.arsiv a.bu{background:var(--yazi);color:var(--kagit)}
footer{margin-top:24px;font:500 .8rem Inter,system-ui,sans-serif;color:var(--soluk)}
@media (max-width:760px){.sayfa{grid-template-columns:1fr}.kart.manset .degisim{columns:1}.tarih{font-size:.72rem}.tarih .kisa{display:none}}
"""

JS = """
document.querySelectorAll('.filtre button').forEach(b=>b.onclick=()=>{
 document.querySelectorAll('.filtre button').forEach(x=>x.classList.remove('secili'));b.classList.add('secili');
 const k=b.dataset.k;document.querySelectorAll('.kart').forEach(a=>
  a.classList.toggle('gizli',!(k==='hepsi'||(k==='onemli'?a.dataset.onem!=='dusuk':a.dataset.konular.split(' ').includes(k)))));
 try{localStorage.setItem('konu',k)}catch(_){}});
try{const k=localStorage.getItem('konu');if(k){const b=document.querySelector(`.filtre button[data-k="${k}"]`);b&&b.click()}}catch(_){}
document.querySelectorAll('.dayanak').forEach(b=>b.onclick=()=>{const q=b.nextElementSibling,ac=q.hidden;q.hidden=!ac;b.setAttribute('aria-expanded',ac)});
"""

KAFA = """<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 fill=%22%23f6f1e7%22/%3E%3Ctext x=%2216%22 y=%2224%22 font-size=%2222%22 font-family=%22Georgia%22 font-weight=%22900%22 text-anchor=%22middle%22 fill=%22%231b1915%22%3EG%3C/text%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@800;900&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=Inter:wght@500;600;700&display=swap" rel="stylesheet">"""


def gun_sayfasi(t, arsiv):
    g = yukle(t)
    ms = sirali(g)
    var = sorted({k for m in ms for k in m["ozet"]["konular"]}, key=KONULAR.index)
    say = {k: sum(k in m["ozet"]["konular"] for m in ms) for k in var}
    onemli = sum(m["ozet"].get("onem") != "dusuk" for m in ms)
    dugmeler = (f'<button data-k="hepsi" class="secili">Hepsi<small>{len(ms)}</small></button>'
                f'<button data-k="onemli">Önemliler<small>{onemli}</small></button>'
                + "".join(f'<button data-k="{k}">{KONU_AD[k]}<small>{say[k]}</small></button>' for k in var))
    toplam = sum(len(m["ozet"].get("degisiklikler", [])) for m in ms)
    dogru = sum(d.get("dogrulandi", False) for m in ms for d in m["ozet"].get("degisiklikler", []))
    genis = sum(m["ozet"].get("onem") == "yuksek" for m in ms)
    i = arsiv.index(t)
    onceki = arsiv[i + 1] if i + 1 < len(arsiv) else None
    sonraki = arsiv[i - 1] if i > 0 else None
    gezin = (f'<a href="{onceki}.html" aria-label="Önceki sayı: {tarih_yaz(onceki)}">← <span class="kisa">{tarih_yaz(onceki)}</span></a>' if onceki else '<span class="bos">←</span>',
             f'<a href="{sonraki}.html" aria-label="Sonraki sayı: {tarih_yaz(sonraki)}"><span class="kisa">{tarih_yaz(sonraki)}</span> →</a>' if sonraki else '<span class="bos">→</span>')
    kartlar = "".join(kart(m, mansetmi=(j == 0)) for j, m in enumerate(ms))
    aciklama = f"Resmî Gazete, {tarih_yaz(t)}: {len(ms)} düzenleme sade Türkçeyle; {dogru} iddia metinden birebir alıntıyla doğrulandı."
    return f"""<!doctype html><html lang="tr"><head>{KAFA}
<title>Gazete Özeti · {tarih_yaz(t)}</title><meta name="description" content="{e(aciklama)}">
<meta property="og:title" content="Gazete Özeti · {tarih_yaz(t)}"><meta property="og:description" content="{e(aciklama)}">
<style>{CSS}</style></head><body><div class="sar">
<header class="kunye"><div class="ust-yazi">Resmî Gazete'nin sade Türkçesi · her sabah</div><h1>Gazete Özeti</h1></header>
<div class="tarih">{gezin[0]}<span>{tarih_yaz(t, True)} · Sayı {e(g['sayi'] or '?')}</span>{gezin[1]}</div>
<div class="sayilar"><span><b>{len(ms)}</b>düzenleme</span><span><b>{genis}</b>geniş kitleyi etkiliyor</span><span><b>{dogru}</b>iddia metinle doğrulandı</span></div>
<nav class="filtre" aria-label="Konuya göre süz">{dugmeler}</nav>
<main class="sayfa">{kartlar}</main>
<section class="nasil"><h3>Bu sayfa nasıl hazırlanıyor?</h3>
<p>Her sabah Resmî Gazete'deki bütün metinler okunur (taranmış PDF'ler dahil) ve her biri yapay zekâyla sade Türkçeye çevrilir. Özetteki her değişiklik, metinden <b>birebir bir alıntıyla</b> eşleştirilir: alıntı metinde geçmiyorsa ya da ayrı bir denetim alıntının iddiayı desteklemediğini söylüyorsa o iddia <b>gösterilmez</b>. Her maddenin yanındaki <span class="dayanak" style="display:inline-block;text-align:center">§</span> düğmesi o alıntıyı açar.</p>
<p>Elle denetimde rastgele seçilen 25 yayımlanmış iddianın 25'i metinle uyumlu çıktı. Yine de bu bir hukuki görüş değildir; karar vermeden önce aslını okuyun.</p></section>
<section class="arsiv"><h3>Önceki sayılar</h3><nav>{''.join(f'<a href="{x}.html"{" class=bu" if x == t else ""}>{tarih_yaz(x)}</a>' for x in arsiv)}</nav></section>
<footer>Kod ve yöntem: <a href="https://github.com/birtohum/gazete-ozeti">github.com/birtohum/gazete-ozeti</a> · <a href="https://birtohum.github.io/">birtohum</a></footer>
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
