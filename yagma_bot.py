import sys
import json
import random
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QTextEdit, QFrame, QFormLayout, QCheckBox, QGroupBox
)
from PyQt5.QtCore import QTimer, QUrl, Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineScript

# ── Renk Paleti ───────────────────────────────────────────────
C = {
    "bg":      "#0d0d0d", "bg2": "#111111", "bg3": "#1a1a1a",
    "bg4":     "#222222", "border": "#2a2a2a", "border2": "#333333",
    "accent":  "#c8a96e", "accent2": "#a07840",
    "green":   "#2ecc71", "green2": "#27ae60",
    "red":     "#e74c3c", "red2":   "#c0392b",
    "blue":    "#4d9fff", "blue2":  "#3a8eee",
    "text":    "#eeeeee", "text2":  "#aaaaaa",
    "text3":   "#777777", "text4":  "#555555",
}

# ── Sunucu Ayarları ───────────────────────────────────────────
SUNUCU       = "enc1.tribalwars.net/game.php"
LOOT_URL     = f"https://{SUNUCU}/game.php?screen=am_farm"

# ── Loot Assistant Otomasyon JS ───────────────────────────────
# Mesafe filtresi, asker kontrolü ve saldırı gönderme
LOOT_JS = """
(function() {
    function log(msg) {
        if (window._yagmaLog) window._yagmaLog(msg);
        console.log('[YagmaBot]', msg);
    }

    // Loot Assistant sayfası mı?
    function sayfaKontrol() {
        return (
            document.querySelector('#am_widget_Farm') !== null ||
            document.querySelector('.farm_icon') !== null ||
            document.querySelector('table.vis') !== null
        );
    }

    // Bir satırdaki mesafeyi oku (fields sütunu)
    // Loot Assistant tablosunda her satır: köy adı | mesafe | A | B
    function satirMesafeOku(row) {
        // "fields" sütunu genellikle 3. veya 4. td içinde "X.XX" formatında
        const cells = row.querySelectorAll('td');
        for (const cell of cells) {
            const txt = (cell.innerText || '').trim();
            // Sadece sayısal mesafe değeri: "7.1" veya "12.45"
            if (/^\\d+(\\.\\d+)?$/.test(txt)) {
                return parseFloat(txt);
            }
        }
        return null;
    }

    // Satırdaki asker durumunu kontrol et
    // Buton kırmızıysa veya disabled ise asker yok demektir
    function satirAskerVarMi(btn) {
        if (!btn) return false;
        if (btn.disabled) return false;
        if (btn.classList.contains('disabled')) return false;
        // Bazı versiyonlarda buton rengi kırmızı olur (asker yok)
        const style = window.getComputedStyle(btn);
        // opacity 0.4 veya benzeri → devre dışı
        const opacity = parseFloat(style.opacity || '1');
        if (opacity < 0.6) return false;
        // parent satırın arka plan rengi kırmızıysa asker yok
        const row = btn.closest('tr');
        if (row) {
            const bg = window.getComputedStyle(row).backgroundColor;
            // rgb(255, x, x) → kırmızı uyarı
            if (bg && bg.startsWith('rgb(255,') && !bg.includes('255, 255')) return false;
        }
        return true;
    }

    // Ana fonksiyon
    // template: 'a' | 'b'
    // minMesafe, maxMesafe: field sınırları
    // maxSaldiri: 0 = sınırsız
    function calistir(template, minMesafe, maxMesafe, maxSaldiri) {
        if (!sayfaKontrol()) {
            log('Loot Assistant sayfası değil!');
            return JSON.stringify({ durum: 'sayfa_yok', gonderilen: 0, askerYok: false });
        }

        const selector = 'input.farm_icon_' + template + ', a.farm_icon_' + template;
        const tumButonlar = Array.from(document.querySelectorAll(selector));

        if (tumButonlar.length === 0) {
            log('Hiç buton bulunamadı (Template ' + template.toUpperCase() + ')');
            return JSON.stringify({ durum: 'buton_yok', gonderilen: 0, askerYok: false });
        }

        let gonderilen  = 0;
        let atlandi     = 0;
        let askerYokAdet = 0;
        let mesafeDisi  = 0;

        tumButonlar.forEach(function(btn, idx) {
            if (maxSaldiri > 0 && gonderilen >= maxSaldiri) return;

            const row = btn.closest('tr');

            // ── Mesafe Filtresi ──────────────────────────────
            if (row && (minMesafe > 0 || maxMesafe > 0)) {
                const mesafe = satirMesafeOku(row);
                if (mesafe !== null) {
                    if (minMesafe > 0 && mesafe < minMesafe) {
                        mesafeDisi++;
                        return; // bu köyü atla
                    }
                    if (maxMesafe > 0 && mesafe > maxMesafe) {
                        mesafeDisi++;
                        return; // bu köyü atla
                    }
                }
            }

            // ── Asker Kontrolü ───────────────────────────────
            if (!satirAskerVarMi(btn)) {
                askerYokAdet++;
                log('⚠ Asker yok — köy atlandı (' + (idx + 1) + ')');
                atlandi++;
                return;
            }

            // ── Saldırı Gönder ───────────────────────────────
            const gecikmems = gonderilen * (280 + Math.floor(Math.random() * 350));
            (function(b, i, g) {
                setTimeout(function() {
                    try {
                        b.click();
                        log('✅ Saldırı ' + (g + 1) + ': Template ' + template.toUpperCase());
                    } catch(e) {
                        log('Hata: ' + e.message);
                    }
                }, gecikmems);
            })(btn, idx, gonderilen);

            gonderilen++;
        });

        // Asker tamamen bitti mi? (gönderilen 0, atlanmış = asker yok sayısı > 0)
        const askerYok = (gonderilen === 0 && askerYokAdet > 0);

        log('Gönderilen: ' + gonderilen +
            ' | Atlanan (asker yok): ' + askerYokAdet +
            ' | Mesafe dışı: ' + mesafeDisi);

        return JSON.stringify({
            durum:       askerYok ? 'asker_yok' : 'ok',
            gonderilen:  gonderilen,
            atlandi:     atlandi,
            mesafeDisي:  mesafeDisi,
            askerYok:    askerYok
        });
    }

    // Yenileme süresi oku
    function yenilemeSuresiOku() {
        const divler = Array.from(document.querySelectorAll('div, span, td'));
        for (const el of divler) {
            const txt = el.innerText || '';
            const m = txt.match(/(\\d+)-(\\d+)\\s*sn/);
            if (m) return { min: parseInt(m[1]) * 1000, max: parseInt(m[2]) * 1000 };
            const m2 = txt.match(/(\\d+)\\s*sn/);
            if (m2) {
                const sn = parseInt(m2[1]) * 1000;
                return { min: sn, max: sn + 30000 };
            }
        }
        return null;
    }

    window._yagmaCalistir       = calistir;
    window._yagmaYenilemeSuresi = yenilemeSuresiOku;
    window._yagmaSayfaKontrol   = sayfaKontrol;

    log('Yağma Bot JS yüklendi ✅');
})();
"""


