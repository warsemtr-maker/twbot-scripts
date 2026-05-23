"""
TribalWars Yağma Asistanı — Ekran Tarama Modu
==============================================
Selenium yok, çerez yok, HTML okuma yok.
Sadece ekrandaki A butonlarını renk taramasıyla bulur ve tıklar.
Herhangi bir tarayıcı/program içinde çalışır.

Kurulum:
    pip install pyautogui requests

Kullanım:
    1. Farm asistanı ekranını aç.
    2. python tw_yagma.py
    3. Menüden [1] seç, 5 sn geri sayımda programa geç.
    4. Durdurmak: fareyi sol üst köşeye sür veya Ctrl+C.
"""

import time
import random
import os
import threading
from datetime import datetime

import pyautogui
import requests

pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0.05

# ══════════════════════════════════════════════════════
#  AYARLAR
# ══════════════════════════════════════════════════════

TIKLA_MIN_MS   = 369      # Tıklamalar arası min bekleme (ms)
TIKLA_MAX_MS   = 976      # Tıklamalar arası max bekleme (ms)

YENILE_MIN_S   = 200      # Sayfa yenileme min bekleme (sn)
YENILE_MAX_S   = 389      # Sayfa yenileme max bekleme (sn)

CALISMA_BAS    = "08:00"  # Çalışma başlangıç saati
CALISMA_BIT    = "23:30"  # Çalışma bitiş saati

# A butonu renkleri — birden fazla renk tanımlayabilirsin
# Her biri (R, G, B, tolerans) formatında
# Resimde A butonu: siyah kare içinde beyaz harf
BUTON_RENKLER  = [
    (40,  40,  40,  25),   # Siyah arka plan
    (68,  51,  17,  25),   # Koyu kahve
    (180, 155, 100, 25),   # Krem kenar
    (161, 115, 69,  25),   # Standart TW kahve
]

# Tarama bölgesi — None = tüm ekran
# Sadece farm listesinin bulunduğu alanı daraltmak için:
# (x_başlangıç, y_başlangıç, genişlik, yükseklik)
TARAMA_BOLGESI = None

# Ekran görüntüsü
SCREENSHOTS    = "screenshots"
ONCE_SONRA     = True

# Telegram — bot koruması gelince bildirim
TELEGRAM_TOKEN   = ""   # örn: "7123456789:AAFxxxxxxx"
TELEGRAM_CHAT_ID = ""   # örn: "123456789"

# Bot koruması — ekranda bu metin görünürse dur
BOT_KORUMA_METIN = ["botprotection", "Bot Protection", "Captcha"]

# ══════════════════════════════════════════════════════


def log(metin):
    zaman = datetime.now().strftime("%H:%M:%S")
    print(f"[{zaman}]  {metin}")

def ms_bekle(mn, mx):
    time.sleep(random.randint(mn, mx) / 1000)

def sn_bekle(mn, mx):
    sure = random.randint(mn, mx)
    log(f"⏳  {sure} sn bekleniyor…")
    bitis = time.time() + sure
    while True:
        kalan = int(bitis - time.time())
        if kalan <= 0: break
        print(f"       {kalan} sn kaldı…", end="\r")
        time.sleep(min(10, kalan))
    print()

def geri_sayim(sn=5):
    print(f"\nPencereye geç! {sn} sn sonra başlıyor…")
    for i in range(sn, 0, -1):
        print(f"  {i}…")
        time.sleep(1)
    print("BAŞLADI!\n")

def saat_parse(s):
    h, m = map(int, s.split(":"))
    return h * 60 + m

def calisma_saati_mi():
    simdi = datetime.now()
    dk = simdi.hour * 60 + simdi.minute
    b, e = saat_parse(CALISMA_BAS), saat_parse(CALISMA_BIT)
    if b <= e: return b <= dk <= e
    return dk >= b or dk <= e

def saat_bekle():
    log(f"😴  Çalışma saati dışında. {CALISMA_BAS} bekleniyor…")
    while not calisma_saati_mi():
        print(f"  💤  {datetime.now().strftime('%H:%M:%S')}", end="\r")
        time.sleep(60)
    print()
    log("✅  Çalışma saati! Devam…")

# ─────────────────────────────────────────────────────
#  TELEGRAM
# ─────────────────────────────────────────────────────

