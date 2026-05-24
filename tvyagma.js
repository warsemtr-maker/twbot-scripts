// ==UserScript==
// @name         TribalWars Yağma Asistanı
// @namespace    https://tribalwars.com.tr/
// @version      5.0
// @description  Farm asistanı — şablon, asker, Telegram, ekran görüntüsü, rastgele tıklama
// @author       —
// @match        https://*.tribalwars.com.tr/game.php*
// @match        https://*.tribalwars.net/game.php*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_xmlhttpRequest
// @connect      api.telegram.org
// ==/UserScript==

(function () {
  'use strict';

  // ══════════════════════════════════════════════
  //  VARSAYILAN AYARLAR
  // ══════════════════════════════════════════════
  const VARSAYILAN = {
    tiklaMin:    369,
    tiklaMax:    976,
    yenileMin:   200,
    yenileMax:   389,
    calismaBas:  '08:00',
    calismaBit:  '23:30',
    sablon:      'a',
    telegramToken:  '',
    telegramChatId: '',
    spear:    0, sword:    0, axe:     0, archer: 0, spy:  0,
    light:    0, marcher:  0, heavy:   0, ram:    0, catapult: 0,
  };

  function cfg(key) {
    try { return GM_getValue(key, VARSAYILAN[key]); } catch (e) { return VARSAYILAN[key]; }
  }
  function ayarKaydet(key, val) {
    try { GM_setValue(key, val); } catch (e) {}
  }

  const rand  = (mn, mx) => Math.floor(Math.random() * (mx - mn + 1)) + mn;
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  // ══════════════════════════════════════════════
  //  LOG
  // ══════════════════════════════════════════════
  function log(msg) {
    const t  = new Date().toLocaleTimeString('tr-TR');
    const el = document.getElementById('tw-log');
    if (el) {
      const line = document.createElement('div');
      line.textContent = '[' + t + ']  ' + msg;
      el.appendChild(line);
      el.scrollTop = el.scrollHeight;
    }
    console.log('[TW-Bot] ' + msg);
  }

  // ══════════════════════════════════════════════
  //  TELEGRAM
  // ══════════════════════════════════════════════
  function telegramGonder(mesaj, base64Resim) {
    const token  = cfg('telegramToken').trim();
    const chatId = cfg('telegramChatId').trim();
    if (!token || !chatId) return;

    if (base64Resim) {
      // sendPhoto: multipart/form-data — base64'ü Blob'a çevir
      const byteStr = atob(base64Resim.split(',')[1]);
      const ab = new ArrayBuffer(byteStr.length);
      const ia = new Uint8Array(ab);
      for (let i = 0; i < byteStr.length; i++) ia[i] = byteStr.charCodeAt(i);
      const blob = new Blob([ab], { type: 'image/png' });

      const fd = new FormData();
      fd.append('chat_id', chatId);
      fd.append('caption', mesaj);
      fd.append('photo', blob, 'screenshot.png');

      GM_xmlhttpRequest({
        method: 'POST',
        url: 'https://api.telegram.org/bot' + token + '/sendPhoto',
        data: fd,
        onload: function (r) { log('Telegram foto gonderildi: ' + r.status); },
        onerror: function ()  { log('Telegram HATA (foto)'); },
      });
    } else {
      GM_xmlhttpRequest({
        method: 'POST',
        url: 'https://api.telegram.org/bot' + token + '/sendMessage',
        headers: { 'Content-Type': 'application/json' },
        data: JSON.stringify({ chat_id: chatId, text: mesaj, parse_mode: 'HTML' }),
        onload: function (r) { log('Telegram mesaj gonderildi: ' + r.status); },
        onerror: function ()  { log('Telegram HATA (mesaj)'); },
      });
    }
  }

  // ══════════════════════════════════════════════
  //  EKRAN GÖRÜNTÜSÜ (html2canvas)
  //  Sayfa yüklenince html2canvas CDN'den çekilir
  // ══════════════════════════════════════════════
  let _h2cYuklendi = false;

  function html2canvasYukle(cb) {
    if (_h2cYuklendi) { cb(); return; }
    const s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
    s.onload = function () { _h2cYuklendi = true; cb(); };
    s.onerror = function () { log('html2canvas yuklenemedi'); cb(); };
    document.head.appendChild(s);
  }

  function ekranGoruntusiAl(cb) {
    html2canvasYukle(function () {
      if (typeof html2canvas === 'undefined') { cb(null); return; }
      html2canvas(document.body, { scale: 0.6, useCORS: true, logging: false })
        .then(function (canvas) { cb(canvas.toDataURL('image/png')); })
        .catch(function () { cb(null); });
    });
  }

  // ══════════════════════════════════════════════
  //  RASTGELE TIKLAMA — buton sınırları içinde
  // ══════════════════════════════════════════════
  function rastgeleTikla(btn) {
    const rect    = btn.getBoundingClientRect();
    const padX    = Math.floor(rect.width  * 0.15);
    const padY    = Math.floor(rect.height * 0.15);
    const rndX    = rand(Math.floor(rect.left) + padX, Math.floor(rect.right)  - padX);
    const rndY    = rand(Math.floor(rect.top)  + padY, Math.floor(rect.bottom) - padY);

    // MouseEvent ile gerçek koordinatta tıkla
    const over  = new MouseEvent('mouseover',  { bubbles: true, clientX: rndX, clientY: rndY });
    const down  = new MouseEvent('mousedown',  { bubbles: true, clientX: rndX, clientY: rndY, button: 0 });
    const up    = new MouseEvent('mouseup',    { bubbles: true, clientX: rndX, clientY: rndY, button: 0 });
    const click = new MouseEvent('click',      { bubbles: true, clientX: rndX, clientY: rndY, button: 0 });

    btn.dispatchEvent(over);
    btn.dispatchEvent(down);
    btn.dispatchEvent(up);
    btn.dispatchEvent(click);
  }

  // ══════════════════════════════════════════════
  //  BIRIMLER
  // ══════════════════════════════════════════════
  const BIRIMLER = ['spear','sword','axe','archer','spy','light','marcher','heavy','ram','catapult'];

  function askerleriDoldur() {
    for (const birim of BIRIMLER) {
      const miktar = parseInt(cfg(birim), 10);
      if (miktar <= 0) continue;
      const inp = document.querySelector('input[name="units[' + birim + ']"]');
      if (inp) { inp.value = miktar; log('  ' + birim + ': ' + miktar); }
    }
  }

  // ══════════════════════════════════════════════
  //  ŞABLON BUTONLARINI BUL
  // ══════════════════════════════════════════════
  function sablonButonlariBul() {
    const sablon = cfg('sablon').toLowerCase();
    const butonlar = [];
    const harfler = ['a','b','c'];
    for (const harf of harfler) {
      if (!sablon.includes(harf)) continue;
      butonlar.push(
        ...document.querySelectorAll('a.farm_icon_' + harf),
        ...document.querySelectorAll('input[value="' + harf.toUpperCase() + '"]'),
        ...document.querySelectorAll('a[data-farmtype="' + harf + '"]'),
        ...document.querySelectorAll('.farm_icon_' + harf),
      );
    }
    return [...new Set(butonlar)];
  }

  function botKorumasiVarMi() {
    const metinler = ['bot protection', 'botprotection', 'captcha', 'dogrulama'];
    return metinler.some(m => document.body.innerText.toLowerCase().includes(m));
  }

  // ══════════════════════════════════════════════
  //  YAĞMA TURU
  // ══════════════════════════════════════════════
  async function yagmaTuru(turNo) {
    log('── TUR ' + turNo + ' ──');

    if (botKorumasiVarMi()) {
      log('BOT KORUMASI ALGILANDI!');
      const zaman = new Date().toLocaleTimeString('tr-TR');
      const mesaj = '<b>TW Bot Koruması!</b>\nSaat: ' + zaman + '\nTur: ' + turNo + '\nScript durduruldu.';

      ekranGoruntusiAl(function (base64) {
        telegramGonder(mesaj, base64);
      });

      durdur();
      return -1;
    }

    askerleriDoldur();

    const butonlar = sablonButonlariBul();
    if (butonlar.length === 0) {
      log('Buton bulunamadi. Sablon: [' + cfg('sablon').toUpperCase() + ']');
      return 0;
    }

    log(butonlar.length + ' buton bulundu. [' + cfg('sablon').toUpperCase() + ']');
    butonlar.sort(() => Math.random() - 0.5);

    let tiklanma = 0;
    for (const btn of butonlar) {
      if (!_calisıyor) break;
      await sleep(rand(cfg('tiklaMin'), cfg('tiklaMax')));
      try {
        rastgeleTikla(btn);
        tiklanma++;
        log('  OK (' + tiklanma + '/' + butonlar.length + ')');
      } catch (e) { log('  HATA: ' + e.message); }
      await sleep(rand(cfg('tiklaMin'), cfg('tiklaMax')));
    }

    log('Tur bitti: ' + tiklanma + ' tiklama.');
    return tiklanma;
  }

  // ══════════════════════════════════════════════
  //  ANA DÖNGÜ
  // ══════════════════════════════════════════════
  let _calisıyor = false;
  let _tur       = 0;
  let _toplam    = 0;
  let _timeoutId = null;

  async function baslat() {
    if (_calisıyor) return;
    _calisıyor = true;
    ayarlariKaydet();
    setButonDurum(true);
    gosterSekme('log');
    _tur = 0; _toplam = 0;
    log('Baslatildi. [' + cfg('sablon').toUpperCase() + ']');
    await dongu();
  }

  async function dongu() {
    if (!_calisıyor) return;
    if (!calismaSaatiMi()) {
      log('Mesai disi. ' + cfg('calismaBas') + ' bekleniyor...');
      _timeoutId = setTimeout(dongu, 60000);
      return;
    }
    _tur++;
    const sonuc = await yagmaTuru(_tur);
    if (sonuc === -1) return;
    _toplam += (sonuc || 0);
    const bekle = rand(cfg('yenileMin'), cfg('yenileMax'));
    log('Toplam: ' + _toplam + ' (' + _tur + ' tur) - ' + bekle + 'sn');
    _timeoutId = setTimeout(function () {
      if (_calisıyor) location.reload();
    }, bekle * 1000);
  }

  function durdur() {
    _calisıyor = false;
    if (_timeoutId) clearTimeout(_timeoutId);
    log('Durduruldu.');
    setButonDurum(false);
  }

  function setButonDurum(c) {
    const b = document.getElementById('tw-btn-baslat');
    const d = document.getElementById('tw-btn-durdur');
    if (!b || !d) return;
    b.disabled = c; d.disabled = !c;
    b.style.opacity = c ? '0.5' : '1';
    d.style.opacity = c ? '1'   : '0.5';
  }

  function saatDakika(s) { const p = s.split(':').map(Number); return p[0]*60+p[1]; }
  function calismaSaatiMi() {
    const now = new Date();
    const dk = now.getHours()*60+now.getMinutes();
    const b = saatDakika(cfg('calismaBas')), e = saatDakika(cfg('calismaBit'));
    return b<=e ? dk>=b&&dk<=e : dk>=b||dk<=e;
  }

  // ══════════════════════════════════════════════
  //  AYAR KAYDET / YÜKLE
  // ══════════════════════════════════════════════
  function ayarlariKaydet() {
    const sayisal = ['tiklaMin','tiklaMax','yenileMin','yenileMax'].concat(BIRIMLER);
    const metin   = ['calismaBas','calismaBit','sablon','telegramToken','telegramChatId'];
    for (const k of sayisal) {
      const el = document.getElementById('tw-cfg-' + k);
      if (el) ayarKaydet(k, parseInt(el.value,10)||0);
    }
    for (const k of metin) {
      const el = document.getElementById('tw-cfg-' + k);
      if (el) ayarKaydet(k, el.value);
    }
    log('Ayarlar kaydedildi.');
  }

  function ayarlariYukle() {
    const tumAnahtarlar = ['tiklaMin','tiklaMax','yenileMin','yenileMax',
      'calismaBas','calismaBit','sablon','telegramToken','telegramChatId'].concat(BIRIMLER);
    for (const k of tumAnahtarlar) {
      const el = document.getElementById('tw-cfg-' + k);
      if (el) el.value = cfg(k);
    }
  }

  function gosterSekme(id) {
    ['log','ayarlar','asker','telegram'].forEach(function (s) {
      const p = document.getElementById('tw-sekme-' + s);
      const t = document.getElementById('tw-tab-' + s);
      if (!p||!t) return;
      const aktif = s===id;
      p.style.display    = aktif ? 'block' : 'none';
      t.style.color      = aktif ? '#e8c87a' : '#888';
      t.style.borderBottom = aktif ? '2px solid #e8c87a' : '2px solid transparent';
    });
  }

  // ══════════════════════════════════════════════
  //  UI YARDIMCILARI
  // ══════════════════════════════════════════════
  function mkEl(tag, css, txt) {
    const e = document.createElement(tag);
    if (css) e.style.cssText = css;
    if (txt !== undefined) e.textContent = txt;
    return e;
  }
  function baslik(txt) {
    return mkEl('div','color:#e8c87a;font-size:10px;margin:10px 0 4px;letter-spacing:.5px', txt);
  }
  function inputSatiri(labelTxt, cfgKey, tip) {
    tip = tip||'number';
    const row = mkEl('div','display:flex;justify-content:space-between;align-items:center;margin-bottom:7px');
    const lbl = mkEl('label','color:#aaa;font-size:11px', labelTxt);
    lbl.htmlFor = 'tw-cfg-'+cfgKey;
    const inp = mkEl('input','width:90px;background:#111;border:1px solid #555;border-radius:3px;color:#e0e0e0;padding:3px 6px;font-family:monospace;font-size:11px;text-align:right');
    inp.type=tip; inp.id='tw-cfg-'+cfgKey; inp.value=cfg(cfgKey);
    row.appendChild(lbl); row.appendChild(inp); return row;
  }
  function textSatiri(labelTxt, cfgKey, placeholder) {
    const row = mkEl('div','display:flex;justify-content:space-between;align-items:center;margin-bottom:7px');
    const lbl = mkEl('label','color:#aaa;font-size:11px', labelTxt);
    lbl.htmlFor = 'tw-cfg-'+cfgKey;
    const inp = mkEl('input','width:130px;background:#111;border:1px solid #555;border-radius:3px;color:#e0e0e0;padding:3px 6px;font-family:monospace;font-size:10px');
    inp.type='text'; inp.id='tw-cfg-'+cfgKey; inp.value=cfg(cfgKey);
    if (placeholder) inp.placeholder=placeholder;
    row.appendChild(lbl); row.appendChild(inp); return row;
  }
  function selectSatiri(labelTxt, cfgKey, secenekler) {
    const row = mkEl('div','display:flex;justify-content:space-between;align-items:center;margin-bottom:7px');
    const lbl = mkEl('label','color:#aaa;font-size:11px', labelTxt);
    lbl.htmlFor = 'tw-cfg-'+cfgKey;
    const sel = mkEl('select','width:90px;background:#111;border:1px solid #555;border-radius:3px;color:#e0e0e0;padding:3px 4px;font-family:monospace;font-size:11px');
    sel.id='tw-cfg-'+cfgKey;
    for (const [val,txt] of secenekler) {
      const opt=document.createElement('option');
      opt.value=val; opt.textContent=txt;
      if (val===cfg(cfgKey)) opt.selected=true;
      sel.appendChild(opt);
    }
    row.appendChild(lbl); row.appendChild(sel); return row;
  }
  function kaydetBtn(ekSekmeyeDon) {
    ekSekmeyeDon = ekSekmeyeDon||'log';
    const btn = mkEl('button','width:100%;margin-top:10px;padding:6px;background:#1a3a4a;color:#7ad4e8;border:1px solid #2a6a8a;border-radius:4px;cursor:pointer;font-family:monospace;font-size:12px','💾 Kaydet');
    btn.addEventListener('click', function () { ayarlariKaydet(); gosterSekme(ekSekmeyeDon); });
    return btn;
  }

  // ══════════════════════════════════════════════
  //  ARAYÜZ
  // ══════════════════════════════════════════════
  function arayuzOlustur() {
    const panel = mkEl('div',[
      'position:fixed','bottom:16px','right:16px','z-index:99999',
      'width:300px','background:#1a1a1a','border:1px solid #555',
      'border-radius:8px','font-family:monospace','font-size:12px',
      'color:#ccc','box-shadow:0 4px 24px rgba(0,0,0,.7)','user-select:none'
    ].join(';'));
    panel.id='tw-bot-panel';

    // Başlık
    const header=mkEl('div','background:#2a2a2a;padding:8px 12px;border-radius:8px 8px 0 0;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #444;cursor:move');
    header.id='tw-drag';
    header.appendChild(mkEl('span','font-weight:600;color:#e8c87a','⚔ TW Yağma Bot'));
    header.appendChild(mkEl('span','font-size:10px;color:#666','v5.0'));

    // Sekme çubuğu (4 sekme — 2 satır)
    const tabBar=mkEl('div','display:flex;flex-wrap:wrap;background:#222;border-bottom:1px solid #444');
    const sekmeler=[
      ['log','📋 Log'],['ayarlar','⚙ Ayarlar'],
      ['asker','⚔ Asker'],['telegram','📨 Telegram'],
    ];
    for (const [id,txt] of sekmeler) {
      const tab=mkEl('div','flex:1;min-width:50%;box-sizing:border-box;text-align:center;padding:5px 0;cursor:pointer;font-size:11px;color:#888;border-bottom:2px solid transparent',txt);
      tab.id='tw-tab-'+id;
      tab.addEventListener('click', function(){gosterSekme(id);});
      tabBar.appendChild(tab);
    }

    // LOG
    const logPanel=mkEl('div','');
    logPanel.id='tw-sekme-log';
    const logDiv=mkEl('div','height:150px;overflow-y:auto;padding:8px 10px;line-height:1.6;color:#aaa;font-size:11px');
    logDiv.id='tw-log';
    logPanel.appendChild(logDiv);

    // AYARLAR
    const ayarPanel=mkEl('div','padding:10px 12px;display:none;max-height:250px;overflow-y:auto');
    ayarPanel.id='tw-sekme-ayarlar';
    ayarPanel.appendChild(baslik('TIKLAMA ARASI (ms)'));
    ayarPanel.appendChild(inputSatiri('Min','tiklaMin'));
    ayarPanel.appendChild(inputSatiri('Max','tiklaMax'));
    ayarPanel.appendChild(baslik('YENİLEME ARASI (sn)'));
    ayarPanel.appendChild(inputSatiri('Min','yenileMin'));
    ayarPanel.appendChild(inputSatiri('Max','yenileMax'));
    ayarPanel.appendChild(baslik('ÇALIŞMA SAATİ'));
    ayarPanel.appendChild(inputSatiri('Başlangıç','calismaBas','time'));
    ayarPanel.appendChild(inputSatiri('Bitiş','calismaBit','time'));
    ayarPanel.appendChild(baslik('ŞABLON'));
    ayarPanel.appendChild(selectSatiri('Şablon','sablon',[
      ['a','A'],['b','B'],['c','C'],
      ['ab','A + B'],['ac','A + C'],['bc','B + C'],['abc','A + B + C'],
    ]));
    ayarPanel.appendChild(kaydetBtn());

    // ASKER
    const askerPanel=mkEl('div','padding:10px 12px;display:none;max-height:250px;overflow-y:auto');
    askerPanel.id='tw-sekme-asker';
    askerPanel.appendChild(baslik('BİRİM SAYILARI (0 = şablon varsayılanı)'));
    const BIRIM_ISIMLER=[
      ['spear','Mızrakçı'],['sword','Kılıçlı'],['axe','Baltacı'],
      ['archer','Okçu'],['spy','Casus'],['light','Hafif Süvari'],
      ['marcher','Okçu Süvari'],['heavy','Ağır Süvari'],
      ['ram','Koçbaşı'],['catapult','Mancınık'],
    ];
    for (const [key,isim] of BIRIM_ISIMLER) askerPanel.appendChild(inputSatiri(isim,key));
    askerPanel.appendChild(kaydetBtn());

    // TELEGRAM
    const telPanel=mkEl('div','padding:10px 12px;display:none');
    telPanel.id='tw-sekme-telegram';
    telPanel.appendChild(baslik('TELEGRAM BİLDİRİMİ'));
    telPanel.appendChild(textSatiri('Bot Token','telegramToken','7123456789:AAF...'));
    telPanel.appendChild(textSatiri('Chat ID','telegramChatId','123456789'));

    // Bilgi notu
    const not=mkEl('div','color:#777;font-size:10px;margin-top:8px;line-height:1.5',
      'Bot koruması gelince ekran görüntüsüyle birlikte bildirim gönderilir.');
    telPanel.appendChild(not);

    // Test butonu
    const testBtn=mkEl('button','width:100%;margin-top:8px;padding:5px;background:#2a3a1a;color:#9de86a;border:1px solid #4a7a2a;border-radius:4px;cursor:pointer;font-family:monospace;font-size:11px','🧪 Test Mesajı Gönder');
    testBtn.addEventListener('click', function () {
      ayarlariKaydet();
      telegramGonder('TW Bot test mesaji - ' + new Date().toLocaleTimeString('tr-TR'), null);
    });
    telPanel.appendChild(testBtn);
    telPanel.appendChild(kaydetBtn('log'));

    // BUTON SATIRI
    const btnRow=mkEl('div','display:flex;gap:6px;padding:8px 10px;border-top:1px solid #333');
    const btnBaslat=mkEl('button','flex:1;padding:5px;background:#2d5a1b;color:#9de86a;border:1px solid #4a8a2a;border-radius:4px;cursor:pointer;font-family:monospace;font-size:12px','▶ Başlat');
    btnBaslat.id='tw-btn-baslat';
    const btnDurdur=mkEl('button','flex:1;padding:5px;background:#3a1a1a;color:#e87070;border:1px solid #8a3030;border-radius:4px;cursor:pointer;font-family:monospace;font-size:12px;opacity:0.5','■ Durdur');
    btnDurdur.id='tw-btn-durdur'; btnDurdur.disabled=true;
    btnBaslat.addEventListener('click', baslat);
    btnDurdur.addEventListener('click', durdur);
    btnRow.appendChild(btnBaslat); btnRow.appendChild(btnDurdur);

    // Birleştir
    panel.appendChild(header); panel.appendChild(tabBar);
    panel.appendChild(logPanel); panel.appendChild(ayarPanel);
    panel.appendChild(askerPanel); panel.appendChild(telPanel);
    panel.appendChild(btnRow);
    document.body.appendChild(panel);

    gosterSekme('log');
    ayarlariYukle();

    // Sürükle
    let ox=0,oy=0,drag=false;
    header.addEventListener('mousedown',function(e){drag=true;ox=e.clientX-panel.getBoundingClientRect().left;oy=e.clientY-panel.getBoundingClientRect().top;});
    document.addEventListener('mousemove',function(e){if(!drag)return;panel.style.left=(e.clientX-ox)+'px';panel.style.top=(e.clientY-oy)+'px';panel.style.right='auto';panel.style.bottom='auto';});
    document.addEventListener('mouseup',function(){drag=false;});

    log('Hazir. Sablon: [' + cfg('sablon').toUpperCase() + ']');
  }

  if (document.readyState==='loading') {
    document.addEventListener('DOMContentLoaded', arayuzOlustur);
  } else { arayuzOlustur(); }

})();