# ── Web Sayfası ───────────────────────────────────────────────
class YagmaPage(QWebEnginePage):
    konsol_sinyali = pyqtSignal(str)

    def certificateError(self, error):
        error.ignoreCertificateError()
        return True

    def javaScriptConsoleMessage(self, level, message, line, source):
        if "[YagmaBot]" in message:
            self.konsol_sinyali.emit(message.replace("[YagmaBot]", "").strip())


# ── Ana Pencere ───────────────────────────────────────────────
class YagmaBot(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TribalWars — Yağma Botu")
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(f"background:{C['bg']};")

        self.calisiyor       = False
        self.toplam_saldiri  = 0
        self.tur_sayisi      = 0
        self._bekleyen_sonuc = 0
        self._tur_asker_yok  = False
        self.yenileme_timer  = QTimer()
        self.yenileme_timer.timeout.connect(self._tur_baslat)

        self._build()

    # ── Arayüz ────────────────────────────────────────────────
    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sol panel
        sol = QFrame()
        sol.setFixedWidth(280)
        sol.setStyleSheet(f"background:{C['bg2']}; border-right:1px solid {C['border']};")
        sol_layout = QVBoxLayout(sol)
        sol_layout.setContentsMargins(16, 16, 16, 16)
        sol_layout.setSpacing(12)

        # Başlık
        baslik = QLabel("⚔ YAĞMA BOTU")
        baslik.setStyleSheet(f"color:{C['accent']}; font-size:16px; font-weight:bold; letter-spacing:1px;")
        sol_layout.addWidget(baslik)

        alt_baslik = QLabel(f"Sunucu: {SUNUCU}")
        alt_baslik.setStyleSheet(f"color:{C['text3']}; font-size:11px;")
        sol_layout.addWidget(alt_baslik)

        self._ayrac(sol_layout)

        # Ayarlar grubu
        ayarlar = QGroupBox("Ayarlar")
        ayarlar.setStyleSheet(f"""
            QGroupBox {{
                color:{C['text2']}; font-size:12px; font-weight:bold;
                border:1px solid {C['border2']}; border-radius:6px;
                margin-top:8px; padding-top:8px;
            }}
            QGroupBox::title {{ subcontrol-origin:margin; left:10px; padding:0 4px; }}
        """)
        ayarlar_layout = QFormLayout(ayarlar)
        ayarlar_layout.setSpacing(8)

        # Template seçimi
        self.template_sec = QComboBox()
        self.template_sec.addItems(["Template A", "Template B", "Önce A, sonra B"])
        self.template_sec.setStyleSheet(self._combo_style())
        ayarlar_layout.addRow(self._lbl("Template:"), self.template_sec)

        # Max saldırı
        self.max_saldiri = QSpinBox()
        self.max_saldiri.setRange(0, 500)
        self.max_saldiri.setValue(0)
        self.max_saldiri.setSpecialValueText("Sınırsız")
        self.max_saldiri.setStyleSheet(self._spin_style())
        ayarlar_layout.addRow(self._lbl("Max saldırı:"), self.max_saldiri)

        # Mesafe aralığı
        self.mesafe_min = QDoubleSpinBox()
        self.mesafe_min.setRange(0, 200)
        self.mesafe_min.setValue(0)
        self.mesafe_min.setSuffix(" field")
        self.mesafe_min.setDecimals(1)
        self.mesafe_min.setSpecialValueText("Yok")
        self.mesafe_min.setStyleSheet(self._spin_style())
        ayarlar_layout.addRow(self._lbl("Min mesafe:"), self.mesafe_min)

        self.mesafe_max = QDoubleSpinBox()
        self.mesafe_max.setRange(0, 200)
        self.mesafe_max.setValue(0)
        self.mesafe_max.setSuffix(" field")
        self.mesafe_max.setDecimals(1)
        self.mesafe_max.setSpecialValueText("Sınırsız")
        self.mesafe_max.setStyleSheet(self._spin_style())
        ayarlar_layout.addRow(self._lbl("Max mesafe:"), self.mesafe_max)

        # Bekleme süresi
        self.bekleme_min = QSpinBox()
        self.bekleme_min.setRange(60, 3600)
        self.bekleme_min.setValue(250)
        self.bekleme_min.setSuffix(" sn")
        self.bekleme_min.setStyleSheet(self._spin_style())
        ayarlar_layout.addRow(self._lbl("Bekleme min:"), self.bekleme_min)

        self.bekleme_max = QSpinBox()
        self.bekleme_max.setRange(60, 3600)
        self.bekleme_max.setValue(310)
        self.bekleme_max.setSuffix(" sn")
        self.bekleme_max.setStyleSheet(self._spin_style())
        ayarlar_layout.addRow(self._lbl("Bekleme max:"), self.bekleme_max)

        # Otomatik yenileme
        self.oto_yenile = QCheckBox("Sayfadan süreyi oku")
        self.oto_yenile.setChecked(True)
        self.oto_yenile.setStyleSheet(f"color:{C['text2']}; font-size:12px;")
        ayarlar_layout.addRow("", self.oto_yenile)

        sol_layout.addWidget(ayarlar)
        self._ayrac(sol_layout)

        # Durum kutusu
        durum_frame = QFrame()
        durum_frame.setStyleSheet(f"background:{C['bg3']}; border-radius:8px; border:1px solid {C['border']};")
        durum_layout = QFormLayout(durum_frame)
        durum_layout.setContentsMargins(12, 12, 12, 12)
        durum_layout.setSpacing(8)

        self.lbl_durum = QLabel("⏸ Bekliyor")
        self.lbl_durum.setStyleSheet(f"color:{C['text3']}; font-weight:bold;")
        durum_layout.addRow(self._lbl("Durum:"), self.lbl_durum)

        self.lbl_tur = QLabel("0")
        self.lbl_tur.setStyleSheet(f"color:{C['text']};")
        durum_layout.addRow(self._lbl("Tur:"), self.lbl_tur)

        self.lbl_toplam = QLabel("0")
        self.lbl_toplam.setStyleSheet(f"color:{C['text']};")
        durum_layout.addRow(self._lbl("Toplam saldırı:"), self.lbl_toplam)

        self.lbl_sonraki = QLabel("—")
        self.lbl_sonraki.setStyleSheet(f"color:{C['accent']};")
        durum_layout.addRow(self._lbl("Sonraki tur:"), self.lbl_sonraki)

        sol_layout.addWidget(durum_frame)
        self._ayrac(sol_layout)

        # Başlat / Durdur
        self.btn_baslat = QPushButton("▶  BAŞLAT")
        self.btn_baslat.setFixedHeight(46)
        self.btn_baslat.setCursor(Qt.PointingHandCursor)
        self._btn_baslat_style()
        self.btn_baslat.clicked.connect(self._toggle)
        sol_layout.addWidget(self.btn_baslat)

        # Şimdi saldır (manuel)
        btn_simdi = QPushButton("⚡ Şimdi Saldır")
        btn_simdi.setFixedHeight(36)
        btn_simdi.setCursor(Qt.PointingHandCursor)
        btn_simdi.setStyleSheet(
            f"QPushButton{{background:{C['bg4']};color:{C['text2']};"
            f"font-size:12px;border-radius:6px;border:1px solid {C['border2']};}}"
            f"QPushButton:hover{{background:{C['border2']};color:{C['text']};}}"
        )
        btn_simdi.clicked.connect(self._tur_baslat)
        sol_layout.addWidget(btn_simdi)

        sol_layout.addStretch()

        # Konsol
        konsol_lbl = QLabel("KONSOL")
        konsol_lbl.setStyleSheet(f"color:{C['text4']}; font-size:10px; letter-spacing:1px;")
        sol_layout.addWidget(konsol_lbl)

        self.konsol = QTextEdit()
        self.konsol.setReadOnly(True)
        self.konsol.setFixedHeight(160)
        self.konsol.setStyleSheet(
            f"QTextEdit{{background:{C['bg']};color:{C['green']};"
            f"border:1px solid {C['border']};border-radius:4px;"
            f"font-family:Consolas,monospace;font-size:11px;padding:6px;}}"
        )
        sol_layout.addWidget(self.konsol)

        root.addWidget(sol)

        # Sağ — tarayıcı
        sag = QVBoxLayout()
        sag.setContentsMargins(0, 0, 0, 0)
        sag.setSpacing(0)

        # URL bar
        url_bar_frame = QFrame()
        url_bar_frame.setFixedHeight(38)
        url_bar_frame.setStyleSheet(f"background:{C['bg2']}; border-bottom:1px solid {C['border']};")
        url_layout = QHBoxLayout(url_bar_frame)
        url_layout.setContentsMargins(8, 4, 8, 4)
        url_layout.setSpacing(6)

        self.url_bar = QLineEdit(LOOT_URL)
        self.url_bar.setStyleSheet(
            f"QLineEdit{{background:{C['bg3']};color:{C['text']};"
            f"border:1px solid {C['border2']};border-radius:5px;"
            f"padding:0 10px;font-size:12px;}}"
            f"QLineEdit:focus{{border:1px solid {C['accent']};}}"
        )
        self.url_bar.returnPressed.connect(self._navigate)
        url_layout.addWidget(self.url_bar)

        btn_git = QPushButton("Git")
        btn_git.setFixedSize(50, 28)
        btn_git.setStyleSheet(
            f"QPushButton{{background:{C['blue']};color:white;"
            f"border-radius:5px;border:none;font-size:11px;}}"
            f"QPushButton:hover{{background:{C['blue2']};}}"
        )
        btn_git.clicked.connect(self._navigate)
        url_layout.addWidget(btn_git)

        btn_la = QPushButton("🎯 Loot Assistant")
        btn_la.setFixedHeight(28)
        btn_la.setStyleSheet(
            f"QPushButton{{background:{C['accent2']};color:#000;"
            f"border-radius:5px;border:none;padding:0 10px;font-size:11px;font-weight:bold;}}"
            f"QPushButton:hover{{background:{C['accent']};}}"
        )
        btn_la.clicked.connect(lambda: self.browser.setUrl(QUrl(LOOT_URL)))
        url_layout.addWidget(btn_la)

        sag.addWidget(url_bar_frame)

        # Tarayıcı
        self.browser = QWebEngineView()
        self.page    = YagmaPage(self.browser)
        self.page.konsol_sinyali.connect(self._konsol_ekle)
        self.browser.setPage(self.page)
        self.browser.loadFinished.connect(self._sayfa_yuklendi)
        self.browser.setUrl(QUrl(LOOT_URL))
        sag.addWidget(self.browser, stretch=1)

        sag_widget = QWidget()
        sag_widget.setLayout(sag)
        root.addWidget(sag_widget, stretch=1)

        # Geri sayım timer
        self.geri_sayim_timer = QTimer()
        self.geri_sayim_timer.setInterval(1000)
        self.geri_sayim_timer.timeout.connect(self._geri_sayim_guncelle)
        self._kalan_sn = 0

    # ── Sayfa Yüklendi ────────────────────────────────────────
    def _sayfa_yuklendi(self, ok):
        if not ok:
            return
        # Yağma JS'ini her yüklemede enjekte et
        self.browser.page().runJavaScript(LOOT_JS)

        if self.calisiyor:
            # Çalışıyorsa sayfa yenilendi → saldırı gönder
            QTimer.singleShot(1500, self._saldiri_gonder)

    # ── Başlat / Durdur ───────────────────────────────────────
    def _toggle(self):
        if not self.calisiyor:
            self.calisiyor = True
            self._btn_durdur_style()
            self.btn_baslat.setText("⏹  DURDUR")
            self.lbl_durum.setText("✅ Çalışıyor")
            self.lbl_durum.setStyleSheet(f"color:{C['green']}; font-weight:bold;")
            self._konsol_ekle("Bot başlatıldı ✅")
            self._tur_baslat()
        else:
            self._durdur()

    def _durdur(self):
        self.calisiyor = False
        self.yenileme_timer.stop()
        self.geri_sayim_timer.stop()
        self.btn_baslat.setText("▶  BAŞLAT")
        self._btn_baslat_style()
        self.lbl_durum.setText("⏸ Durduruldu")
        self.lbl_durum.setStyleSheet(f"color:{C['red']}; font-weight:bold;")
        self.lbl_sonraki.setText("—")
        self._konsol_ekle("Bot durduruldu ⏹")

    # ── Tur Başlat ────────────────────────────────────────────
    def _tur_baslat(self):
        if not self.calisiyor:
            return
        self.yenileme_timer.stop()
        self.geri_sayim_timer.stop()
        self.tur_sayisi += 1
        self.lbl_tur.setText(str(self.tur_sayisi))
        self._konsol_ekle(f"── Tur {self.tur_sayisi} başladı ──")

        # Sayfayı yenile → _sayfa_yuklendi tetiklenince saldırı gönderilir
        self.browser.reload()

    # ── Saldırı Gönder ────────────────────────────────────────
    def _saldiri_gonder(self):
        if not self.calisiyor:
            return

        template_idx = self.template_sec.currentIndex()
        max_s        = self.max_saldiri.value()
        min_m        = self.mesafe_min.value()
        max_m        = self.mesafe_max.value()

        if template_idx == 0:
            templates = ["a"]
        elif template_idx == 1:
            templates = ["b"]
        else:
            templates = ["a", "b"]

        self._bekleyen_sonuc = len(templates)
        self._tur_asker_yok  = False

        for t in templates:
            js = f"window._yagmaCalistir('{t}', {min_m}, {max_m}, {max_s});"
            self.browser.page().runJavaScript(js, self._saldiri_sonucu)

    def _saldiri_sonucu(self, sonuc):
        if not sonuc:
            self._konsol_ekle("Sonuc alinamadi")
            self._bekleyen_sonuc = max(0, self._bekleyen_sonuc - 1)
            self._tur_tamamla()
            return
        try:
            data        = json.loads(sonuc) if isinstance(sonuc, str) else sonuc
            durum       = data.get("durum", "ok")
            gonderilen  = data.get("gonderilen", 0)
            asker_yok   = data.get("askerYok", False)
            mesafe_disi = data.get("mesafeDisi", 0)

            self.toplam_saldiri += gonderilen
            self.lbl_toplam.setText(str(self.toplam_saldiri))

            if gonderilen > 0:
                self._konsol_ekle(f"Gonderilen: {gonderilen} (toplam: {self.toplam_saldiri})")
            if mesafe_disi > 0:
                self._konsol_ekle(f"Mesafe filtresi: {mesafe_disi} koy atlandi")
            if asker_yok:
                self._tur_asker_yok = True
                self._konsol_ekle("Asker bitti, bekleme moduna geciliyor")
            if durum == "buton_yok":
                self._konsol_ekle("Hic saldiri butonu bulunamadi")
        except Exception as ex:
            self._konsol_ekle(f"Parse hatasi: {ex}")
        finally:
            self._bekleyen_sonuc = max(0, self._bekleyen_sonuc - 1)
            self._tur_tamamla()

    def _tur_tamamla(self):
        if self._bekleyen_sonuc > 0:
            return
        if self._tur_asker_yok:
            bekleme_ms = self.bekleme_min.value() * 1000
            self._konsol_ekle(f"Asker bekleniyor, {bekleme_ms // 1000}sn sonra tekrar denenecek")
            self.lbl_durum.setText("Asker bekleniyor")
            self.lbl_durum.setStyleSheet(f"color:{C['accent']}; font-weight:bold;")
            self._kalan_sn = bekleme_ms // 1000
            self._geri_sayim_guncelle()
            self.geri_sayim_timer.start()
            self.yenileme_timer.setSingleShot(True)
            self.yenileme_timer.start(bekleme_ms)
        else:
            self.lbl_durum.setText("Calisiyor")
            self.lbl_durum.setStyleSheet(f"color:{C['green']}; font-weight:bold;")
            QTimer.singleShot(2000, self._sonraki_turu_planla)


    # ── Sonraki Turu Planla ───────────────────────────────────
    def _sonraki_turu_planla(self):
        if not self.calisiyor:
            return

        def _sure_belirle(sayfa_suresi):
            if self.oto_yenile.isChecked() and sayfa_suresi:
                # Sayfadan okunan süreyi kullan + biraz random
                min_ms = sayfa_suresi.get("min", self.bekleme_min.value() * 1000)
                max_ms = sayfa_suresi.get("max", self.bekleme_max.value() * 1000)
            else:
                min_ms = self.bekleme_min.value() * 1000
                max_ms = self.bekleme_max.value() * 1000

            bekleme_ms = random.randint(min_ms, max_ms)
            self._konsol_ekle(f"⏳ Sonraki tur: {bekleme_ms // 1000} saniye sonra")
            self._kalan_sn = bekleme_ms // 1000
            self._geri_sayim_guncelle()
            self.geri_sayim_timer.start()
            self.yenileme_timer.setSingleShot(True)
            self.yenileme_timer.start(bekleme_ms)

        if self.oto_yenile.isChecked():
            self.browser.page().runJavaScript(
                "JSON.stringify(window._yagmaYenilemeSuresi())",
                lambda r: _sure_belirle(json.loads(r) if r and r != "null" else None)
            )
        else:
            _sure_belirle(None)

    # ── Geri Sayım ───────────────────────────────────────────
    def _geri_sayim_guncelle(self):
        if self._kalan_sn > 0:
            self._kalan_sn -= 1
            dk  = self._kalan_sn // 60
            sn  = self._kalan_sn % 60
            self.lbl_sonraki.setText(f"{dk:02d}:{sn:02d}")
        else:
            self.geri_sayim_timer.stop()
            self.lbl_sonraki.setText("Başlıyor...")

    # ── URL Navigasyon ────────────────────────────────────────
    def _navigate(self):
        url = self.url_bar.text().strip()
        if not url.startswith("http"):
            url = "https://" + url
        self.browser.setUrl(QUrl(url))

    # ── Konsol ───────────────────────────────────────────────
    def _konsol_ekle(self, mesaj):
        self.konsol.append(f"<span style='color:{C['text3']};'>›</span> {mesaj}")
        self.konsol.verticalScrollBar().setValue(
            self.konsol.verticalScrollBar().maximum()
        )

    # ── Stiller ──────────────────────────────────────────────
    def _lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color:{C['text4']}; font-size:11px;")
        return l

    def _ayrac(self, layout):
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color:{C['border']};")
        layout.addWidget(sep)

    def _combo_style(self):
        return (
            f"QComboBox{{background:{C['bg3']};color:{C['text']};"
            f"border:1px solid {C['border2']};border-radius:5px;"
            f"padding:0 8px;height:28px;}}"
            f"QComboBox::drop-down{{border:none;}}"
            f"QComboBox QAbstractItemView{{background:{C['bg3']};color:{C['text']};"
            f"selection-background-color:{C['bg4']};}}"
        )

    def _spin_style(self):
        return (
            f"QSpinBox{{background:{C['bg3']};color:{C['text']};"
            f"border:1px solid {C['border2']};border-radius:5px;"
            f"padding:0 8px;height:28px;}}"
            f"QSpinBox::up-button,QSpinBox::down-button{{width:16px;"
            f"background:{C['bg4']};border:none;}}"
        )

    def _btn_baslat_style(self):
        self.btn_baslat.setStyleSheet(
            f"QPushButton{{background:{C['green']};color:#000;"
            f"font-weight:bold;font-size:14px;border-radius:6px;border:none;}}"
            f"QPushButton:hover{{background:{C['green2']};}}"
        )

    def _btn_durdur_style(self):
        self.btn_baslat.setStyleSheet(
            f"QPushButton{{background:{C['red']};color:white;"
            f"font-weight:bold;font-size:14px;border-radius:6px;border:none;}}"
            f"QPushButton:hover{{background:{C['red2']};}}"
        )


# ── Giriş ─────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pencere = YagmaBot()
    pencere.show()
    sys.exit(app.exec_())
