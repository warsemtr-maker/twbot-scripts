"""
TribalWars Yagma Asistani — Bot Icinde Calisir
Ayrı pencere yok, pyautogui yok.
Bot sidebar'dan baslatilir, tarayiciya JS enjekte eder.

Bu script bot tarafindan subprocess olarak degil,
dogrudan bot context'inde calisir (tip: python_internal).
"""

# Bot context'inden gelenler:
# browser  -> aktif QWebEngineView
# log      -> konsola yaz fonksiyonu
# QTimer   -> zamanlayici
# json     -> json modulu
# durdur   -> scripti durdur

import random

# ── Ayarlar ──────────────────────────────────────────
TIKLA_MIN_MS  = 369
TIKLA_MAX_MS  = 976
YENILE_MIN_S  = 200
YENILE_MAX_S  = 389
TEMPLATE      = "a"   # "a", "b" veya "ab"
MESAFE_MIN    = 0
MESAFE_MAX    = 0     # 0 = sinirsiz

# ─────────────────────────────────────────────────────

YAGMA_JS = """
(function() {
    function log(msg) { console.log('[TW_YAGMA] ' + msg); }

    function sayfaKontrol() {
        return document.querySelector('.farm_icon_a, .farm_icon_b, #am_widget_Farm') !== null;
    }

    function satirMesafeOku(row) {
        var cells = row.querySelectorAll('td');
        for (var i = 0; i < cells.length; i++) {
            var txt = (cells[i].innerText || '').trim();
            if (/^\\d+(\\.\\d+)?$/.test(txt)) return parseFloat(txt);
        }
        return null;
    }

    function askerVarMi(btn) {
        if (!btn || btn.disabled) return false;
        if (btn.classList.contains('disabled')) return false;
        var op = parseFloat(window.getComputedStyle(btn).opacity || '1');
        if (op < 0.6) return false;
        var row = btn.closest('tr');
        if (row) {
            var bg = window.getComputedStyle(row).backgroundColor;
            if (bg && bg.startsWith('rgb(255,') && bg.indexOf('255, 255') === -1) return false;
        }
        return true;
    }

    function gonder(template, minM, maxM) {
        if (!sayfaKontrol()) {
            log('Loot Assistant sayfasi degil!');
            return JSON.stringify({gonderilen:0, askerYok:false});
        }

        var selector = 'input.farm_icon_' + template + ', a.farm_icon_' + template;
        var butonlar = Array.from(document.querySelectorAll(selector));
        var gonderilen = 0, askerYokAdet = 0, mesafeDisi = 0;

        butonlar.forEach(function(btn, idx) {
            var row = btn.closest('tr');
            if (row && (minM > 0 || maxM > 0)) {
                var m = satirMesafeOku(row);
                if (m !== null) {
                    if (minM > 0 && m < minM) { mesafeDisi++; return; }
                    if (maxM > 0 && m > maxM) { mesafeDisi++; return; }
                }
            }
            if (!askerVarMi(btn)) { askerYokAdet++; return; }
            var gecikme = gonderilen * (280 + Math.floor(Math.random() * 350));
            (function(b, g) {
                setTimeout(function() {
                    try { b.click(); log('Saldirildi: ' + (g+1) + '. hedef'); }
                    catch(e) { log('Hata: ' + e.message); }
                }, gecikme);
            })(btn, gonderilen);
            gonderilen++;
        });

        var askerYok = (gonderilen === 0 && askerYokAdet > 0);
        log('Gonderilen: ' + gonderilen + ' | AskerYok: ' + askerYokAdet + ' | MesafeDisi: ' + mesafeDisi);
        return JSON.stringify({gonderilen:gonderilen, askerYok:askerYok});
    }

    function yenilemeSuresi() {
        var els = Array.from(document.querySelectorAll('div,span,td'));
        for (var i = 0; i < els.length; i++) {
            var txt = els[i].innerText || '';
            var m = txt.match(/(\\d+)-(\\d+)\\s*sn/);
            if (m) return {min: parseInt(m[1])*1000, max: parseInt(m[2])*1000};
            var m2 = txt.match(/(\\d+)\\s*sn/);
            if (m2) { var sn = parseInt(m2[1])*1000; return {min:sn, max:sn+30000}; }
        }
        return null;
    }

    window._twYagmaGonder       = gonder;
    window._twYagmaYenileSuresi = yenilemeSuresi;
    window._twYagmaSayfaKontrol = sayfaKontrol;
    log('JS yuklendi');
})();
"""

