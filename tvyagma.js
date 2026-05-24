(function() {
    'use strict';

    if (!window.location.href.includes('screen=am_farm')) return;

    function gmGet(key, def) {
        const val = localStorage.getItem('FarmGod_' + key);
        if (val === null) return def;
        try { return JSON.parse(val); } catch { return val; }
    }
    function gmSet(key, value) {
        localStorage.setItem('FarmGod_' + key, JSON.stringify(value));
    }

    let ayarlar = {
        scriptUrl: gmGet('scriptUrl', 'https://higamy.github.io/TW/Scripts/Approved/FarmGodCopy.js'),
        tiklamaMin: gmGet('tiklamaMin', 500),
        tiklamaMax: gmGet('tiklamaMax', 1000),
        aralilar: gmGet('aralilar', [[100,150],[150,200],[200,250],[250,300],[300,350]]),
        aktif: gmGet('aktif', true),
        molalar: gmGet('molalar', [['02:00','08:00']]),
        tgToken: gmGet('tgToken', ''),
        tgChatId: gmGet('tgChatId', '')
    };

    let durduruldu = !ayarlar.aktif;
    let sayacInterval = null;
    let molaKontrolInterval = null;
    let panelAcik = false;
    let botKorumaMessajAtildi = false;

    function oyunSaati() {
        const now = new Date();
        const saat = now.getUTCHours().toString().padStart(2,'0');
        const dakika = now.getUTCMinutes().toString().padStart(2,'0');
        return `${saat}:${dakika}`;
    }

    function saateDakika(saat) {
        const [h, m] = saat.split(':').map(Number);
        return h * 60 + m;
    }

    function moladaMi() {
        const simdi = saateDakika(oyunSaati());
        for (const [bas, bitis] of ayarlar.molalar) {
            const b = saateDakika(bas);
            const bt = saateDakika(bitis);
            if (b <= bt) {
                if (simdi >= b && simdi < bt) return true;
            } else {
                if (simdi >= b || simdi < bt) return true;
            }
        }
        return false;
    }

    function molaBitisineKalanDakika() {
        const simdi = saateDakika(oyunSaati());
        let enAzKalan = Infinity;
        for (const [bas, bitis] of ayarlar.molalar) {
            const b = saateDakika(bas);
            const bt = saateDakika(bitis);
            let kalan;
            if (b <= bt) {
                if (simdi >= b && simdi < bt) kalan = bt - simdi;
            } else {
                if (simdi >= b || simdi < bt)
                    kalan = simdi >= b ? (1440 - simdi + bt) : (bt - simdi);
            }
            if (kalan !== undefined && kalan < enAzKalan) enAzKalan = kalan;
        }
        return enAzKalan === Infinity ? 0 : enAzKalan;
    }

    function telegramMesajAt(mesaj) {
        if (!ayarlar.tgToken || !ayarlar.tgChatId) return;
        fetch(`https://api.telegram.org/bot${ayarlar.tgToken}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: ayarlar.tgChatId,
                text: mesaj,
                parse_mode: 'HTML'
            })
        }).catch(() => {});
    }

    function botKorumaVar() {
        const var_ = document.querySelector("#botprotection_quest") !== null ||
                     document.querySelector(".bot-protection-row") !== null;
        if (var_ && !botKorumaMessajAtildi) {
            botKorumaMessajAtildi = true;
            telegramMesajAt(`⚠️ <b>Bot Koruma Algılandı!</b>\n🌐 ${window.location.href}\n⏰ UTC ${oyunSaati()}`);
        }
        return var_;
    }

    // Ana panel
    const panel = document.createElement('div');
    panel.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(20,20,20,0.95);
        color: #fff;
        padding: 12px 18px;
        border-radius: 10px;
        font-size: 13px;
        font-family: monospace;
        z-index: 99999;
        min-width: 220px;
        border: 1px solid #f90;
        box-shadow: 0 0 10px rgba(255,150,0,0.3);
    `;
    panel.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <span style="color:#f90;font-weight:bold;font-size:15px;">⚔️ FarmGod Bot</span>
            <span id="fg_oyunsaati" style="color:#aaa;font-size:11px;">UTC --:--</span>
        </div>
        <div id="fg_durum">Başlatılıyor...</div>
        <div id="fg_sayac" style="font-size:26px;text-align:center;margin:8px 0;color:#0f0;">--</div>
        <div style="display:flex;gap:6px;margin-top:8px;">
            <button id="fg_baslatdurdur" style="flex:1;padding:6px;border-radius:6px;border:none;cursor:pointer;font-weight:bold;background:${ayarlar.aktif ? '#c00' : '#080'};color:#fff;">
                ${ayarlar.aktif ? '⏹ Durdur' : '▶ Başlat'}
            </button>
            <button id="fg_ayarlar_btn" style="flex:1;padding:6px;border-radius:6px;border:none;cursor:pointer;font-weight:bold;background:#555;color:#fff;">
                ⚙️ Ayarlar
            </button>
        </div>
    `;
    document.body.appendChild(panel);

    setInterval(() => {
        const el = document.getElementById('fg_oyunsaati');
        if (el) el.textContent = 'UTC ' + oyunSaati();
    }, 1000);

    // Ayarlar paneli
    const ayarlarPanel = document.createElement('div');
    ayarlarPanel.style.cssText = `
        position: fixed;
        bottom: 140px;
        right: 20px;
        background: rgba(20,20,20,0.97);
        color: #fff;
        padding: 16px;
        border-radius: 10px;
        font-size: 13px;
        font-family: monospace;
        z-index: 99999;
        width: 320px;
        border: 1px solid #f90;
        box-shadow: 0 0 10px rgba(255,150,0,0.3);
        display: none;
        max-height: 80vh;
        overflow-y: auto;
    `;
    ayarlarPanel.innerHTML = `
        <div style="color:#f90;font-weight:bold;margin-bottom:12px;font-size:14px;">⚙️ Ayarlar</div>

        <div style="margin-bottom:10px;">
            <label style="color:#aaa;">FarmGod Script URL</label><br>
            <input id="fg_url" type="text" value="${ayarlar.scriptUrl}" style="width:100%;padding:5px;margin-top:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;box-sizing:border-box;">
        </div>

        <div style="margin-bottom:10px;">
            <label style="color:#aaa;">Tıklama Hızı (ms)</label>
            <div style="display:flex;gap:8px;margin-top:4px;align-items:center;">
                <input id="fg_tikMin" type="number" value="${ayarlar.tiklamaMin}" style="width:80px;padding:5px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;">
                <span style="color:#aaa;">-</span>
                <input id="fg_tikMax" type="number" value="${ayarlar.tiklamaMax}" style="width:80px;padding:5px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;">
                <span style="color:#aaa;">ms</span>
            </div>
        </div>

        <div style="margin-bottom:10px;">
            <label style="color:#aaa;">Yenileme Aralıkları (sn)</label>
            <div id="fg_aralilar_list" style="margin-top:6px;"></div>
            <button id="fg_aralik_ekle" style="margin-top:6px;padding:4px 10px;background:#444;border:1px solid #888;color:#fff;border-radius:4px;cursor:pointer;">+ Ekle</button>
        </div>

        <div style="margin-bottom:10px;">
            <label style="color:#aaa;">☕ Mola Saatleri (UTC - Oyun Saati)</label>
            <div id="fg_mola_list" style="margin-top:6px;"></div>
            <button id="fg_mola_ekle" style="margin-top:6px;padding:4px 10px;background:#444;border:1px solid #888;color:#fff;border-radius:4px;cursor:pointer;">+ Mola Ekle</button>
        </div>

        <div style="margin-bottom:10px;">
            <label style="color:#aaa;">🤖 Telegram Bot Token</label><br>
            <input id="fg_tg_token" type="text" value="${ayarlar.tgToken}" placeholder="123456:ABC-DEF..." style="width:100%;padding:5px;margin-top:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;box-sizing:border-box;">
        </div>

        <div style="margin-bottom:10px;">
            <label style="color:#aaa;">🤖 Telegram Chat ID</label><br>
            <input id="fg_tg_chatid" type="text" value="${ayarlar.tgChatId}" placeholder="-100xxxxxxxxx" style="width:100%;padding:5px;margin-top:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;box-sizing:border-box;">
        </div>

        <div style="display:flex;gap:8px;margin-top:12px;">
            <button id="fg_kaydet" style="flex:1;padding:8px;background:#f90;border:none;color:#000;font-weight:bold;border-radius:6px;cursor:pointer;">💾 Kaydet</button>
            <button id="fg_kapat" style="flex:1;padding:8px;background:#555;border:none;color:#fff;border-radius:6px;cursor:pointer;">✖ Kapat</button>
        </div>
    `;
    document.body.appendChild(ayarlarPanel);

    function araliklarCiz() {
        const liste = document.getElementById('fg_aralilar_list');
        liste.innerHTML = '';
        ayarlar.aralilar.forEach((aralik, i) => {
            const satir = document.createElement('div');
            satir.style.cssText = 'display:flex;gap:6px;margin-bottom:4px;align-items:center;';
            satir.innerHTML = `
                <input type="number" value="${aralik[0]}" data-i="${i}" data-j="0" style="width:70px;padding:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;">
                <span style="color:#aaa;">-</span>
                <input type="number" value="${aralik[1]}" data-i="${i}" data-j="1" style="width:70px;padding:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;">
                <span style="color:#aaa;">sn</span>
                <button data-sil="${i}" style="padding:2px 8px;background:#900;border:none;color:#fff;border-radius:4px;cursor:pointer;">✖</button>
            `;
            liste.appendChild(satir);
        });
        liste.querySelectorAll('[data-sil]').forEach(btn => {
            btn.addEventListener('click', function() {
                ayarlar.aralilar.splice(parseInt(this.dataset.sil), 1);
                araliklarCiz();
            });
        });
        liste.querySelectorAll('input').forEach(inp => {
            inp.addEventListener('change', function() {
                ayarlar.aralilar[parseInt(this.dataset.i)][parseInt(this.dataset.j)] = parseInt(this.value);
            });
        });
    }

    function molalarCiz() {
        const liste = document.getElementById('fg_mola_list');
        liste.innerHTML = '';
        ayarlar.molalar.forEach((mola, i) => {
            const satir = document.createElement('div');
            satir.style.cssText = 'display:flex;gap:6px;margin-bottom:4px;align-items:center;';
            satir.innerHTML = `
                <input type="time" value="${mola[0]}" data-mi="${i}" data-mj="0" style="width:90px;padding:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;">
                <span style="color:#aaa;">-</span>
                <input type="time" value="${mola[1]}" data-mi="${i}" data-mj="1" style="width:90px;padding:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;">
                <button data-msil="${i}" style="padding:2px 8px;background:#900;border:none;color:#fff;border-radius:4px;cursor:pointer;">✖</button>
            `;
            liste.appendChild(satir);
        });
        liste.querySelectorAll('[data-msil]').forEach(btn => {
            btn.addEventListener('click', function() {
                ayarlar.molalar.splice(parseInt(this.dataset.msil), 1);
                molalarCiz();
            });
        });
        liste.querySelectorAll('input[type=time]').forEach(inp => {
            inp.addEventListener('change', function() {
                ayarlar.molalar[parseInt(this.dataset.mi)][parseInt(this.dataset.mj)] = this.value;
            });
        });
    }

    araliklarCiz();
    molalarCiz();

    document.getElementById('fg_aralik_ekle').addEventListener('click', function() {
        ayarlar.aralilar.push([100, 150]);
        araliklarCiz();
    });

    document.getElementById('fg_mola_ekle').addEventListener('click', function() {
        ayarlar.molalar.push(['02:00', '08:00']);
        molalarCiz();
    });

    document.getElementById('fg_ayarlar_btn').addEventListener('click', function() {
        panelAcik = !panelAcik;
        ayarlarPanel.style.display = panelAcik ? 'block' : 'none';
    });

    document.getElementById('fg_kapat').addEventListener('click', function() {
        panelAcik = false;
        ayarlarPanel.style.display = 'none';
    });

    document.getElementById('fg_kaydet').addEventListener('click', function() {
        ayarlar.scriptUrl = document.getElementById('fg_url').value;
        ayarlar.tiklamaMin = parseInt(document.getElementById('fg_tikMin').value);
        ayarlar.tiklamaMax = parseInt(document.getElementById('fg_tikMax').value);
        ayarlar.tgToken = document.getElementById('fg_tg_token').value;
        ayarlar.tgChatId = document.getElementById('fg_tg_chatid').value;
        gmSet('scriptUrl', ayarlar.scriptUrl);
        gmSet('tiklamaMin', ayarlar.tiklamaMin);
        gmSet('tiklamaMax', ayarlar.tiklamaMax);
        gmSet('aralilar', ayarlar.aralilar);
        gmSet('molalar', ayarlar.molalar);
        gmSet('tgToken', ayarlar.tgToken);
        gmSet('tgChatId', ayarlar.tgChatId);
        ayarlarPanel.style.display = 'none';
        panelAcik = false;
        durumGuncelle('✅ Ayarlar kaydedildi!');
    });

    document.getElementById('fg_baslatdurdur').addEventListener('click', function() {
        durduruldu = !durduruldu;
        ayarlar.aktif = !durduruldu;
        gmSet('aktif', ayarlar.aktif);
        this.textContent = durduruldu ? '▶ Başlat' : '⏹ Durdur';
        this.style.background = durduruldu ? '#080' : '#c00';
        if (!durduruldu) {
            location.reload();
        } else {
            durumGuncelle('⏹ Durduruldu');
            if (sayacInterval) clearInterval(sayacInterval);
            sayacGuncelle('--');
        }
    });

    function durumGuncelle(mesaj) {
        const el = document.getElementById('fg_durum');
        if (el) el.textContent = mesaj;
    }

    function sayacGuncelle(deger) {
        const el = document.getElementById('fg_sayac');
        if (el) el.textContent = deger;
    }

    function sayacBaslat(toplamMs) {
        if (sayacInterval) clearInterval(sayacInterval);
        let kalan = Math.floor(toplamMs / 1000);
        sayacGuncelle(kalan + ' sn');
        sayacInterval = setInterval(function() {
            if (durduruldu) { clearInterval(sayacInterval); return; }
            kalan--;
            sayacGuncelle(kalan + ' sn');
            if (kalan <= 0) clearInterval(sayacInterval);
        }, 1000);
    }

    function molaKontrolBaslat() {
        if (molaKontrolInterval) clearInterval(molaKontrolInterval);
        molaKontrolInterval = setInterval(function() {
            if (!moladaMi()) {
                clearInterval(molaKontrolInterval);
                durumGuncelle('☕ Mola bitti, devam ediliyor...');
                setTimeout(() => location.reload(), 2000);
            } else {
                const kalan = molaBitisineKalanDakika();
                durumGuncelle(`☕ Mola - ${kalan} dakika kaldı`);
                sayacGuncelle(kalan + ' dk');
            }
        }, 30000);
    }

    if (durduruldu) {
        durumGuncelle('⏹ Durduruldu');
        return;
    }

    if (moladaMi()) {
        const kalan = molaBitisineKalanDakika();
        durumGuncelle(`☕ Mola - ${kalan} dakika kaldı`);
        sayacGuncelle(kalan + ' dk');
        molaKontrolBaslat();
        return;
    }

    function loadScript(url) {
        return new Promise((resolve, reject) => {
            const s = document.createElement('script');
            s.src = url;
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    setTimeout(function() {

        if (botKorumaVar()) { durumGuncelle('⚠️ Bot koruma! Durdu.'); return; }

        durumGuncelle('FarmGod yükleniyor...');

        loadScript(ayarlar.scriptUrl).then(function() {

            durumGuncelle('Popup bekleniyor...');

            setTimeout(function() {

                let deneme = 0;
                const bekle = setInterval(function() {

                    if (durduruldu || botKorumaVar() || moladaMi()) {
                        clearInterval(bekle);
                        if (moladaMi()) {
                            const kalan = molaBitisineKalanDakika();
                            durumGuncelle(`☕ Mola - ${kalan} dakika kaldı`);
                            sayacGuncelle(kalan + ' dk');
                            molaKontrolBaslat();
                        } else {
                            durumGuncelle(botKorumaVar() ? '⚠️ Bot koruma! Durdu.' : '⏹ Durduruldu');
                        }
                        return;
                    }

                    const buton = document.querySelector("#popup_box_FarmGod > div > div > input");
                    if (buton) {
                        clearInterval(bekle);
                        buton.click();
                        durumGuncelle('Plan farms tıklandı...');

                        const aButonBekle = setInterval(function() {

                            if (durduruldu || botKorumaVar() || moladaMi()) {
                                clearInterval(aButonBekle);
                                if (moladaMi()) {
                                    const kalan = molaBitisineKalanDakika();
                                    durumGuncelle(`☕ Mola - ${kalan} dakika kaldı`);
                                    sayacGuncelle(kalan + ' dk');
                                    molaKontrolBaslat();
                                } else {
                                    durumGuncelle(botKorumaVar() ? '⚠️ Bot koruma! Durdu.' : '⏹ Durduruldu');
                                }
                                return;
                            }

                            const ilkButon = document.querySelector("#content_value > div.vis.farmGodContent > table > tbody > tr > td:nth-child(4) > a");
                            if (ilkButon) {
                                clearInterval(aButonBekle);
                                let tikSayisi = 0;
                                function tikla() {
                                    if (durduruldu || botKorumaVar() || moladaMi()) {
                                        if (moladaMi()) {
                                            const kalan = molaBitisineKalanDakika();
                                            durumGuncelle(`☕ Mola - ${kalan} dakika kaldı`);
                                            sayacGuncelle(kalan + ' dk');
                                            molaKontrolBaslat();
                                        } else {
                                            durumGuncelle(botKorumaVar() ? '⚠️ Bot koruma! Durdu.' : '⏹ Durduruldu');
                                        }
                                        return;
                                    }
                                    const b = document.querySelector("#content_value > div.vis.farmGodContent > table > tbody > tr > td:nth-child(4) > a");
                                    if (b) {
                                        tikSayisi++;
                                        b.click();
                                        durumGuncelle(`✅ ${tikSayisi}. köye saldırıldı`);
                                        const bekleMs = Math.floor(Math.random() * (ayarlar.tiklamaMax - ayarlar.tiklamaMin + 1)) + ayarlar.tiklamaMin;
                                        setTimeout(tikla, bekleMs);
                                    } else {
                                        durumGuncelle(`✅ Bitti! ${tikSayisi} köye saldırıldı`);
                                    }
                                }
                                tikla();
                            }
                        }, 500);

                    } else {
                        deneme++;
                        if (deneme > 40) { clearInterval(bekle); durumGuncelle('❌ Popup bulunamadı.'); }
                    }
                }, 500);

            }, 5000);

        }).catch(function() {
            durumGuncelle('❌ Script yüklenemedi.');
        });

        function rastgele(min, max) {
            return Math.floor(Math.random() * (max - min + 1) + min) * 1000;
        }

        function karistir(dizi) {
            let arr = [...dizi];
            for (let i = arr.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [arr[i], arr[j]] = [arr[j], arr[i]];
            }
            return arr;
        }

        function rastgeleTurSec(dizi) {
            const turSayisi = Math.floor(Math.random() * 4) + 1;
            const karisik = karistir(dizi);
            return karisik.slice(0, turSayisi);
        }

        let secilenAralilar = rastgeleTurSec(ayarlar.aralilar);
        let index = 0;

        function siradakiYenile() {
            if (durduruldu) { durumGuncelle('⏹ Durduruldu'); return; }
            if (botKorumaVar()) { durumGuncelle('⚠️ Bot koruma! Durdu.'); return; }
            if (moladaMi()) {
                const kalan = molaBitisineKalanDakika();
                durumGuncelle(`☕ Mola - ${kalan} dakika kaldı`);
                sayacGuncelle(kalan + ' dk');
                molaKontrolBaslat();
                return;
            }
            if (index >= secilenAralilar.length) {
                durumGuncelle('🔄 Sayfa yenileniyor...');
                sayacGuncelle('--');
                location.reload();
                return;
            }
            const [min, max] = secilenAralilar[index];
            const sure = rastgele(min, max);
            durumGuncelle(`⏳ Yenileme bekleniyor (${min}-${max}sn)`);
            sayacBaslat(sure);
            setTimeout(() => {
                index++;
                siradakiYenile();
            }, sure);
        }

        siradakiYenile();

    }, 3000);

})();
