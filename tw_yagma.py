"""
TribalWars Yağma Asistanı — Saf Python (pyautogui)
Bot panelinden başlatılır — input() yok, direkt çalışır.

Kurulum:
    pip install pyautogui pygetwindow
"""

import time
import random
import pyautogui

# ── Ayarlar ──────────────────────────────────────────
TIKLA_MIN_MS  = 369
TIKLA_MAX_MS  = 976
YENILE_MIN_S  = 200
YENILE_MAX_S  = 389
BUTON_RENK    = (161, 115, 69)
RENK_TOLERANS = 30
TARAMA_BOLGESI = None
FARE_HAREKET_SURE = 0.15
GERI_SAYIM_SN = 5   # Başlamadan önce bekleme

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

_calisiyor = True

def ms_bekle(min_ms, max_ms):
    time.sleep(random.randint(min_ms, max_ms) / 1000)

def sn_bekle(min_s, max_s):
    sure = random.randint(min_s, max_s)
    print(f"⏳ Yenileme için {sure} saniye bekleniyor...")
    bitis = time.time() + sure
    while _calisiyor:
        kalan = int(bitis - time.time())
        if kalan <= 0:
            break
        print(f"   {kalan} saniye kaldı...", end="\r")
        time.sleep(min(10, kalan))
    print()

def butonlari_bul():
    konumlar = []
    try:
        ekran = pyautogui.screenshot(region=TARAMA_BOLGESI)
        genislik, yukseklik = ekran.size
        ofset_x = TARAMA_BOLGESI[0] if TARAMA_BOLGESI else 0
        ofset_y = TARAMA_BOLGESI[1] if TARAMA_BOLGESI else 0
        adim = 4
        for y in range(0, yukseklik, adim):
            for x in range(0, genislik, adim):
                r, g, b = ekran.getpixel((x, y))[:3]
                hr, hg, hb = BUTON_RENK
                if (abs(r-hr) <= RENK_TOLERANS and
                    abs(g-hg) <= RENK_TOLERANS and
                    abs(b-hb) <= RENK_TOLERANS):
                    gx, gy = x + ofset_x, y + ofset_y
                    cok_yakin = any(
                        abs(gx-px) < 20 and abs(gy-py) < 20
                        for px, py in konumlar
                    )
                    if not cok_yakin:
                        konumlar.append((gx, gy))
    except Exception as e:
        print(f"⚠ Tarama hatası: {e}")
    return konumlar

def sayfayi_yenile():
    pyautogui.hotkey("f5")
    print("🔄 Sayfa yenilendi (F5)")
    time.sleep(3)

def yagma_turu(tur):
    print(f"\n━━━ TUR {tur} ━━━")
    konumlar = butonlari_bul()
    if not konumlar:
        print("⚠ Hiç buton bulunamadı! BUTON_RENK değerini kontrol et.")
        return 0

    print(f"🎯 {len(konumlar)} buton bulundu.")
    random.shuffle(konumlar)
    tiklanma = 0
    for x, y in konumlar:
        if not _calisiyor:
            break
        try:
            ms_bekle(TIKLA_MIN_MS, TIKLA_MAX_MS)
            pyautogui.moveTo(x, y, duration=FARE_HAREKET_SURE)
            pyautogui.click()
            tiklanma += 1
            print(f"✅ Tıklandı ({tiklanma}/{len(konumlar)}) → ({x}, {y})")
            ms_bekle(TIKLA_MIN_MS, TIKLA_MAX_MS)
        except pyautogui.FailSafeException:
            raise
        except Exception as e:
            print(f"⚠ Tıklama hatası: {e}")

    print(f"📊 Tur tamamlandı: {tiklanma}/{len(konumlar)}")
    return tiklanma

def main():
    global _calisiyor
    print("=" * 50)
    print("  TribalWars Yağma Asistanı")
    print("=" * 50)
    print(f"  Tıklama: {TIKLA_MIN_MS}–{TIKLA_MAX_MS} ms")
    print(f"  Yenileme: {YENILE_MIN_S}–{YENILE_MAX_S} sn")
    print(f"\n{GERI_SAYIM_SN} saniye sonra başlıyor — tarayıcıya geç!")

    for i in range(GERI_SAYIM_SN, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    print("BAŞLADI!\n")

    tur = 0
    toplam = 0
    try:
        while _calisiyor:
            tur += 1
            if tur > 1:
                sayfayi_yenile()
            tiklanma = yagma_turu(tur)
            toplam += tiklanma
            print(f"📈 Toplam tıklama: {toplam}")
            sn_bekle(YENILE_MIN_S, YENILE_MAX_S)

    except pyautogui.FailSafeException:
        print("\n⛔ Fare köşeye sürüldü — durduruldu.")
    except KeyboardInterrupt:
        print("\n⛔ Durduruldu.")
    finally:
        _calisiyor = False
        print(f"\n✔ Toplam {tur} tur, {toplam} tıklama.")

if __name__ == "__main__":
    main()
