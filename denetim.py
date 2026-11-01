"""İnsan denetimi için rastgele örnek: doğrulanmış iddiaları metindeki bölümüyle yan yana basar.

Kullanım: python denetim.py N [tohum]
Elle verilen hükümler kayitlar/denetim.jsonl'e değil, README'deki tabloya yazılır.
"""
import json
import random
import sys

from cek import VERI
import ozet
from ozet import baglam

ozet.BAGLAM = 350

n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
havuz = []
for p in sorted(VERI.glob("*/ozet.json")):
    metin = {m["no"]: m["metin"] for m in json.loads((p.parent / "maddeler.json").read_text(encoding="utf-8"))["maddeler"]}
    for m in json.loads(p.read_text(encoding="utf-8"))["maddeler"]:
        for d in m["ozet"].get("degisiklikler", []):
            if d.get("dogrulandi"):
                havuz.append((p.parent.name, m["no"], d, metin[m["no"]]))
print(f"havuz: {len(havuz)} doğrulanmış iddia\n")
for i, (t, no, d, metin) in enumerate(random.sample(havuz, min(n, len(havuz))), 1):
    print(f"#{i} {t}-{no}\nİDDİA: {d['ne']}\nBÖLÜM: {baglam(d['dayanak'], metin)}\n{'=' * 80}")
