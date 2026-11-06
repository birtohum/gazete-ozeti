#!/usr/bin/env bash
# Günlük güncelleme, AWS sunucusundan (systemd: gazete-ozeti.timer). Resmî Gazete bu sunucudan erişilebiliyor,
# GitHub Actions'tan erişilemiyor. Sunucu kapalı kaldıysa son 14 günün eksik sayıları da tamamlanır.
set -u
cd "$(dirname "$0")/.."
export TZ=Europe/Istanbul PYTHONIOENCODING=utf-8
git pull --ff-only -q || exit 1
for i in $(seq 14 -1 0); do
  g=$(date -d "-$i days" +%Y%m%d)
  if [ "$i" -ne 0 ] && [ -f "veri/$g/ozet.json" ]; then continue; fi
  .venv/bin/python ozet.py "$g" > /dev/null || echo "ozet.py $g: gazete yok ya da hata ($?)"
done
.venv/bin/python sayfa.py || exit 1
git add veri site
if ! git diff --cached --quiet; then
  git commit -q -m "Gazete: $(date +%Y%m%d) (sunucu görevi)"
  git push -q || exit 1
else
  echo "değişiklik yok"
fi
