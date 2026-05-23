"""
TribalWars Yağma Asistanı — Saf Python (Terminal)
==================================================
Kurulum:
    pip install pyautogui requests beautifulsoup4 browser-cookie3

Kullanım:
    1. Chrome'da TribalWars farm asistanı ekranını aç, giriş yap.
    2. python tw_yagma.py
    3. 5 saniyelik geri sayımda tarayıcıya geç.
    4. Durdurmak: fareyi sol üst köşeye sür (Failsafe) veya Ctrl+C.
"""

import time
import random
import os
import re
import threading
from datetime import datetime

import requests
import pyautogui
from bs4 import BeautifulSoup

try:
    import browser_cookie3
    COOKIE_DESTEGI = True
except ImportError:
    COOKIE_DESTEGI = False
    print("⚠️  browser_cookie3 bulunamadı → pip install browser-cookie3")

pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0.05

# ══════════════════════════════════════════════════════
#  AYARLAR  —  Buraya kendi bilgilerini gir
# ══════════════════════════════════════════════════════

SUNUCU_URL     = "https://tr1.tribalwars.com.tr"

TIKLA_MIN_MS   = 369      # Tıklamalar arası min bekleme (ms)
TIKLA_MAX_MS   = 976      # Tıklamalar arası max bekleme (ms)

YENILE_MIN_S   = 200      # Sayfa yenileme min bekleme (sn)
YENILE_MAX_S   = 389      # Sayfa yenileme max bekleme (sn)

MAX_MESAFE     = 20.0     # Bu mesafeden uzak köyleri atla (None = kapalı)
MAX_DUVAR      = 4        # Bu duvar seviyesinden yüksek köyleri atla (None = kapalı)

# Birlik filtresi — format: "birlik:minimum,birlik:minimum"
# Seçili birliklerden herhangi biri minimumun altındaysa köyü atla (VE mantığı)
# spear=Mızrakçı  sword=Kılıçlı  axe=Baltacı  archer=Okçu
# spy=Casus  light=H.Süvari  heavy=A.Süvari  ram=Koçbaşı  catapult=Katapult
# Devre dışı için: ""
BIRLIK_FILTRE  = "spear:50,sword:30,spy:3"

CALISMA_BAS    = "08:00"  # Çalışma başlangıç saati (HH:MM)
CALISMA_BIT    = "23:30"  # Çalışma bitiş saati (HH:MM)

BUTON_RENK     = (161, 115, 69)   # A butonunun rengi (R, G, B)
RENK_TOLERANS  = 30               # Renk toleransı

SCREENSHOTS    = "screenshots"    # Ekran görüntüsü klasörü
ONCE_SONRA     = True             # Tur öncesi ve sonrası ekran görüntüsü al

TELEGRAM_TOKEN   = ""   # BotFather token — örn: "7123456789:AAFxxxxxxx"
TELEGRAM_CHAT_ID = ""   # Chat ID      — örn: "123456789"

# ══════════════════════════════════════════════════════


# ─────────────────────────────────────────────────────
#  YARDIMCI
# ─────────────────────────────────────────────────────

def log(metin, sembol=""):
    zaman = datetime.now().strftime("%H:%M:%S")
    print(f"[{zaman}] {sembol}  {metin}" if sembol else f"[{zaman}] {metin}")

def ms_bekle(mn, mx):
    time.sleep(random.randint(mn, mx) / 1000)

def sn_bekle(mn, mx):
    sure = random.randint(mn, mx)
    log(f"⏳  {sure} saniye bekleniyor…")
    bitis = time.time() + sure
    while True:
        kalan = int(bitis - time.time())
        if kalan <= 0: break
        print(f"       {kalan} sn kaldı…", end="\r")
        time.sleep(min(10, kalan))
    print()

def geri_sayim(sn=5):
    print(f"\nTarayıcıya geç! {sn} saniye sonra başlıyor…")
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
        print(f"  💤  {datetime.now().strftime('%H:%M:%S')} bekleniyor…", end="\r")
        time.sleep(60)
    print()
    log("✅  Çalışma saati geldi, devam ediliyor…")

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
                requests.post(url, data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "caption": mesaj
                }, files={"photo": f}, timeout=10)
        else:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": mesaj,
                "parse_mode": "HTML"
            }, timeout=10)
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
#  CHROME ÇEREZLERİ
# ─────────────────────────────────────────────────────

def cerezleri_al():
    if not COOKIE_DESTEGI:
        return None
    try:
        domain = SUNUCU_URL.replace("https://","").replace("http://","")
        cj = browser_cookie3.chrome(domain_name=domain)
        log("🍪  Chrome çerezleri alındı.")
        return cj
    except Exception as e:
        log(f"⚠️  Çerez alınamadı: {e}")
        return None

# ─────────────────────────────────────────────────────
#  HTML ÇEKME & PARSE
# ─────────────────────────────────────────────────────

