from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import random

# ================= AYARLAR =================
world_url = "https://enc1.tribalwars.net"   # Kendi world'ünü yaz
village_id = "7871"                         # Köy ID
template = "A"                              # "A" veya "B"

min_troops = 20                             # Minimum asker sayısı (20'den azsa göndermeyecek)

raid_count = 999

# Tıklama aralığı (ms)
min_click_delay = 552
max_click_delay = 1254
# ===========================================

def go_to_loot_assistant():
    url = f"{world_url}/game.php?village={village_id}&screen=am_farm"
    driver.get(url)
    time.sleep(4)
    print("✅ Loot Assistant sayfasına gidildi.")

def get_available_troops():
    """Available bölümünden toplam asker sayısını alır"""
    try:
        # Tüm Available asker sayılarını bul
        troops = driver.find_elements(By.XPATH, "//td[@class='farm_icon']//following-sibling::td[contains(@class, 'unit') or contains(@class, 'troop')]")
        total = 0
        for troop in troops[:6]:  # İlk 6 birim (mızrak, kılıç, vs.)
            try:
                num = int(troop.text.strip().replace('.', '').replace(',', ''))
                total += num
            except:
                continue
        return total
    except:
        return 0

def send_raid():
    available = get_available_troops()
    
    if available < min_troops:
        print(f"⚠️ Yetersiz asker ({available}). Bekleniyor...")
        return False
    
    try:
        # Template butonuna tıkla
        button = driver.find_element(By.XPATH, f"//a[contains(@class, 'farm_icon') and contains(text(), '{template}')]")
        button.click()
        print(f"✅ {template} template ile yağma gönderildi. (Asker: {available})")
        return True
    except:
        try:
            driver.find_element(By.XPATH, f"//img[@title='{template}']/parent::a").click()
            print(f"✅ {template} template ile yağma gönderildi. (Asker: {available})")
            return True
        except:
            print("❌ Buton bulunamadı.")
            return False

# ================= ANA PROGRAM =================
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    go_to_loot_assistant()
    print("🚀 Asker kontrollü yağma botu başladı!\n")
    
    for i in range(raid_count):
        success = send_raid()
        
        if success:
            delay_ms = random.randint(min_click_delay, max_click_delay)
            delay_sec = delay_ms / 1000.0
            time.sleep(delay_sec)
        else:
            # Yetersiz asker durumunda daha uzun bekle
            time.sleep(random.uniform(8, 15))

except KeyboardInterrupt:
    print("\n\nBot durduruldu.")
except Exception as e:
    print(f"Hata: {e}")
finally:
    input("\nBot bitti. Tarayıcıyı kapatmak için Enter'a bas...")
    driver.quit()