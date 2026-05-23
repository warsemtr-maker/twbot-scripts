"""
TribalWars Yağma Asistanı — GUI + Saf Python
==============================================
Kurulum:
    pip install pyautogui requests beautifulsoup4 browser-cookie3
"""

import time
import random
import os
import re
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext

import requests
import pyautogui
from bs4 import BeautifulSoup

try:
    import browser_cookie3
    COOKIE_DESTEGI = True
except ImportError:
    COOKIE_DESTEGI = False

pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0.05

VARSAYILAN = {
    "sunucu_url"      : "https://tr1.tribalwars.com.tr",
    "tikla_min_ms"    : 369,
    "tikla_max_ms"    : 976,
    "yenile_min_s"    : 200,
    "yenile_max_s"    : 389,
    "max_mesafe"      : 20.0,
    "max_duvar"       : 4,
    "birlik_filtre"   : "spear:50,sword:30,spy:3",
    "calisma_bas"     : "08:00",
    "calisma_bit"     : "23:30",
    "buton_renk_r"    : 161,
    "buton_renk_g"    : 115,
    "buton_renk_b"    : 69,
    "renk_tolerans"   : 30,
    "screenshots_klas": "screenshots",
    "once_sonra"      : True,
    "telegram_token"  : "",
    "telegram_chat_id": "",
}

def telegram_gonder(token, chat_id, mesaj, resim_yolu=None):
    if not token or not chat_id:
        return
    try:
        if resim_yolu and os.path.exists(resim_yolu):
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(resim_yolu, "rb") as f:
                requests.post(url, data={"chat_id": chat_id, "caption": mesaj},
                              files={"photo": f}, timeout=10)
        else:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, data={"chat_id": chat_id, "text": mesaj,
                                     "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Telegram gönderilemedi: {e}")

def ms_bekle(mn, mx):
    time.sleep(random.randint(mn, mx) / 1000)

def saat_parse(s):
    h, m = map(int, s.split(":"))
    return h * 60 + m

def calisma_saati_mi(bas, bit):
    simdi = datetime.now()
    dk = simdi.hour * 60 + simdi.minute
    b, e = saat_parse(bas), saat_parse(bit)
    if b <= e:
        return b <= dk <= e
    return dk >= b or dk <= e

def cerezleri_al(domain):
    if not COOKIE_DESTEGI:
        return None
    try:
        return browser_cookie3.chrome(domain_name=domain)
    except:
        return None