def telegram_gonder(mesaj, resim_yolu=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        if resim_yolu and os.path.exists(resim_yolu):
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            with open(resim_yolu, "rb") as f:
                requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": mesaj},
                              files={"photo": f}, timeout=10)
        else:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": mesaj,
                                     "parse_mode": "HTML"}, timeout=10)
        log("📨  Telegram bildirimi gönderildi.")
    except Exception as e:
        log(f"⚠️  Telegram hatası: {e}")

# ─────────────────────────────────────────────────────
#  EKRAN GÖRÜNTÜSÜ
# ─────────────────────────────────────────────────────

def ekran_goruntus_al(tur, etiket):
    os.makedirs(SCREENSHOTS, exist_ok=True)
    zaman = datetime.now().strftime("%H-%M-%S")
    dosya = os.path.join(SCREENSHOTS, f"tur_{tur:03d}_{etiket}_{zaman}.png")
    pyautogui.screenshot(dosya)
    log(f"📸  {dosya}")
    return dosya

# ─────────────────────────────────────────────────────
#  BOT KORUMASI KONTROLÜ (ekran görüntüsünden OCR yerine
#  ekrandaki pikselleri kontrol eder — basit yöntem)
# ─────────────────────────────────────────────────────

def bot_korumasi_var_mi():
    """
    Ekran görüntüsü alır, belirli bir bölgede
    bot koruma rengini arar.
    Captcha genellikle beyaz popup içinde gelir —
    ekranın ortasında parlak beyaz büyük alan varsa şüpheli.
    """
    try:
        ekran = pyautogui.screenshot()
        gw, gh = ekran.size
        # Ekranın ortasındaki 400x300 bölgeyi kontrol et
        merkez_x = gw // 2
        merkez_y = gh // 2
        beyaz_sayisi = 0
        for y in range(merkez_y - 150, merkez_y + 150, 4):
            for x in range(merkez_x - 200, merkez_x + 200, 4):
                r, g, b = ekran.getpixel((x, y))[:3]
                # Parlak beyaz piksel
                if r > 240 and g > 240 and b > 240:
                    beyaz_sayisi += 1
        # Ortada 500'den fazla beyaz piksel varsa captcha şüphesi
        return beyaz_sayisi > 500
    except:
        return False

# ─────────────────────────────────────────────────────
#  A BUTONLARINI BUL
# ─────────────────────────────────────────────────────

def butonlari_bul():
    """
    Tanımlanan tüm renkleri ekranda tarar,
    A buton koordinatlarını döndürür.
    """
    konumlar = []
    try:
        ekran = pyautogui.screenshot(region=TARAMA_BOLGESI)
        ox = TARAMA_BOLGESI[0] if TARAMA_BOLGESI else 0
        oy = TARAMA_BOLGESI[1] if TARAMA_BOLGESI else 0
        gw, gh = ekran.size

        for y in range(0, gh, 3):
            for x in range(0, gw, 3):
                piksel = ekran.getpixel((x, y))[:3]
                r, g, b = piksel

                for hr, hg, hb, tol in BUTON_RENKLER:
                    if abs(r-hr)<=tol and abs(g-hg)<=tol and abs(b-hb)<=tol:
                        gx, gy = x + ox, y + oy
                        # Yakın noktaları filtrele
                        if not any(abs(gx-px)<25 and abs(gy-py)<25 for px,py in konumlar):
                            konumlar.append((gx, gy))
                        break
    except Exception as e:
        log(f"⚠️  Tarama hatası: {e}")
    return konumlar

# ─────────────────────────────────────────────────────
#  SAYFA YENİLE
# ─────────────────────────────────────────────────────

def sayfayi_yenile():
    pyautogui.hotkey("f5")
    log("🔄  F5 — sayfa yenileniyor…")
    time.sleep(3)

# ─────────────────────────────────────────────────────
#  YAĞMA TURU
# ─────────────────────────────────────────────────────

