# Günlük güncelleme, bu bilgisayardan (Windows zamanlanmış görevi "gazete-ozeti gunluk").
# Resmî Gazete sitesi yurt dışından bağlantıyı yanıtlamadığı için çekme ve özet burada yapılır;
# site/ değişirse commit edilip gönderilir, yayin.yml siteyi yeniden yayımlar.
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
Start-Transcript -Append -Path (Join-Path $PSScriptRoot "yerel_guncelle.log") | Out-Null
try {
    git pull --ff-only -q
    $gun = (Get-Date).ToString("yyyyMMdd")
    # Bilgisayar kapalı kaldıysa son 14 günün eksik sayılarını da tamamla (bugün her zaman denenir)
    foreach ($i in 14..0) {
        $g = (Get-Date).AddDays(-$i).ToString("yyyyMMdd")
        if ($i -ne 0 -and (Test-Path (Join-Path $PSScriptRoot "veri\$g\ozet.json"))) { continue }
        .\.venv\Scripts\python.exe ozet.py $g
        if ($LASTEXITCODE -ne 0) { "ozet.py ${g}: gazete yok ya da hata ($LASTEXITCODE)" }
    }
    .\.venv\Scripts\python.exe sayfa.py
    if ($LASTEXITCODE -ne 0) { throw "sayfa.py başarısız ($LASTEXITCODE)" }
    git add veri site
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        git commit -q -m ("Gazete: " + $gun + " (yerel görev)")
        git push -q
        if ($LASTEXITCODE -ne 0) { throw "git push başarısız" }
    } else { "değişiklik yok" }
} catch { "HATA: $_" } finally { Stop-Transcript | Out-Null }
