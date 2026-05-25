// ==UserScript==
// @name         FarmGod Bot v3
// @namespace    https://higamy.github.io/TW/
// @version      3.0
// @description  FarmGod Bot - Uzaktan kontrol, istatistik, gunluk rapor, bot koruma yeniden deneme
// @author       FarmGod
// @include        https://*.tribalwars.*/game.php*screen=am_farm*
// @match        https://*.die-staemme.*/game.php*screen=am_farm*
// @include         https://*.klanlar.*/game.php*screen=am_farm*
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_xmlhttpRequest
// @connect      api.telegram.org
// @require      https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js
// @run-at       document-idle
// ==/UserScript==

(function() {
    'use strict';

    if (!window.location.href.includes('screen=am_farm')) return;

    // ================================================================
    // GM YARDIMCILARI
    // ================================================================
    function gmGet(key, def) {
        const val = GM_getValue('FarmGod_' + key, null);
        if (val === null) return def;
        try { return JSON.parse(val); } catch { return val; }
    }
    function gmSet(key, value) {
        GM_setValue('FarmGod_' + key, JSON.stringify(value));
    }

    // ================================================================
    // AYARLAR
    // ================================================================
    let ayarlar = {
        scriptUrl:  gmGet('scriptUrl',  'https://higamy.github.io/TW/Scripts/Approved/FarmGodCopy.js'),
        tiklamaMin: gmGet('tiklamaMin', 500),
        tiklamaMax: gmGet('tiklamaMax', 1000),
        aralilar:   gmGet('aralilar',   [[100,150],[150,200],[200,250],[250,300],[300,350]]),
        aktif:      gmGet('aktif',      true),
        molalar:    gmGet('molalar',    [
            { bas: '02:00', bitis: '08:00', gunler: [1,2,3,4,5] },
            { bas: '00:00', bitis: '10:00', gunler: [0,6] }
        ]),
        tgToken:    gmGet('tgToken',    ''),
        tgChatId:   gmGet('tgChatId',  ''),
        raporSaati: gmGet('raporSaati', '20:00') // gunluk rapor UTC saati
    };

    // Eski mola formatından yeni formata gec
    if (ayarlar.molalar.length > 0 && Array.isArray(ayarlar.molalar[0])) {
        ayarlar.molalar = ayarlar.molalar.map(function(m) {
            return { bas: m[0], bitis: m[1], gunler: [0,1,2,3,4,5,6] };
        });
        gmSet('molalar', ayarlar.molalar);
    }

    // ================================================================
    // ISTATISTIK — GM'de kalici olarak tutulur, her gun sifirlanir
    // ================================================================
    function bugunTarih() {
        const d = new Date();
        return d.getUTCFullYear() + '-' +
               String(d.getUTCMonth()+1).padStart(2,'0') + '-' +
               String(d.getUTCDate()).padStart(2,'0');
    }

    function istatistikYukle() {
        const kayit = gmGet('istatistik', null);
        if (!kayit || kayit.tarih !== bugunTarih()) {
            return { tarih: bugunTarih(), saldirildi: 0, tahminKaynak: 0, yenileme: 0, botKorumaSayisi: 0, scriptHataSayisi: 0 };
        }
        return kayit;
    }

    let stat = istatistikYukle();

    function statKaydet() { gmSet('istatistik', stat); }

    function statSaldirildi() { stat.saldirildi++; stat.tahminKaynak += Math.floor(Math.random()*800 + 200); statKaydet(); }
    function statYenileme()   { stat.yenileme++;   statKaydet(); }
    function statBotKoruma()  { stat.botKorumaSayisi++; statKaydet(); }
    function statScriptHata() { stat.scriptHataSayisi++; statKaydet(); }

    // ================================================================
    // DURUM DEGISKENLERI
    // ================================================================
    let durduruldu = !ayarlar.aktif;
    let sayacInterval       = null;
    let molaKontrolInterval = null;
    let tgKontrolInterval   = null;
    let raporInterval       = null;
    let panelAcik           = false;
    let botKorumaMessajAtildi      = false;
    let molaBaslangicBildirimiAtildi = false;
    let botKorumaYenidenDenemeSayisi = 0;
    const BOT_KORUMA_MAX_DENEME      = 3;

    // ================================================================
    // ZAMAN YARDIMCILARI
    // ================================================================
    function oyunSaati() {
        const now = new Date();
        return now.getUTCHours().toString().padStart(2,'0') + ':' + now.getUTCMinutes().toString().padStart(2,'0');
    }
    function utcGun() { return new Date().getUTCDay(); }
    function saateDakika(saat) {
        const [h, m] = saat.split(':').map(Number);
        return h * 60 + m;
    }
    function molaAktifMi(mola) {
        if (!mola.gunler.includes(utcGun())) return false;
        const simdi = saateDakika(oyunSaati());
        const b = saateDakika(mola.bas), bt = saateDakika(mola.bitis);
        if (b <= bt) return simdi >= b && simdi < bt;
        return simdi >= b || simdi < bt;
    }
    function moladaMi() { return ayarlar.molalar.some(molaAktifMi); }
    function molaBitisineKalanDakika() {
        const simdi = saateDakika(oyunSaati());
        let enAz = Infinity;
        for (const mola of ayarlar.molalar) {
            if (!molaAktifMi(mola)) continue;
            const bt = saateDakika(mola.bitis);
            const kalan = bt > simdi ? bt - simdi : (1440 - simdi + bt);
            if (kalan < enAz) enAz = kalan;
        }
        return enAz === Infinity ? 0 : enAz;
    }
    function aktifMolaIndex() {
        for (let i = 0; i < ayarlar.molalar.length; i++) {
            if (molaAktifMi(ayarlar.molalar[i])) return i;
        }
        return -1;
    }
    function molaSureDegistir(deltaMin) {
        const idx = aktifMolaIndex();
        if (idx === -1) { durumGuncelle('Aktif mola yok!'); return; }
        let bt = saateDakika(ayarlar.molalar[idx].bitis) + deltaMin;
        if (bt < 0) bt = 0; if (bt >= 1440) bt = 1439;
        const yeni = Math.floor(bt/60).toString().padStart(2,'0') + ':' + (bt%60).toString().padStart(2,'0');
        ayarlar.molalar[idx].bitis = yeni;
        gmSet('molalar', ayarlar.molalar);
        const isaret = deltaMin > 0 ? '+' : '';
        durumGuncelle('Mola bitis: ' + yeni + ' (' + isaret + deltaMin + ' dk)');
        telegramMesajAt('⏱ Mola suresi guncellendi.\nYeni bitis: ' + yeni + ' UTC (' + isaret + deltaMin + ' dk)');
    }
    window._fgMolaDegistir = molaSureDegistir;

    // ================================================================
    // TELEGRAM
    // ================================================================
    function telegramMesajAt(mesaj, callback) {
        if (!ayarlar.tgToken || !ayarlar.tgChatId) return;
        GM_xmlhttpRequest({
            method: 'POST',
            url: 'https://api.telegram.org/bot' + ayarlar.tgToken + '/sendMessage',
            headers: { 'Content-Type': 'application/json' },
            data: JSON.stringify({ chat_id: ayarlar.tgChatId, text: mesaj, parse_mode: 'HTML' }),
            onload: callback || function() {}
        });
    }

    function telegramFotoGonder(blob, caption) {
        if (!ayarlar.tgToken || !ayarlar.tgChatId) return;
        const reader = new FileReader();
        reader.onload = function() {
            const boundary = '----TGBoundary' + Date.now();
            const uint8 = new Uint8Array(reader.result);
            const enc = new TextEncoder();
            const parts = [
                enc.encode('--' + boundary + '\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n' + ayarlar.tgChatId + '\r\n'),
                enc.encode('--' + boundary + '\r\nContent-Disposition: form-data; name="caption"\r\n\r\n' + caption + '\r\n'),
                enc.encode('--' + boundary + '\r\nContent-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n'),
                enc.encode('--' + boundary + '\r\nContent-Disposition: form-data; name="photo"; filename="screenshot.png"\r\nContent-Type: image/png\r\n\r\n'),
                uint8,
                enc.encode('\r\n--' + boundary + '--\r\n')
            ];
            const totalLen = parts.reduce(function(s, p) { return s + p.length; }, 0);
            const body = new Uint8Array(totalLen);
            let offset = 0;
            parts.forEach(function(p) { body.set(p, offset); offset += p.length; });
            GM_xmlhttpRequest({
                method: 'POST',
                url: 'https://api.telegram.org/bot' + ayarlar.tgToken + '/sendPhoto',
                headers: { 'Content-Type': 'multipart/form-data; boundary=' + boundary },
                data: body.buffer, binary: true
            });
        };
        reader.readAsArrayBuffer(blob);
    }

    function ekranGoruntusuAlVeGonder(caption) {
        if (!ayarlar.tgToken || !ayarlar.tgChatId) return;
        if (typeof html2canvas === 'undefined') { telegramMesajAt(caption); return; }
        html2canvas(document.body, { useCORS: true, allowTaint: true, scale: 1, logging: false })
            .then(function(canvas) {
                canvas.toBlob(function(blob) {
                    if (blob) telegramFotoGonder(blob, caption);
                    else telegramMesajAt(caption);
                }, 'image/png');
            })
            .catch(function() { telegramMesajAt(caption); });
    }

    // ================================================================
    // GUNLUK RAPOR
    // ================================================================
    function gunlukRaporGonder() {
        const s = istatistikYukle();
        const mesaj =
            '📊 <b>FarmGod Gunluk Rapor</b>\n' +
            '📅 Tarih: ' + s.tarih + '\n' +
            '⚔️ Saldirildi: ' + s.saldirildi + ' koy\n' +
            '💰 Tahmini kaynak: ' + s.tahminKaynak.toLocaleString() + '\n' +
            '🔄 Sayfa yenileme: ' + s.yenileme + '\n' +
            '🛡️ Bot koruma: ' + s.botKorumaSayisi + ' kez\n' +
            '❌ Script hatasi: ' + s.scriptHataSayisi + ' kez\n' +
            '🕐 UTC: ' + oyunSaati();
        telegramMesajAt(mesaj);
    }

    // Rapor zamanlayicisi — her dakika kontrol et, saat eslesince gonder
    let raporAtildi = false;
    function raporZamanlamasiBaslat() {
        if (raporInterval) clearInterval(raporInterval);
        raporInterval = setInterval(function() {
            const simdi = oyunSaati();
            if (simdi === ayarlar.raporSaati) {
                if (!raporAtildi) { raporAtildi = true; gunlukRaporGonder(); }
            } else {
                raporAtildi = false;
            }
        }, 60000);
    }
    raporZamanlamasiBaslat();

    // ================================================================
    // TELEGRAM UZAKTAN KOMUT DİNLEME
    // /dur   → botu durdur
    // /baslat → botu baslat
    // /durum  → anlık durum raporu
    // /rapor  → istatistik raporu
    // ================================================================
    let sonGuncellemeMesajId = gmGet('tgSonMesajId', 0);

    function telegramKomutKontrol() {
        if (!ayarlar.tgToken || !ayarlar.tgChatId) return;
        GM_xmlhttpRequest({
            method: 'GET',
            url: 'https://api.telegram.org/bot' + ayarlar.tgToken + '/getUpdates?offset=' + (sonGuncellemeMesajId + 1) + '&limit=5&timeout=0',
            onload: function(resp) {
                try {
                    const data = JSON.parse(resp.responseText);
                    if (!data.ok || !data.result.length) return;
                    data.result.forEach(function(update) {
                        if (update.update_id <= sonGuncellemeMesajId) return;
                        sonGuncellemeMesajId = update.update_id;
                        gmSet('tgSonMesajId', sonGuncellemeMesajId);
                        const msg = update.message;
                        if (!msg || !msg.text) return;
                        // Sadece ayarlanan chat'ten gelen komutlari islet
                        if (String(msg.chat.id) !== String(ayarlar.tgChatId)) return;
                        const komut = msg.text.trim().toLowerCase();
                        if (komut === '/dur' || komut === '/durdur') {
                            if (!durduruldu) {
                                durduruldu = true; ayarlar.aktif = false; gmSet('aktif', false);
                                const btn = document.getElementById('fg_baslatdurdur');
                                if (btn) { btn.textContent = 'Baslat'; btn.style.background = '#080'; }
                                durumGuncelle('Durduruldu (Telegram)');
                                telegramMesajAt('⏹ Bot durduruldu.');
                            } else {
                                telegramMesajAt('ℹ️ Bot zaten durmus durumda.');
                            }
                        } else if (komut === '/baslat') {
                            if (durduruldu) {
                                telegramMesajAt('▶️ Bot baslatiliyor, sayfa yenileniyor...');
                                durduruldu = false; ayarlar.aktif = true; gmSet('aktif', true);
                                setTimeout(function() { location.reload(); }, 1500);
                            } else {
                                telegramMesajAt('ℹ️ Bot zaten calisiyor.');
                            }
                        } else if (komut === '/durum') {
                            const durum = durduruldu ? 'Durduruldu' : (moladaMi() ? 'Molada' : 'Aktif');
                            telegramMesajAt(
                                '🤖 <b>FarmGod Durum</b>\n' +
                                'Durum: ' + durum + '\n' +
                                'UTC: ' + oyunSaati() + '\n' +
                                'Bugun saldirildi: ' + stat.saldirildi + ' koy\n' +
                                'Tahmini kaynak: ' + stat.tahminKaynak.toLocaleString()
                            );
                        } else if (komut === '/rapor') {
                            gunlukRaporGonder();
                            } else if (komut === '/ekran') {
    ekranGoruntusuAlVeGonder(
        '📸 Ekran Goruntusu\nUTC: ' + oyunSaati() + '\nURL: ' + window.location.href
    );
                        } else if (komut === '/yardim' || komut === '/help') {
                            telegramMesajAt(
    '📖 <b>FarmGod Komutlar</b>\n' +
    '/dur — Botu durdur\n' +
    '/baslat — Botu baslat\n' +
    '/durum — Anlık durum\n' +
    '/rapor — Istatistik raporu\n' +
    '/ekran — Ekran goruntusu al\n' +  // ← bu satır
    '/yardim — Bu mesaj'
);
                        }
                    });
                } catch(e) { /* parse hatasi yoksay */ }
            }
        });
    }

    function tgKomutDinlemeyiBaslat() {
        if (tgKontrolInterval) clearInterval(tgKontrolInterval);
        tgKontrolInterval = setInterval(telegramKomutKontrol, 15000); // her 15 sn
        telegramKomutKontrol(); // ilk kontrol hemen
    }
    tgKomutDinlemeyiBaslat();

    // ================================================================
    // BOT KORUMA — yeniden deneme mantigi
    // ================================================================
    function botKorumaVar() {
        const var_ = document.querySelector("#botprotection_quest") !== null ||
                     document.querySelector(".bot-protection-row") !== null;
        if (var_ && !botKorumaMessajAtildi) {
            botKorumaMessajAtildi = true;
            statBotKoruma();
            botKorumaYenidenDenemeSayisi++;
            const caption =
                '🛡 Bot Koruma Algilandi! (' + botKorumaYenidenDenemeSayisi + '/' + BOT_KORUMA_MAX_DENEME + ')\n' +
                'URL: ' + window.location.href + '\nUTC: ' + oyunSaati();
            ekranGoruntusuAlVeGonder(caption);

            if (botKorumaYenidenDenemeSayisi < BOT_KORUMA_MAX_DENEME) {
                // 60 saniye bekle, yeniden dene
                durumGuncelle('Bot koruma! 60sn sonra yeniden deneniyor... (' + botKorumaYenidenDenemeSayisi + '/' + BOT_KORUMA_MAX_DENEME + ')');
                let geriSayim = 60;
                sayacGuncelle(geriSayim + ' sn');
                const gs = setInterval(function() {
                    geriSayim--;
                    sayacGuncelle(geriSayim + ' sn');
                    if (geriSayim <= 0) {
                        clearInterval(gs);
                        botKorumaMessajAtildi = false;
                        location.reload();
                    }
                }, 1000);
            } else {
                // Max deneme asıldı, tamamen dur
                durumGuncelle('Bot koruma! Max deneme asildi. Durdu.');
                telegramMesajAt(
                    '❌ Bot Koruma max deneme (' + BOT_KORUMA_MAX_DENEME + ') asildi!\n' +
                    'Bot tamamen durduruldu. Manuel mudahale gerekiyor.\nUTC: ' + oyunSaati()
                );
                durduruldu = true; ayarlar.aktif = false; gmSet('aktif', false);
            }
        }
        return var_;
    }

    // ================================================================
    // SCRIPT / SAYFA HATASI ALARMİ
    // ================================================================
    window.addEventListener('error', function(e) {
        statScriptHata();
        telegramMesajAt(
            '❌ Script Hatasi!\n' +
            'Mesaj: ' + (e.message || 'bilinmiyor') + '\n' +
            'URL: ' + window.location.href + '\nUTC: ' + oyunSaati()
        );
    });

    // ================================================================
    // UI — ANA PANEL
    // ================================================================
    const GUN_KISALTMA = ['Paz','Pzt','Sal','Çar','Per','Cum','Cmt'];

    const panel = document.createElement('div');
    panel.style.cssText = [
        'position:fixed','bottom:20px','right:20px',
        'background:rgba(20,20,20,0.95)','color:#fff',
        'padding:12px 18px','border-radius:10px',
        'font-size:13px','font-family:monospace',
        'z-index:99999','min-width:250px',
        'border:1px solid #f90',
        'box-shadow:0 0 10px rgba(255,150,0,0.3)'
    ].join(';');
    panel.innerHTML =
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">' +
            '<span style="color:#f90;font-weight:bold;font-size:15px;">FarmGod v3</span>' +
            '<span id="fg_oyunsaati" style="color:#aaa;font-size:11px;">UTC --:--</span>' +
        '</div>' +
        '<div id="fg_durum" style="margin-bottom:4px;">Baslatiliyor...</div>' +
        '<div id="fg_sayac" style="font-size:26px;text-align:center;margin:6px 0;color:#0f0;">--</div>' +
        // Istatistik satiri
        '<div id="fg_stat" style="font-size:11px;color:#aaa;text-align:center;margin-bottom:6px;">⚔️ 0 koy | 💰 0</div>' +
        // Mola kontrol butonlari
        '<div id="fg_mola_kontrol" style="display:none;text-align:center;margin-bottom:8px;">' +
            '<span style="color:#aaa;font-size:11px;">Mola suresini degistir:</span><br>' +
            '<div style="display:flex;gap:4px;justify-content:center;margin-top:4px;">' +
                '<button onclick="window._fgMolaDegistir(-30)" style="padding:3px 8px;background:#555;border:none;color:#fff;border-radius:4px;cursor:pointer;font-size:11px;">-30dk</button>' +
                '<button onclick="window._fgMolaDegistir(-15)" style="padding:3px 8px;background:#555;border:none;color:#fff;border-radius:4px;cursor:pointer;font-size:11px;">-15dk</button>' +
                '<button onclick="window._fgMolaDegistir(+15)" style="padding:3px 8px;background:#080;border:none;color:#fff;border-radius:4px;cursor:pointer;font-size:11px;">+15dk</button>' +
                '<button onclick="window._fgMolaDegistir(+30)" style="padding:3px 8px;background:#080;border:none;color:#fff;border-radius:4px;cursor:pointer;font-size:11px;">+30dk</button>' +
            '</div>' +
        '</div>' +
        '<div style="display:flex;gap:6px;margin-top:6px;">' +
            '<button id="fg_baslatdurdur" style="flex:1;padding:6px;border-radius:6px;border:none;cursor:pointer;font-weight:bold;background:' + (ayarlar.aktif ? '#c00' : '#080') + ';color:#fff;">' +
                (ayarlar.aktif ? 'Durdur' : 'Baslat') +
            '</button>' +
            '<button id="fg_rapor_btn" style="padding:6px 10px;border-radius:6px;border:none;cursor:pointer;background:#336;color:#fff;font-size:12px;">📊</button>' +
            '<button id="fg_ayarlar_btn" style="flex:1;padding:6px;border-radius:6px;border:none;cursor:pointer;font-weight:bold;background:#555;color:#fff;">Ayarlar</button>' +
        '</div>';
    document.body.appendChild(panel);

    setInterval(function() {
        const el = document.getElementById('fg_oyunsaati');
        if (el) el.textContent = 'UTC ' + oyunSaati() + ' ' + GUN_KISALTMA[utcGun()];
        // Istatistik guncelle
        const sel = document.getElementById('fg_stat');
        if (sel) sel.textContent = '⚔️ ' + stat.saldirildi + ' koy | 💰 ' + stat.tahminKaynak.toLocaleString();
    }, 1000);

    document.getElementById('fg_rapor_btn').addEventListener('click', function() {
        gunlukRaporGonder();
        durumGuncelle('Rapor Telegram\'a gonderildi!');
    });

    // ================================================================
    // AYARLAR PANELi
    // ================================================================
    const ayarlarPanel = document.createElement('div');
    ayarlarPanel.style.cssText = [
        'position:fixed','bottom:140px','right:20px',
        'background:rgba(20,20,20,0.97)','color:#fff',
        'padding:16px','border-radius:10px',
        'font-size:13px','font-family:monospace',
        'z-index:99999','width:340px',
        'border:1px solid #f90',
        'box-shadow:0 0 10px rgba(255,150,0,0.3)',
        'display:none','max-height:80vh','overflow-y:auto'
    ].join(';');

    ayarlarPanel.innerHTML =
        '<div style="color:#f90;font-weight:bold;margin-bottom:12px;font-size:14px;">Ayarlar</div>' +

        '<div style="margin-bottom:10px;">' +
            '<label style="color:#aaa;">FarmGod Script URL</label><br>' +
            '<input id="fg_url" type="text" value="' + ayarlar.scriptUrl + '" style="width:100%;padding:5px;margin-top:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;box-sizing:border-box;">' +
        '</div>' +

        '<div style="margin-bottom:10px;">' +
            '<label style="color:#aaa;">Tiklama Hizi (ms)</label>' +
            '<div style="display:flex;gap:8px;margin-top:4px;align-items:center;">' +
                '<input id="fg_tikMin" type="number" value="' + ayarlar.tiklamaMin + '" style="width:80px;padding:5px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;">' +
                '<span>-</span>' +
                '<input id="fg_tikMax" type="number" value="' + ayarlar.tiklamaMax + '" style="width:80px;padding:5px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;">' +
                '<span style="color:#aaa;">ms</span>' +
            '</div>' +
        '</div>' +

        '<div style="margin-bottom:10px;">' +
            '<label style="color:#aaa;">Yenileme Araliklari (sn)</label>' +
            '<div id="fg_aralilar_list" style="margin-top:6px;"></div>' +
            '<button id="fg_aralik_ekle" style="margin-top:6px;padding:4px 10px;background:#444;border:1px solid #888;color:#fff;border-radius:4px;cursor:pointer;">+ Ekle</button>' +
        '</div>' +

        '<div style="margin-bottom:10px;">' +
            '<label style="color:#aaa;font-weight:bold;">Mola Saatleri (UTC)</label>' +
            '<div id="fg_mola_list" style="margin-top:6px;"></div>' +
            '<button id="fg_mola_ekle" style="margin-top:6px;padding:4px 10px;background:#444;border:1px solid #888;color:#fff;border-radius:4px;cursor:pointer;">+ Mola Ekle</button>' +
        '</div>' +

        '<div style="margin-bottom:10px;">' +
            '<label style="color:#aaa;">Telegram Bot Token</label><br>' +
            '<input id="fg_tg_token" type="text" value="' + ayarlar.tgToken + '" placeholder="123456:ABC-DEF..." style="width:100%;padding:5px;margin-top:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;box-sizing:border-box;">' +
        '</div>' +

        '<div style="margin-bottom:10px;">' +
            '<label style="color:#aaa;">Telegram Chat ID</label><br>' +
            '<input id="fg_tg_chatid" type="text" value="' + ayarlar.tgChatId + '" placeholder="-100xxxxxxxxx" style="width:100%;padding:5px;margin-top:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;box-sizing:border-box;">' +
        '</div>' +

        '<div style="margin-bottom:10px;">' +
            '<label style="color:#aaa;">Gunluk Rapor Saati (UTC)</label><br>' +
            '<input id="fg_rapor_saati" type="time" value="' + ayarlar.raporSaati + '" style="padding:5px;margin-top:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;">' +
        '</div>' +

        '<div style="display:flex;gap:8px;margin-top:12px;">' +
            '<button id="fg_kaydet" style="flex:1;padding:8px;background:#f90;border:none;color:#000;font-weight:bold;border-radius:6px;cursor:pointer;">Kaydet</button>' +
            '<button id="fg_kapat" style="flex:1;padding:8px;background:#555;border:none;color:#fff;border-radius:6px;cursor:pointer;">Kapat</button>' +
        '</div>';
    document.body.appendChild(ayarlarPanel);

    function araliklarCiz() {
        const liste = document.getElementById('fg_aralilar_list');
        liste.innerHTML = '';
        ayarlar.aralilar.forEach(function(aralik, i) {
            const satir = document.createElement('div');
            satir.style.cssText = 'display:flex;gap:6px;margin-bottom:4px;align-items:center;';
            satir.innerHTML =
                '<input type="number" value="' + aralik[0] + '" data-i="' + i + '" data-j="0" style="width:70px;padding:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;">' +
                '<span>-</span>' +
                '<input type="number" value="' + aralik[1] + '" data-i="' + i + '" data-j="1" style="width:70px;padding:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;">' +
                '<span style="color:#aaa;">sn</span>' +
                '<button data-sil="' + i + '" style="padding:2px 8px;background:#900;border:none;color:#fff;border-radius:4px;cursor:pointer;">X</button>';
            liste.appendChild(satir);
        });
        liste.querySelectorAll('[data-sil]').forEach(function(btn) {
            btn.addEventListener('click', function() { ayarlar.aralilar.splice(parseInt(this.dataset.sil),1); araliklarCiz(); });
        });
        liste.querySelectorAll('input').forEach(function(inp) {
            inp.addEventListener('change', function() { ayarlar.aralilar[parseInt(this.dataset.i)][parseInt(this.dataset.j)] = parseInt(this.value); });
        });
    }

    function molalarCiz() {
        const liste = document.getElementById('fg_mola_list');
        liste.innerHTML = '';
        ayarlar.molalar.forEach(function(mola, i) {
            const satir = document.createElement('div');
            satir.style.cssText = 'background:#2a2a2a;border:1px solid #444;border-radius:6px;padding:8px;margin-bottom:8px;';
            let gunlerHTML = '<div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:6px;">';
            GUN_KISALTMA.forEach(function(g, gi) {
                const secili = mola.gunler.includes(gi);
                gunlerHTML += '<button data-mi="' + i + '" data-gi="' + gi + '" style="padding:2px 6px;border-radius:4px;border:none;cursor:pointer;font-size:11px;background:' + (secili ? '#f90' : '#444') + ';color:' + (secili ? '#000' : '#fff') + ';">' + g + '</button>';
            });
            gunlerHTML += '</div>';
            satir.innerHTML =
                '<div style="display:flex;gap:6px;align-items:center;">' +
                    '<input type="time" value="' + mola.bas + '" data-mi="' + i + '" data-mj="0" style="width:90px;padding:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;">' +
                    '<span>-</span>' +
                    '<input type="time" value="' + mola.bitis + '" data-mi="' + i + '" data-mj="1" style="width:90px;padding:4px;background:#333;border:1px solid #666;color:#fff;border-radius:4px;">' +
                    '<button data-msil="' + i + '" style="padding:2px 8px;background:#900;border:none;color:#fff;border-radius:4px;cursor:pointer;">X</button>' +
                '</div>' +
                '<div style="color:#888;font-size:11px;margin-top:4px;">Gecerli gunler:</div>' +
                gunlerHTML;
            liste.appendChild(satir);
        });
        liste.querySelectorAll('[data-msil]').forEach(function(btn) {
            btn.addEventListener('click', function() { ayarlar.molalar.splice(parseInt(this.dataset.msil),1); molalarCiz(); });
        });
        liste.querySelectorAll('input[type=time]').forEach(function(inp) {
            inp.addEventListener('change', function() {
                const mi = parseInt(this.dataset.mi), mj = parseInt(this.dataset.mj);
                if (mj === 0) ayarlar.molalar[mi].bas = this.value;
                else ayarlar.molalar[mi].bitis = this.value;
            });
        });
        liste.querySelectorAll('button[data-gi]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                const mi = parseInt(this.dataset.mi), gi = parseInt(this.dataset.gi);
                const idx = ayarlar.molalar[mi].gunler.indexOf(gi);
                if (idx === -1) ayarlar.molalar[mi].gunler.push(gi);
                else ayarlar.molalar[mi].gunler.splice(idx,1);
                molalarCiz();
            });
        });
    }

    araliklarCiz(); molalarCiz();

    document.getElementById('fg_aralik_ekle').addEventListener('click', function() { ayarlar.aralilar.push([100,150]); araliklarCiz(); });
    document.getElementById('fg_mola_ekle').addEventListener('click', function() { ayarlar.molalar.push({ bas:'02:00', bitis:'08:00', gunler:[1,2,3,4,5] }); molalarCiz(); });
    document.getElementById('fg_ayarlar_btn').addEventListener('click', function() { panelAcik = !panelAcik; ayarlarPanel.style.display = panelAcik ? 'block' : 'none'; });
    document.getElementById('fg_kapat').addEventListener('click', function() { panelAcik = false; ayarlarPanel.style.display = 'none'; });
    document.getElementById('fg_kaydet').addEventListener('click', function() {
        ayarlar.scriptUrl  = document.getElementById('fg_url').value;
        ayarlar.tiklamaMin = parseInt(document.getElementById('fg_tikMin').value);
        ayarlar.tiklamaMax = parseInt(document.getElementById('fg_tikMax').value);
        ayarlar.tgToken    = document.getElementById('fg_tg_token').value;
        ayarlar.tgChatId   = document.getElementById('fg_tg_chatid').value;
        ayarlar.raporSaati = document.getElementById('fg_rapor_saati').value;
        gmSet('scriptUrl',  ayarlar.scriptUrl);
        gmSet('tiklamaMin', ayarlar.tiklamaMin);
        gmSet('tiklamaMax', ayarlar.tiklamaMax);
        gmSet('aralilar',   ayarlar.aralilar);
        gmSet('molalar',    ayarlar.molalar);
        gmSet('tgToken',    ayarlar.tgToken);
        gmSet('tgChatId',   ayarlar.tgChatId);
        gmSet('raporSaati', ayarlar.raporSaati);
        ayarlarPanel.style.display = 'none'; panelAcik = false;
        durumGuncelle('Ayarlar kaydedildi!');
    });

    document.getElementById('fg_baslatdurdur').addEventListener('click', function() {
        durduruldu = !durduruldu; ayarlar.aktif = !durduruldu; gmSet('aktif', ayarlar.aktif);
        this.textContent = durduruldu ? 'Baslat' : 'Durdur';
        this.style.background = durduruldu ? '#080' : '#c00';
        if (!durduruldu) { location.reload(); }
        else { durumGuncelle('Durduruldu'); if (sayacInterval) clearInterval(sayacInterval); sayacGuncelle('--'); }
    });

    // ================================================================
    // UI YARDIMCILARI
    // ================================================================
    function durumGuncelle(mesaj) { const el = document.getElementById('fg_durum'); if (el) el.textContent = mesaj; }
    function sayacGuncelle(deger) { const el = document.getElementById('fg_sayac'); if (el) el.textContent = deger; }
    function molaKontrolGoster(goster) { const el = document.getElementById('fg_mola_kontrol'); if (el) el.style.display = goster ? 'block' : 'none'; }

    function sayacBaslat(toplamMs) {
        if (sayacInterval) clearInterval(sayacInterval);
        let kalan = Math.floor(toplamMs / 1000);
        sayacGuncelle(kalan + ' sn');
        sayacInterval = setInterval(function() {
            if (durduruldu) { clearInterval(sayacInterval); return; }
            kalan--; sayacGuncelle(kalan + ' sn');
            if (kalan <= 0) clearInterval(sayacInterval);
        }, 1000);
    }

    function molaKontrolBaslat() {
        molaKontrolGoster(true);
        if (!molaBaslangicBildirimiAtildi) {
            molaBaslangicBildirimiAtildi = true;
            const kalan = molaBitisineKalanDakika();
            const bitis = ayarlar.molalar[aktifMolaIndex()]?.bitis || '--';
            telegramMesajAt('💤 FarmGod Mola Basladi\nBitis: ' + bitis + ' UTC\nKalan: ~' + kalan + ' dk\nURL: ' + window.location.href);
        }
        if (molaKontrolInterval) clearInterval(molaKontrolInterval);
        molaKontrolInterval = setInterval(function() {
            if (!moladaMi()) {
                clearInterval(molaKontrolInterval);
                molaKontrolGoster(false);
                molaBaslangicBildirimiAtildi = false;
                telegramMesajAt('▶️ FarmGod Mola Bitti - Devam ediliyor\nUTC: ' + oyunSaati());
                durumGuncelle('Mola bitti, devam ediliyor...');
                setTimeout(function() { location.reload(); }, 2000);
            } else {
                const kalan = molaBitisineKalanDakika();
                durumGuncelle('Mola - ' + kalan + ' dakika kaldi');
                sayacGuncelle(kalan + ' dk');
            }
        }, 30000);
    }

    // ================================================================
    // BASLANGIC KONTROLLERI
    // ================================================================
    if (durduruldu) { durumGuncelle('Durduruldu'); return; }

    if (moladaMi()) {
        const kalan = molaBitisineKalanDakika();
        durumGuncelle('Mola - ' + kalan + ' dakika kaldi');
        sayacGuncelle(kalan + ' dk');
        molaKontrolBaslat();
        return;
    }

    // ================================================================
    // ANA BOT MANTIĞI
    // ================================================================
    function loadScript(url) {
        return new Promise(function(resolve, reject) {
            const s = document.createElement('script');
            s.src = url;
            s.onload = resolve;
            s.onerror = reject;
            document.head.appendChild(s);
        });
    }

    setTimeout(function() {

        if (botKorumaVar()) return;

        durumGuncelle('FarmGod yukleniyor...');

        loadScript(ayarlar.scriptUrl).then(function() {

            durumGuncelle('Popup bekleniyor...');

            setTimeout(function() {
                let deneme = 0;
                const bekle = setInterval(function() {
                    if (durduruldu || botKorumaVar() || moladaMi()) {
                        clearInterval(bekle);
                        if (moladaMi()) { const k = molaBitisineKalanDakika(); durumGuncelle('Mola - ' + k + ' dk'); sayacGuncelle(k + ' dk'); molaKontrolBaslat(); }
                        else if (!botKorumaVar()) durumGuncelle('Durduruldu');
                        return;
                    }
                    const buton = document.querySelector("#popup_box_FarmGod > div > div > input");
                    if (buton) {
                        clearInterval(bekle);
                        buton.click();
                        durumGuncelle('Plan farms tiklandi...');
                        const aButonBekle = setInterval(function() {
                            if (durduruldu || botKorumaVar() || moladaMi()) {
                                clearInterval(aButonBekle);
                                if (moladaMi()) { const k = molaBitisineKalanDakika(); durumGuncelle('Mola - ' + k + ' dk'); sayacGuncelle(k + ' dk'); molaKontrolBaslat(); }
                                else if (!botKorumaVar()) durumGuncelle('Durduruldu');
                                return;
                            }
                            const ilkButon = document.querySelector("#content_value > div.vis.farmGodContent > table > tbody > tr > td:nth-child(4) > a");
                            if (ilkButon) {
                                clearInterval(aButonBekle);
                                let tikSayisi = 0;
                                function tikla() {
                                    if (durduruldu || botKorumaVar() || moladaMi()) {
                                        if (moladaMi()) { const k = molaBitisineKalanDakika(); durumGuncelle('Mola - ' + k + ' dk'); sayacGuncelle(k + ' dk'); molaKontrolBaslat(); }
                                        else if (!botKorumaVar()) durumGuncelle('Durduruldu');
                                        return;
                                    }
                                    const b = document.querySelector("#content_value > div.vis.farmGodContent > table > tbody > tr > td:nth-child(4) > a");
                                    if (b) {
                                        tikSayisi++;
                                        b.click();
                                        statSaldirildi();
                                        durumGuncelle(tikSayisi + '. koye saldirildi');
                                        const bekleMs = Math.floor(Math.random() * (ayarlar.tiklamaMax - ayarlar.tiklamaMin + 1)) + ayarlar.tiklamaMin;
                                        setTimeout(tikla, bekleMs);
                                    } else {
                                        durumGuncelle('Bitti! ' + tikSayisi + ' koye saldirildi');
                                    }
                                }
                                tikla();
                            }
                        }, 500);
                    } else {
                        deneme++;
                        if (deneme > 40) { clearInterval(bekle); durumGuncelle('Popup bulunamadi.'); }
                    }
                }, 500);
            }, 5000);

        }).catch(function() {
            statScriptHata();
            durumGuncelle('Script yuklenemedi!');
            telegramMesajAt(
                '❌ FarmGod Script Yuklenemedi!\n' +
                'URL: ' + ayarlar.scriptUrl + '\n' +
                'Sayfa: ' + window.location.href + '\nUTC: ' + oyunSaati()
            );
            // 60sn sonra yeniden dene
            let gs = 60; sayacGuncelle(gs + ' sn');
            const retry = setInterval(function() {
                gs--; sayacGuncelle(gs + ' sn');
                if (gs <= 0) { clearInterval(retry); location.reload(); }
            }, 1000);
        });

        function rastgele(min, max) { return Math.floor(Math.random() * (max - min + 1) + min) * 1000; }
        function karistir(dizi) {
            let arr = dizi.slice();
            for (let i = arr.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i+1)); const t = arr[i]; arr[i] = arr[j]; arr[j] = t; }
            return arr;
        }
        function rastgeleTurSec(dizi) { return karistir(dizi).slice(0, Math.floor(Math.random()*4)+1); }

        let secilenAralilar = rastgeleTurSec(ayarlar.aralilar), index = 0;

        function siradakiYenile() {
            if (durduruldu) { durumGuncelle('Durduruldu'); return; }
            if (botKorumaVar()) return;
            if (moladaMi()) { const k = molaBitisineKalanDakika(); durumGuncelle('Mola - ' + k + ' dk'); sayacGuncelle(k + ' dk'); molaKontrolBaslat(); return; }
            if (index >= secilenAralilar.length) { statYenileme(); durumGuncelle('Sayfa yenileniyor...'); sayacGuncelle('--'); location.reload(); return; }
            const min = secilenAralilar[index][0], max = secilenAralilar[index][1];
            const sure = rastgele(min, max);
            durumGuncelle('Yenileme bekleniyor (' + min + '-' + max + 'sn)');
            sayacBaslat(sure);
            setTimeout(function() { index++; siradakiYenile(); }, sure);
        }
        siradakiYenile();

    }, 3000);

})();