def yagma_turu(tur):
    print(f"\n{'━'*46}")
    log(f"TUR {tur}")
    print(f"{'━'*46}")

    # Tur öncesi ekran görüntüsü
    if ONCE_SONRA:
        ekran_goruntus_al(tur, "once")

    # Bot koruması kontrolü
    if bot_korumasi_var_mi():
        log("🚨  BOT KORUMASI ALGILANDI! Durduruluyor.")
        dosya = ekran_goruntus_al(tur, "bot_koruma")
        mesaj = (
            f"🚨 TribalWars Bot Koruması!\n"
            f"⏰ Saat: {datetime.now().strftime('%H:%M:%S')}\n"
            f"🔄 Tur: {tur}\n\n"
            f"Script durduruldu. Captcha'yı çöz ve tekrar başlat."
        )
        threading.Thread(target=telegram_gonder, args=(mesaj, dosya), daemon=True).start()
        try:
            import winsound
            for _ in range(5):
                winsound.Beep(1000, 400)
                time.sleep(0.2)
        except: pass
        return -1  # dur sinyali

    # A butonlarını bul
    butonlar = butonlari_bul()
    if not butonlar:
        log("⚠️  Ekranda A butonu bulunamadı!")
        log("    → [2] ile rengi oku ve BUTON_RENKLER listesini güncelle.")
        ekran_goruntus_al(tur, "buton_yok")
        return 0

    log(f"🎯  {len(butonlar)} A butonu bulundu.")
    random.shuffle(butonlar)

    tiklanma = 0
    for x, y in butonlar:
        try:
            ms_bekle(TIKLA_MIN_MS, TIKLA_MAX_MS)
            pyautogui.moveTo(x, y, duration=0.15)
            pyautogui.click()
            tiklanma += 1
            log(f"   ✅  ({tiklanma}/{len(butonlar)})  →  ({x}, {y})")
            ms_bekle(TIKLA_MIN_MS, TIKLA_MAX_MS)
        except pyautogui.FailSafeException:
            raise
        except Exception as e:
            log(f"   ⚠️  Tıklama hatası: {e}")

    # Tur sonrası ekran görüntüsü
    ekran_goruntus_al(tur, "sonra")
    log(f"📊  Tur tamamlandı: {tiklanma} tıklama.")
    return tiklanma

# ─────────────────────────────────────────────────────
#  YARDIMCI: RENK OKU
# ─────────────────────────────────────────────────────

def renk_al_helper():
    print("\nFareyi A butonunun üzerine götür — 5 sn sonra renk okunuyor…")
    time.sleep(5)
    x, y = pyautogui.position()
    r, g, b = pyautogui.pixel(x, y)
    print(f"\nKoordinat  : ({x}, {y})")
    print(f"Renk       : ({r}, {g}, {b})")
    print(f"\nBUTON_RENKLER listesine şunu ekle:")
    print(f"    ({r}, {g}, {b}, 25),")

# ─────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  TribalWars Yağma Asistanı  |  Ekran Tarama")
    print("=" * 50)
    print(f"  Tıklama arası  : {TIKLA_MIN_MS}–{TIKLA_MAX_MS} ms")
    print(f"  Yenileme arası : {YENILE_MIN_S}–{YENILE_MAX_S} sn")
    print(f"  Çalışma saati  : {CALISMA_BAS} – {CALISMA_BIT}")
    print(f"  Renk sayısı    : {len(BUTON_RENKLER)} tanımlı")
    print(f"  Telegram       : {'✅ Aktif' if TELEGRAM_TOKEN else '❌ Kapalı'}")
    print()
    print("  [1] Yağmaya başla")
    print("  [2] A butonu rengini oku")
    print()
    secim = input("Seçim: ").strip()

    if secim == "2":
        renk_al_helper()
        return

    geri_sayim(5)

    tur    = 0
    toplam = 0

    try:
        while True:
            if not calisma_saati_mi():
                saat_bekle()
                geri_sayim(5)

            tur += 1

            if tur > 1:
                sayfayi_yenile()

            sonuc = yagma_turu(tur)

            if sonuc == -1:  # Bot koruması
                break

            toplam += sonuc
            log(f"📈  Toplam: {toplam} tıklama ({tur} tur)")
            sn_bekle(YENILE_MIN_S, YENILE_MAX_S)

    except pyautogui.FailSafeException:
        print("\n⛔  Fare köşeye sürüldü — durduruldu.")
    except KeyboardInterrupt:
        print("\n⛔  Ctrl+C ile durduruldu.")
    finally:
        print(f"\n✔️  Toplam {tur} tur, {toplam} tıklama. İyi oyunlar!")

if __name__ == "__main__":
    main()