def html_cek(farm_url, cerez_jar):
    headers = {
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
        return None

def koyleri_parse_et(html, max_mesafe, max_duvar, birlik_filtre):
    soup = BeautifulSoup(html, "html.parser")
    koyler = []
    tablo = soup.find("table", id="plunder_list")
    if not tablo:
        tablo = soup.find("table", {"class": re.compile(r"vis")})
    if not tablo:
        return []
    for satir in tablo.find_all("tr")[1:]:
        hucreler = satir.find_all("td")
        if len(hucreler) < 3:
            continue
        koy = {"mesafe": None, "duvar": None, "birlikler": {}, "atla": False, "atla_neden": ""}
        buton = satir.find("input", {"class": re.compile(r"farm_icon")})
        if buton:
            koy["farm_id"] = buton.get("data-farmid", "")
        for h in hucreler:
            cls = " ".join(h.get("class", []))
            if "dist" in cls or "distance" in cls:
                try: koy["mesafe"] = float(h.get_text(strip=True).replace(",", "."))
                except: pass
            if "wall" in cls or "building_wall" in cls:
                try: koy["duvar"] = int(re.search(r"\d+", h.get_text()).group())
                except: koy["duvar"] = 0
            m = re.match(r"units_(\w+)", cls)
            if m:
                try: koy["birlikler"][m.group(1)] = int(re.search(r"\d+", h.get_text() or "0").group())
                except: koy["birlikler"][m.group(1)] = 0
        if max_mesafe and koy["mesafe"] and koy["mesafe"] > max_mesafe:
            koy["atla"], koy["atla_neden"] = True, f"mesafe {koy['mesafe']} > {max_mesafe}"
        if not koy["atla"] and max_duvar is not None and koy["duvar"] is not None and koy["duvar"] > max_duvar:
            koy["atla"], koy["atla_neden"] = True, f"duvar {koy['duvar']} > {max_duvar}"
        if not koy["atla"] and birlik_filtre:
            for parca in birlik_filtre.split(","):
                parca = parca.strip()
                if not parca: continue
                if ":" in parca:
                    b, min_str = parca.split(":", 1)
                    b = b.strip()
                    try: minimum = int(min_str.strip())
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

def butonlari_bul(renk, tolerans):
    konumlar = []
    try:
        ekran = pyautogui.screenshot()
        gw, gh = ekran.size
        hr, hg, hb = renk
        for y in range(0, gh, 4):
            for x in range(0, gw, 4):
                r, g, b = ekran.getpixel((x, y))[:3]
                if abs(r-hr)<=tolerans and abs(g-hg)<=tolerans and abs(b-hb)<=tolerans:
                    if not any(abs(x-px)<20 and abs(y-py)<20 for px,py in konumlar):
                        konumlar.append((x, y))
    except: pass
    return konumlar

class TwGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TribalWars Yağma Asistanı")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")
        self.calisıyor = False
        self.thread    = None
        self.dur_event = threading.Event()
        self.tur_sayisi    = 0
        self.toplam_tikla  = 0
        self.toplam_atla   = 0
        self.baslama_zamani = None
        self._arayuz_kur()

    BG="1e1e2e"; PANEL="#2a2a3e"; ACCENT="#c0392b"; YESIL="#27ae60"
    SARI="#f39c12"; METIN="#ecf0f1"; GRI="#7f8c8d"
    BUTON_ON="#c0392b"; BUTON_OF="#27ae60"

    def _etiket(self, parent, metin, renk=None, bold=False, size=10):
        font = ("Segoe UI", size, "bold" if bold else "normal")
        return tk.Label(parent, text=metin, bg=self.PANEL, fg=renk or self.METIN, font=font)

    def _giris(self, parent, genislik=12, varsayilan=""):
        e = tk.Entry(parent, width=genislik, bg="#16213e", fg=self.METIN,
                     insertbackground=self.METIN, relief="flat",
                     font=("Segoe UI", 9), bd=4)
        e.insert(0, str(varsayilan))
        return e

    def _panel(self, parent, baslik):
        return tk.LabelFrame(parent, text=f"  {baslik}  ",
                             bg=self.PANEL, fg=self.SARI,
                             font=("Segoe UI", 9, "bold"),
                             bd=1, relief="groove", labelanchor="n")

    def _arayuz_kur(self):
        SOL = tk.Frame(self.root, bg="#1e1e2e", padx=10, pady=10)
        SOL.grid(row=0, column=0, sticky="nsew")
        SAG = tk.Frame(self.root, bg="#1e1e2e", padx=10, pady=10)
        SAG.grid(row=0, column=1, sticky="nsew")
        self._sunucu_panel(SOL)
        self._zamanlama_panel(SOL)
        self._filtre_panel(SOL)
        self._renk_panel(SOL)
        self._saat_panel(SOL)
        self._telegram_panel(SOL)
        self._istatistik_panel(SAG)
        self._log_panel(SAG)
        self._kontrol_panel(SAG)

    def _satir(self, parent, etiket, widget, row):
        tk.Label(parent, text=etiket, bg=self.PANEL, fg=self.GRI,
                 font=("Segoe UI", 9), anchor="w").grid(row=row, column=0, sticky="w", padx=8, pady=3)
        widget.grid(row=row, column=1, sticky="w", padx=8, pady=3)

    def _sunucu_panel(self, parent):
        f = self._panel(parent, "🌐  Sunucu")
        f.pack(fill="x", pady=(0, 6))
        f.columnconfigure(1, weight=1)
        self.e_sunucu = self._giris(f, 32, VARSAYILAN["sunucu_url"])
        self._satir(f, "URL", self.e_sunucu, 0)

    def _zamanlama_panel(self, parent):
        f = self._panel(parent, "⏱  Zamanlama")
        f.pack(fill="x", pady=6)
        f.columnconfigure(1, weight=1)
        self.e_tikla_min = self._giris(f, 6, VARSAYILAN["tikla_min_ms"])
        self.e_tikla_max = self._giris(f, 6, VARSAYILAN["tikla_max_ms"])
        self.e_yen_min   = self._giris(f, 6, VARSAYILAN["yenile_min_s"])
        self.e_yen_max   = self._giris(f, 6, VARSAYILAN["yenile_max_s"])
        row = tk.Frame(f, bg=self.PANEL)
        row.grid(row=0, column=1, sticky="w", padx=8, pady=3)
        self.e_tikla_min.pack(in_=row, side="left")
        tk.Label(row, text=" – ", bg=self.PANEL, fg=self.GRI).pack(side="left")
        self.e_tikla_max.pack(in_=row, side="left")
        tk.Label(f, text="Tıklama (ms)", bg=self.PANEL, fg=self.GRI,
                 font=("Segoe UI", 9), anchor="w").grid(row=0, column=0, sticky="w", padx=8)
        row2 = tk.Frame(f, bg=self.PANEL)
        row2.grid(row=1, column=1, sticky="w", padx=8, pady=3)
        self.e_yen_min.pack(in_=row2, side="left")
        tk.Label(row2, text=" – ", bg=self.PANEL, fg=self.GRI).pack(side="left")
        self.e_yen_max.pack(in_=row2, side="left")
        tk.Label(f, text="Yenileme (sn)", bg=self.PANEL, fg=self.GRI,
                 font=("Segoe UI", 9), anchor="w").grid(row=1, column=0, sticky="w", padx=8)

    def _filtre_panel(self, parent):
        f = self._panel(parent, "🔎  Filtreler")
        f.pack(fill="x", pady=6)
        f.columnconfigure(1, weight=1)
        self.e_mesafe = self._giris(f, 8, VARSAYILAN["max_mesafe"])
        self.e_duvar  = self._giris(f, 8, VARSAYILAN["max_duvar"])
        self.e_birlik = self._giris(f, 8, VARSAYILAN["birlik_filtre"])
        self._satir(f, "Max mesafe", self.e_mesafe, 0)
        self._satir(f, "Max duvar",  self.e_duvar,  1)
        self._satir(f, "Birlik min", self.e_birlik, 2)

    def _renk_panel(self, parent):
        f = self._panel(parent, "🎨  A Butonu Rengi")
        f.pack(fill="x", pady=6)
        self.e_r   = self._giris(f, 4, VARSAYILAN["buton_renk_r"])
        self.e_g   = self._giris(f, 4, VARSAYILAN["buton_renk_g"])
        self.e_b   = self._giris(f, 4, VARSAYILAN["buton_renk_b"])
        self.e_tol = self._giris(f, 4, VARSAYILAN["renk_tolerans"])
        row = tk.Frame(f, bg=self.PANEL)
        row.pack(fill="x", padx=8, pady=4)
        for lbl, w in [("R", self.e_r), ("G", self.e_g), ("B", self.e_b), ("±", self.e_tol)]:
            tk.Label(row, text=lbl, bg=self.PANEL, fg=self.GRI, font=("Segoe UI", 9)).pack(side="left")
            w.pack(side="left", padx=2)
        self.renk_onizleme = tk.Frame(f, bg="#ffffff", width=28, height=20, relief="flat")
        self.renk_onizleme.pack(side="left", padx=6)
        tk.Button(f, text="Önizle", command=self._renk_onizle,
                  bg=self.PANEL, fg=self.METIN, relief="flat",
                  font=("Segoe UI", 8), cursor="hand2").pack(side="left")

    def _saat_panel(self, parent):
        f = self._panel(parent, "🕐  Çalışma Saatleri")
        f.pack(fill="x", pady=6)
        f.columnconfigure(1, weight=1)
        self.e_bas = self._giris(f, 8, VARSAYILAN["calisma_bas"])
        self.e_bit = self._giris(f, 8, VARSAYILAN["calisma_bit"])
        self._satir(f, "Başlangıç", self.e_bas, 0)
        self._satir(f, "Bitiş",     self.e_bit, 1)

    def _telegram_panel(self, parent):
        f = self._panel(parent, "📨  Telegram Bildirimi")
        f.pack(fill="x", pady=6)
        f.columnconfigure(1, weight=1)
        self.e_tg_token   = self._giris(f, 28, VARSAYILAN["telegram_token"])
        self.e_tg_chat_id = self._giris(f, 28, VARSAYILAN["telegram_chat_id"])
        self._satir(f, "Bot Token", self.e_tg_token,   0)
        self._satir(f, "Chat ID",   self.e_tg_chat_id, 1)

    def _istatistik_panel(self, parent):
        f = self._panel(parent, "📊  İstatistikler")
        f.pack(fill="x", pady=(0, 6))
        ic = tk.Frame(f, bg=self.PANEL)
        ic.pack(fill="x", padx=8, pady=6)
        def stat_kutu(p, baslik, renk):
            k = tk.Frame(p, bg="#1e1e2e", padx=10, pady=6)
            k.pack(side="left", expand=True, fill="x", padx=4)
            tk.Label(k, text=baslik, bg="#1e1e2e", fg=self.GRI, font=("Segoe UI", 8)).pack()
            lbl = tk.Label(k, text="0", bg="#1e1e2e", fg=renk, font=("Segoe UI", 16, "bold"))
            lbl.pack()
            return lbl
        self.lbl_tur   = stat_kutu(ic, "TUR",     self.SARI)
        self.lbl_tikla = stat_kutu(ic, "TIKLAMA", self.YESIL)
        self.lbl_atla  = stat_kutu(ic, "ATLANAN", self.ACCENT)
        self.lbl_durum = tk.Label(f, text="⬤  Bekleniyor", bg=self.PANEL, fg=self.GRI,
                                  font=("Segoe UI", 9, "bold"))
        self.lbl_durum.pack(pady=(0, 4))
        self.lbl_geri  = tk.Label(f, text="", bg=self.PANEL, fg=self.SARI, font=("Segoe UI", 9))
        self.lbl_geri.pack(pady=(0, 6))

    def _log_panel(self, parent):
        f = self._panel(parent, "📋  Log")
        f.pack(fill="both", expand=True, pady=6)
        self.log_kutu = scrolledtext.ScrolledText(
            f, width=48, height=18, bg="#0d0d1a", fg=self.METIN,
            font=("Consolas", 8), relief="flat", bd=0, state="disabled")
        self.log_kutu.pack(fill="both", expand=True, padx=6, pady=6)
        self.log_kutu.tag_config("yesil",   foreground="#27ae60")
        self.log_kutu.tag_config("sari",    foreground="#f39c12")
        self.log_kutu.tag_config("kirmizi", foreground="#e74c3c")
        self.log_kutu.tag_config("gri",     foreground="#7f8c8d")
        self.log_kutu.tag_config("beyaz",   foreground="#ecf0f1")

    def _kontrol_panel(self, parent):
        f = tk.Frame(parent, bg="#1e1e2e")
        f.pack(fill="x", pady=6)
        self.btn_basla = tk.Button(f, text="▶  BAŞLAT", command=self._basla_durdur,
                                   bg=self.BUTON_OF, fg="white",
                                   font=("Segoe UI", 11, "bold"), relief="flat",
                                   cursor="hand2", height=2, width=20)
        self.btn_basla.pack(side="left", padx=4)
        tk.Button(f, text="🗑  Logu Temizle", command=self._log_temizle,
                  bg=self.PANEL, fg=self.GRI, relief="flat",
                  font=("Segoe UI", 9), cursor="hand2").pack(side="left", padx=4)

    def log(self, metin, tag="beyaz"):
        def _yaz():
            self.log_kutu.config(state="normal")
            zaman = datetime.now().strftime("%H:%M:%S")
            self.log_kutu.insert("end", f"[{zaman}] {metin}\n", tag)
            self.log_kutu.see("end")
            self.log_kutu.config(state="disabled")
        self.root.after(0, _yaz)

    def _log_temizle(self):
        self.log_kutu.config(state="normal")
        self.log_kutu.delete("1.0", "end")
        self.log_kutu.config(state="disabled")

    def _stat_guncelle(self):
        self.root.after(0, lambda: self.lbl_tur.config(text=str(self.tur_sayisi)))
        self.root.after(0, lambda: self.lbl_tikla.config(text=str(self.toplam_tikla)))
        self.root.after(0, lambda: self.lbl_atla.config(text=str(self.toplam_atla)))

    def _durum(self, metin, renk=None):
        self.root.after(0, lambda: self.lbl_durum.config(text=metin, fg=renk or self.GRI))

    def _geri_sayim_goster(self, metin):
        self.root.after(0, lambda: self.lbl_geri.config(text=metin))

    def _renk_onizle(self):
        try:
            r = int(self.e_r.get()); g = int(self.e_g.get()); b = int(self.e_b.get())
            self.renk_onizleme.config(bg=f"#{r:02x}{g:02x}{b:02x}")
        except: pass

    def _ayarlari_oku(self):
        def f(widget, tip=str, varsayilan=None):
            try: return tip(widget.get().strip())
            except: return varsayilan
        return {
            "sunucu_url"      : f(self.e_sunucu),
            "tikla_min_ms"    : f(self.e_tikla_min, int, 369),
            "tikla_max_ms"    : f(self.e_tikla_max, int, 976),
            "yenile_min_s"    : f(self.e_yen_min,   int, 200),
            "yenile_max_s"    : f(self.e_yen_max,   int, 389),
            "max_mesafe"      : f(self.e_mesafe, float, None),
            "max_duvar"       : f(self.e_duvar,  int,   None),
            "telegram_token"  : f(self.e_tg_token)   or "",
            "telegram_chat_id": f(self.e_tg_chat_id) or "",
            "birlik_filtre"   : f(self.e_birlik) or None,
            "calisma_bas"     : f(self.e_bas) or "00:00",
            "calisma_bit"     : f(self.e_bit) or "23:59",
            "buton_renk"      : (f(self.e_r,int,161), f(self.e_g,int,115), f(self.e_b,int,69)),
            "renk_tolerans"   : f(self.e_tol, int, 30),
        }

    def _basla_durdur(self):
        if self.calisıyor:
            self.dur_event.set()
            self.calisıyor = False
            self.btn_basla.config(text="▶  BAŞLAT", bg=self.BUTON_OF)
            self._durum("⬤  Durduruldu", self.ACCENT)
            self.log("Kullanıcı tarafından durduruldu.", "kirmizi")
        else:
            self.dur_event.clear()
            self.calisıyor = True
            self.tur_sayisi = 0; self.toplam_tikla = 0; self.toplam_atla = 0
            self.baslama_zamani = datetime.now()
            self.btn_basla.config(text="⏹  DURDUR", bg=self.BUTON_ON)
            self._durum("⬤  Çalışıyor", self.YESIL)
            self.thread = threading.Thread(target=self._dongu, daemon=True)
            self.thread.start()

    def _dongu(self):
        ayar = self._ayarlari_oku()
        farm_url = f"{ayar['sunucu_url']}/game.php?village=0&screen=am_farm"
        self.log("Chrome çerezleri alınıyor…", "sari")
        cerez = cerezleri_al(ayar["sunucu_url"].replace("https://","").replace("http://",""))
        if not cerez:
            self.log("❌ Çerez alınamadı!", "kirmizi")
            self._sonlandir(); return
        self.log("✅ Çerezler alındı.", "yesil")
        for i in range(5, 0, -1):
            if self.dur_event.is_set(): break
            self._geri_sayim_goster(f"⏳ Tarayıcıya geç!  {i}…")
            time.sleep(1)
        self._geri_sayim_goster("")
        tur = 0
        while not self.dur_event.is_set():
            if not calisma_saati_mi(ayar["calisma_bas"], ayar["calisma_bit"]):
                self._durum("😴  Saat bekleniyor", self.GRI)
                self.log(f"Çalışma saati dışında. {ayar['calisma_bas']} bekleniyor…", "gri")
                while not self.dur_event.is_set() and \
                      not calisma_saati_mi(ayar["calisma_bas"], ayar["calisma_bit"]):
                    self._geri_sayim_goster(f"💤 {datetime.now().strftime('%H:%M:%S')}")
                    time.sleep(30)
                self._geri_sayim_goster("")
                if self.dur_event.is_set(): break
                self._durum("⬤  Çalışıyor", self.YESIL); continue
            tur += 1; self.tur_sayisi = tur; self._stat_guncelle()
            self.log(f"━━━  TUR {tur}  ━━━", "sari")
            self._durum(f"⬤  Tur {tur} — veri çekiliyor…", self.YESIL)
            if tur > 1:
                pyautogui.hotkey("f5"); self.log("F5 — sayfa yenilendi.", "gri"); time.sleep(3)
            html = html_cek(farm_url, cerez)
            if not html:
                self.log("❌ HTML alınamadı.", "kirmizi")
            else:
                if 'id="botprotection_quest"' in html or "botprotection_quest" in html:
                    self.log("🚨 BOT KORUMASI ALGILANDI!", "kirmizi")
                    self._durum("🚨  BOT KORUMASI", self.ACCENT)
                    self.dur_event.set()
                    ekran_dosya = self._ekran_goruntus_al(tur, "bot_koruma", ayar)
                    token = ayar.get("telegram_token",""); chat_id = ayar.get("telegram_chat_id","")
                    mesaj = (f"🚨 <b>Bot Koruması!</b>\n⏰ {datetime.now().strftime('%H:%M:%S')}\n"
                             f"🔄 Tur: {tur}\nScript durduruldu.")
                    threading.Thread(target=telegram_gonder,
                                     args=(token,chat_id,mesaj,ekran_dosya),daemon=True).start()
                    try:
                        import winsound
                        for _ in range(5): winsound.Beep(1000,400); time.sleep(0.2)
                    except: pass
                    return
                koyler = koyleri_parse_et(html, ayar["max_mesafe"], ayar["max_duvar"], ayar["birlik_filtre"])
                atla   = [k for k in koyler if k["atla"]]
                saldir = [k for k in koyler if not k["atla"]]
                self.toplam_atla += len(atla)
                self.log(f"📋 {len(koyler)} köy  |  Saldırı: {len(saldir)}  |  Atlanan: {len(atla)}", "beyaz")
                for k in atla: self.log(f"   ⏭ {k['atla_neden']}", "gri")
                if saldir:
                    butonlar = butonlari_bul(ayar["buton_renk"], ayar["renk_tolerans"])
                    if not butonlar:
                        self.log("⚠️ Buton bulunamadı!", "kirmizi")
                    else:
                        self.log(f"🎯 {len(butonlar)} buton.", "yesil")
                        hedefler = butonlar[:min(len(saldir), len(butonlar))]
                        random.shuffle(hedefler)
                        for i, (x, y) in enumerate(hedefler):
                            if self.dur_event.is_set(): break
                            ms_bekle(ayar["tikla_min_ms"], ayar["tikla_max_ms"])
                            pyautogui.moveTo(x, y, duration=0.15); pyautogui.click()
                            self.toplam_tikla += 1; self._stat_guncelle()
                            self.log(f"   ✅ ({i+1}/{len(hedefler)})  ({x},{y})", "yesil")
                            ms_bekle(ayar["tikla_min_ms"], ayar["tikla_max_ms"])
                else:
                    self.log("ℹ️ Filtreyi geçen köy yok.", "gri")
            self._ekran_goruntus_al(tur, "sonra", ayar)
            if self.dur_event.is_set(): break
            bekleme = random.randint(ayar["yenile_min_s"], ayar["yenile_max_s"])
            self.log(f"⏳ {bekleme} sn bekleniyor…", "sari")
            bitis = time.time() + bekleme
            while not self.dur_event.is_set():
                kalan = int(bitis - time.time())
                if kalan <= 0: break
                self._geri_sayim_goster(f"⏳ Sonraki tur: {kalan} sn"); time.sleep(1)
            self._geri_sayim_goster("")
        self._sonlandir()

    def _ekran_goruntus_al(self, tur, etiket, ayar):
        try:
            klasor = ayar.get("screenshots_klas", "screenshots")
            os.makedirs(klasor, exist_ok=True)
            zaman = datetime.now().strftime("%H-%M-%S")
            dosya = os.path.join(klasor, f"tur_{tur:03d}_{etiket}_{zaman}.png")
            pyautogui.screenshot(dosya)
            self.log(f"📸 {dosya}", "gri")
            return dosya
        except Exception as e:
            self.log(f"📸 Hata: {e}", "kirmizi")
            return None

    def _sonlandir(self):
        self.calisıyor = False
        self.root.after(0, lambda: self.btn_basla.config(text="▶  BAŞLAT", bg=self.BUTON_OF))
        self._durum("⬤  Durduruldu", self.ACCENT)
        self._geri_sayim_goster("")
        self.log(f"✔ Toplam {self.tur_sayisi} tur, {self.toplam_tikla} tıklama.", "yesil")

def main():
    root = tk.Tk()
    app  = TwGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