def html_cek(cerez_jar):
    farm_url = f"{SUNUCU_URL}/game.php?village=0&screen=am_farm"
    headers  = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9",
    }
    try:
        r = requests.get(farm_url, cookies=cerez_jar, headers=headers, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log(f"⚠️  HTML çekme hatası: {e}")
        return None

def koyleri_parse_et(html):
    soup   = BeautifulSoup(html, "html.parser")
    koyler = []
    tablo  = soup.find("table", id="plunder_list")
    if not tablo:
        tablo = soup.find("table", {"class": re.compile(r"vis")})
    if not tablo:
        log("⚠️  Farm tablosu bulunamadı. SUNUCU_URL doğru mu?")
        return []

    for satir in tablo.find_all("tr")[1:]:
        hucreler = satir.find_all("td")
        if len(hucreler) < 3: continue

        koy = {"mesafe": None, "duvar": None, "birlikler": {},
               "atla": False, "atla_neden": ""}

        for h in hucreler:
            cls = " ".join(h.get("class", []))
            if "dist" in cls or "distance" in cls:
                try: koy["mesafe"] = float(h.get_text(strip=True).replace(",","."))
                except: pass
            if "wall" in cls or "building_wall" in cls:
                try: koy["duvar"] = int(re.search(r"\d+", h.get_text()).group())
                except: koy["duvar"] = 0
            m = re.match(r"units_(\w+)", cls)
            if m:
                try: koy["birlikler"][m.group(1)] = int(re.search(r"\d+", h.get_text() or "0").group())
                except: koy["birlikler"][m.group(1)] = 0

        # ── Filtreler ──
        if MAX_MESAFE and koy["mesafe"] and koy["mesafe"] > MAX_MESAFE:
            koy["atla"] = True
            koy["atla_neden"] = f"mesafe {koy['mesafe']} > {MAX_MESAFE}"

        if not koy["atla"] and MAX_DUVAR is not None and koy["duvar"] is not None:
            if koy["duvar"] > MAX_DUVAR:
                koy["atla"] = True
                koy["atla_neden"] = f"duvar {koy['duvar']} > {MAX_DUVAR}"

        if not koy["atla"] and BIRLIK_FILTRE:
            for parca in BIRLIK_FILTRE.split(","):
                parca = parca.strip()
                if not parca: continue
                if ":" in parca:
                    b, min_s = parca.split(":", 1)
                    b = b.strip()
                    try: minimum = int(min_s.strip())
                    except: minimum = 1
                else:
                    b, minimum = parca.strip(), 1
                mevcut = koy["birlikler"].get(b, None)
                if mevcut is not None and mevcut < minimum:
                    koy["atla"] = True
                    koy["atla_neden"] = f"{b}={mevcut} < {minimum}"
                    break

        koyler.append(koy)
    return koyler

# ─────────────────────────────────────────────────────
#  EKRAN TARAMA & TIKLAMA
# ─────────────────────────────────────────────────────

def butonlari_bul():
    konumlar = []
    try:
        ekran = pyautogui.screenshot()
        gw, gh = ekran.size
        hr, hg, hb = BUTON_RENK
        for y in range(0, gh, 4):
            for x in range(0, gw, 4):
                r, g, b = ekran.getpixel((x, y))[:3]
                if abs(r-hr)<=RENK_TOLERANS and abs(g-hg)<=RENK_TOLERANS and abs(b-hb)<=RENK_TOLERANS:
                    if not any(abs(x-px)<20 and abs(y-py)<20 for px,py in konumlar):
                        konumlar.append((x, y))
    except Exception as e:
        log(f"⚠️  Tarama hatası: {e}")
    return konumlar

def sayfayi_yenile():
    pyautogui.hotkey("f5")
    log("🔄  F5 — sayfa yenilendi.")
    time.sleep(3)

# ─────────────────────────────────────────────────────
#  YAĞMA TURU
# ─────────────────────────────────────────────────────

def yagma_turu(tur, cerez_jar):
    print(f"\n{'━'*48}")
    log(f"TUR {tur}")
    print(f"{'━'*48}")

    if ONCE_SONRA:
        ekran_goruntus_al(tur, "once")

    # HTML çek
    log("🌐  Sayfa verisi okunuyor…")
    html = html_cek(cerez_jar)
    if not html:
        log("❌  HTML alınamadı, tur atlanıyor.")
        return 0

    # Bot koruması kontrolü
    if "botprotection_quest" in html:
        log("🚨  BOT KORUMASI ALGILANDI! Script durduruluyor.")
        dosya = ekran_goruntus_al(tur, "bot_koruma")
        mesaj = (
            f"🚨 TribalWars Bot Koruması!\n"
            f"⏰ Saat: {datetime.now().strftime('%H:%M:%S')}\n"
            f"🔄 Tur: {tur}\n"
            f"🌐 Sunucu: {SUNUCU_URL}\n\n"
            f"Script durduruldu. Captcha'yı çöz ve tekrar başlat."
        )
        threading.Thread(target=telegram_gonder, args=(mesaj, dosya), daemon=True).start()
        try:
            import winsound
            for _ in range(5):
                winsound.Beep(1000, 400)
                time.sleep(0.2)
        except: pass
        return -1  # -1 = dur sinyali

    # Köyleri parse et
    koyler   = koyleri_parse_et(html)
    atla     = [k for k in koyler if k["atla"]]
    saldir   = [k for k in koyler if not k["atla"]]

    log(f"📋  {len(koyler)} köy  |  Saldırı: {len(saldir)}  |  Atlanan: {len(atla)}")
    for k in atla:
        log(f"   ⏭  Atlandı ({k['atla_neden']})")

    if not saldir:
        log("ℹ️  Filtreyi geçen köy yok.")
        ekran_goruntus_al(tur, "sonra")
        return 0

    # Ekrandaki butonları bul
    butonlar = butonlari_bul()
    if not butonlar:
        log("⚠️  Ekranda A butonu bulunamadı! BUTON_RENK değerini kontrol et.")
        ekran_goruntus_al(tur, "buton_yok")
        return 0

    log(f"🎯  {len(butonlar)} buton bulundu.")
    hedefler = butonlar[:min(len(saldir), len(butonlar))]
    random.shuffle(hedefler)

    tiklanma = 0
    for i, (x, y) in enumerate(hedefler):
        try:
            ms_bekle(TIKLA_MIN_MS, TIKLA_MAX_MS)
            pyautogui.moveTo(x, y, duration=0.15)
            pyautogui.click()
            tiklanma += 1
            log(f"   ✅  ({tiklanma}/{len(hedefler)})  →  ({x}, {y})")
            ms_bekle(TIKLA_MIN_MS, TIKLA_MAX_MS)
        except pyautogui.FailSafeException:
            raise
        except Exception as e:
            log(f"   ⚠️  Tıklama hatası: {e}")

    ekran_goruntus_al(tur, "sonra")
    log(f"📊  Tur tamamlandı: {tiklanma} tıklama.")
    return tiklanma

# ─────────────────────────────────────────────────────
#  YARDIMCI: RENK OKU
# ─────────────────────────────────────────────────────

def renk_al_helper():
    print("\nFareyi A butonunun üzerine götür — 5 saniye sonra renk okunuyor…")
    time.sleep(5)
    x, y = pyautogui.position()
    r, g, b = pyautogui.pixel(x, y)
    print(f"\nKoordinat  : ({x}, {y})")
    print(f"Renk       : ({r}, {g}, {b})")
    print(f"Scriptte   : BUTON_RENK = ({r}, {g}, {b})")

# ─────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  TribalWars Yağma Asistanı  |  Saf Python")
    print("=" * 50)
    print(f"  Sunucu         : {SUNUCU_URL}")
    print(f"  Tıklama arası  : {TIKLA_MIN_MS}–{TIKLA_MAX_MS} ms")
    print(f"  Yenileme arası : {YENILE_MIN_S}–{YENILE_MAX_S} sn")
    print(f"  Çalışma saati  : {CALISMA_BAS} – {CALISMA_BIT}")
    print(f"  Max mesafe     : {MAX_MESAFE}")
    print(f"  Max duvar      : {MAX_DUVAR}")
    print(f"  Birlik filtresi: {BIRLIK_FILTRE or 'Kapalı'}")
    print(f"  Telegram       : {'✅ Aktif' if TELEGRAM_TOKEN else '❌ Kapalı'}")
    print()
    print("  [1] Yağmaya başla")
    print("  [2] A butonu rengini oku")
    print()
    secim = input("Seçim: ").strip()

    if secim == "2":
        renk_al_helper()
        return

    log("🍪  Chrome çerezleri alınıyor…")
    cerez = cerezleri_al()
    if not cerez:
        print("❌  Çerez alınamadı. Chrome açık ve TribalWars'a giriş yapılmış olmalı.")
        return

    geri_sayim(5)

    tur = 0
    toplam = 0

    try:
        while True:
            # Çalışma saati kontrolü
            if not calisma_saati_mi():
                saat_bekle()
                geri_sayim(5)

            tur += 1

            if tur > 1:
                sayfayi_yenile()

            sonuc = yagma_turu(tur, cerez)

            if sonuc == -1:  # Bot koruması — dur
                break

            toplam += sonuc
            log(f"📈  Toplam tıklama: {toplam}")
            sn_bekle(YENILE_MIN_S, YENILE_MAX_S)

    except pyautogui.FailSafeException:
        print("\n⛔  Fare köşeye sürüldü — durduruldu.")
    except KeyboardInterrupt:
        print("\n⛔  Ctrl+C ile durduruldu.")
    finally:
        print(f"\n✔️  Toplam {tur} tur, {toplam} tıklama. İyi oyunlar!")


if __name__ == "__main__":
    main()