tur_sayisi    = [0]
toplam        = [0]
yenileme_timer = QTimer()
geri_sayim_timer = QTimer()
_aktif        = [True]

def _durdur():
    _aktif[0] = False
    yenileme_timer.stop()
    geri_sayim_timer.stop()
    log("Yağma botu durduruldu ⏹")

def _js_yukle():
    if not _aktif[0]: return
    browser.page().runJavaScript(YAGMA_JS)
    log("JS yüklendi, 2sn sonra saldırı başlıyor...")
    QTimer.singleShot(2000, _saldiri_gonder)

def _saldiri_gonder():
    if not _aktif[0]: return
    templates = ["a", "b"] if TEMPLATE == "ab" else [TEMPLATE]
    for t in templates:
        gecikme = random.randint(TIKLA_MIN_MS, TIKLA_MAX_MS)
        js = f"window._twYagmaGonder('{t}', {MESAFE_MIN}, {MESAFE_MAX});"
        QTimer.singleShot(gecikme, lambda tt=t: browser.page().runJavaScript(
            f"window._twYagmaGonder('{tt}', {MESAFE_MIN}, {MESAFE_MAX});",
            _saldiri_sonucu
        ))

def _saldiri_sonucu(sonuc):
    if not _aktif[0]: return
    try:
        data = json.loads(sonuc) if isinstance(sonuc, str) else (sonuc or {})
        g = data.get("gonderilen", 0)
        asker_yok = data.get("askerYok", False)
        toplam[0] += g
        tur_sayisi[0] += 1
        log(f"Tur {tur_sayisi[0]}: {g} saldırı gönderildi (toplam: {toplam[0]})")

        if asker_yok:
            log("⚠ Asker yok — bekleniyor...")
            bekleme = YENILE_MIN_S * 1000
        else:
            # Sayfadan yenileme süresi oku
            browser.page().runJavaScript(
                "JSON.stringify(window._twYagmaYenileSuresi());",
                _sonraki_turu_planla
            )
            return

        _bekle_ve_yenile(bekleme)
    except Exception as e:
        log(f"Sonuç parse hatası: {e}")

def _sonraki_turu_planla(sonuc):
    if not _aktif[0]: return
    try:
        sayfa_suresi = json.loads(sonuc) if sonuc and sonuc != "null" else None
        if sayfa_suresi:
            bekleme = random.randint(sayfa_suresi["min"], sayfa_suresi["max"])
        else:
            bekleme = random.randint(YENILE_MIN_S * 1000, YENILE_MAX_S * 1000)
    except Exception:
        bekleme = random.randint(YENILE_MIN_S * 1000, YENILE_MAX_S * 1000)

    log(f"⏳ Sonraki tur: {bekleme // 1000} saniye sonra")
    _bekle_ve_yenile(bekleme)

def _bekle_ve_yenile(ms):
    if not _aktif[0]: return
    yenileme_timer.setSingleShot(True)
    yenileme_timer.timeout.disconnect() if yenileme_timer.receivers(yenileme_timer.timeout) > 0 else None
    yenileme_timer.timeout.connect(_sayfa_yenile)
    yenileme_timer.start(ms)

def _sayfa_yenile():
    if not _aktif[0]: return
    log("🔄 Sayfa yenileniyor...")
    browser.reload()
    QTimer.singleShot(2500, _js_yukle)

# Başlat
log("⚔ Yağma botu başlatılıyor...")
log(f"Template: {TEMPLATE} | Mesafe: {MESAFE_MIN}-{MESAFE_MAX} | Bekleme: {YENILE_MIN_S}-{YENILE_MAX_S}sn")
QTimer.singleShot(500, _js_yukle)
