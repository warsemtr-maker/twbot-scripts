// ==UserScript==
// @name         001*scriptler
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  script
// @author       warsem
// @include http*://*.*game.php*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=tribalwars.net
// @grant        none
// ==/UserScript==






(function() {
  
    // --- MENÜ OLUŞTURMA (İzinli ise) ---
    var menu = document.createElement('td');
    menu.className = 'menu-item';
    menu.innerHTML = `
      <a href="#">❤ EFSANELERE-ÖZEL ❤</a>
      <table cellspacing="0" class="menu_column">
        <tbody>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('http://warsemtv.altervista.org/20-05-2525/scriptler/saldr.js');void(0);">saldırı</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://dl.dropboxusercontent.com/scl/fi/z64zyb694bhj3fpohx0r8/denge2.js?rlkey=b1wu4udddiezi5lln2xln54fe&dl=0');void(0);">maden dengele 2</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twscripts.dev/scripts/backtimesPlanner.js');void(0);">süre 1 hesapla</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twdevtools.github.io/approved/scripts/planner.js');void(0);">süre 2 hesapla</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://shinko-to-kuma.com/scripts/backTimeFromReport.js');void(0);">rapor gel tıkla kilit</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://shinko-to-kuma.com/scripts/requestScript.js');void(0);">maden lazım koye</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://shinko-to-kuma.com/scripts/massScavenge.js');void(0);">toplu temizlik</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://media.innogamescdn.com/com_DS_BR/Scripts/Aprovados/UpdatedResourceSenderForMinting.js');void(0);">maden tek köy</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://dl.dropbox.com/scl/fi/co1mfmxbttnz1c2es47mf/otomatikrapor.js?rlkey=mhzrjmzwnulcmvxa8hb9hrwmv&dl=0');void(0);">rapor ekle</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://dl.dropbox.com/scl/fi/57xqzlshk7j4kslpqokqp/toplutem-zlik.js?rlkey=xaelfltuaf4xf8q3tm34hilzr&dl=0');void(0);">otomatik toplu temizlik</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://dl.dropboxusercontent.com/scl/fi/ns1xnwt1kq101fvrr5pe7/kaynakdenge.js?rlkey=octgsgo5jkorzuulirrq84t6l&dl=0');void(0);">maden dengele yeni</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twscripts.dev/scripts/mapCoordPicker.js');">harita sec</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://dl.dropboxusercontent.com/scl/fi/qhlrqnlprfh3ge7r82le5/YAKINKOY.js?rlkey=5hege9uz4y6kpsrrcv7qwyxjq&dl=0');void(0);">ENYAKIN köyden destek at</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twscripts.dev/scripts/countHomeTroops.js');void(0);">birlik say</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twscripts.dev/scripts/supportCounterEvolved.js');void(0);">destek say</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twscripts.dev/scripts/commandsOverview.js');void(0);">komut bak</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twscripts.dev/scripts/findFrontlineVillages.js');void(0);">köy bul</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twscripts.dev/scripts/troopTemplatesManager.js');void(0);">birlik sablonu</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://dl.dropboxusercontent.com/scl/fi/sshk4f7ph15kgvi8lqzns/sald-r.js?rlkey=zvkqn3qi2029rg7r581rii5gl&dl=0');void(0);">saldırı</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twscripts.dev/scripts/clearBarbarianWalls.js');void(0);">duvar yık</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twscripts.dev/scripts/massCommandTimer.js');">süre</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twscripts.dev/scripts/singleVillageSnipe.js');">süre 2</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twscripts.dev/scripts/extendedPlayerInfo.js');">OYUNCU PROFİLE GEL TIKLA</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twscripts.dev/scripts/extendedTribeInfo.js');">KLAN PROFİLE GEL TIKLA</a></td></tr>
          <tr><td class="menu-column-item"><a href="javascript:$.getScript('https://twscripts.dev/scripts/mapCoordPicker.js');">haritadan kordinat sec</a></td></tr>
          <tr><td class="bottom"><div class="corner"></div><div class="decoration"></div></td></tr>
        </tbody>
      </table>
    `;
    function _menuEkle() {
        var row = document.querySelector('tr#menu_row');
        if (!row) {
            setTimeout(_menuEkle, 500);
            return;
        }
        row.prepend(menu);
    }
    _menuEkle();
})();