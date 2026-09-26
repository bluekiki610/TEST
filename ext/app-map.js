// 恋与临空 前端地图/建筑/经济插件（合并版 app-map）v3.3：修复公共建筑本店按钮消失问题
// ===== [ext_bgfix] 房间背景宽松匹配 + 定时兜底 =====
(function(){
  function norm(s){ return String(s||'').replace(/\s+/g,''); }
  function findBg(room){
    if(!mapData || !mapData.room_bg) return '';
    if(mapData.room_bg[room]) return mapData.room_bg[room];
    var keys=Object.keys(mapData.room_bg); var rn=norm(room);
    for(var i=0;i<keys.length;i++){ var k=keys[i], kn=norm(k); if(kn===rn) return mapData.room_bg[k]; }
    for(var j=0;j<keys.length;j++){ var k2=keys[j], kn2=norm(k2); if(rn && (kn2.indexOf(rn)>=0 || rn.indexOf(kn2)>=0)) return mapData.room_bg[k2]; }
    return '';
  }
  // 只在背景真正缺失时才补一次，每 4 秒检查
  setInterval(function(){
    try{
      var area=document.getElementById('msgArea'); if(!area) return;
      if(!mapData || !mapData.room_bg) return;
      if(area.style.backgroundImage && area.style.backgroundImage.indexOf('url(')===0) return;
      var want=findBg(currentRoom);
      if(want){ applyBg(currentRoom); }
    }catch(e){}
  }, 4000);
})();

// ===== [ext_econui] 经济增强 =====
(function(){
  function buildInfo(d){
    var txt='💰 我的余额：'+(d.wallet||0).toFixed(0)+' 金币';
    var w=d.working;
    if(w){ var b=mapData.buildings[w.building_id]; var left=Math.max(0,Math.ceil(w.start_ts+w.hours*3600-Date.now()/1000)); txt+='<br>💼 上班中：'+(b?esc(b.name):'?')+'（剩 '+Math.floor(left/60)+' 分钟）'; }
    var hj=d.home_jobs[userName]; if(hj) txt+='<br>🏢 我的常驻：'+esc(hj);
    (mapData.user_ais[userName]||[]).forEach(function(ai){ if(d.home_jobs[ai]) txt+='<br>🤖 '+esc(ai)+' 常驻：'+esc(d.home_jobs[ai]); });
    var aw=d.ai_wallets||[];
    if(aw.length){ txt+='<div class="ai-wallet-block" style="margin-top:6px;border-top:1px solid #1d3a5f;padding-top:4px">🤖 我的 AI 钱包：'; aw.forEach(function(w2){ txt+='<div style="padding:2px 0">'+esc(w2.name)+'：💰 '+w2.wallet.toFixed(0)+' 金币</div>'; }); txt+='</div>'; }
    var myh=d.my_history||[];
    if(myh.length){ txt+='<br><br>📖 打工记录：'+myh.slice(-5).reverse().map(function(m){ return '<br>· '+esc(m.time)+' '+esc(m.building)+' '+m.hours+'小时 +'+m.earn.toFixed(0)+'金币'; }).join(''); }
    return txt;
  }
  window.refreshEco = function(){ api('/api/economy?user='+encodeURIComponent(userName)).then(function(d){ var info=document.getElementById('ecoInfo'); if(info) info.innerHTML=buildInfo(d); }).catch(function(){}); };
  setInterval(function(){
    try{
      var info=document.getElementById('ecoInfo'); if(!info || info.querySelector('.ai-wallet-block')) return;
      api('/api/economy?user='+encodeURIComponent(userName)).then(function(d){
        var aw=d.ai_wallets||[]; if(!aw.length) return;
        var info2=document.getElementById('ecoInfo'); if(!info2 || info2.querySelector('.ai-wallet-block')) return;
        var b=document.createElement('div'); b.className='ai-wallet-block'; b.style.cssText='margin-top:6px;border-top:1px solid #1d3a5f;padding-top:4px';
        var t='🤖 我的 AI 钱包：'; aw.forEach(function(w2){ t+='<div style="padding:2px 0">'+esc(w2.name)+'：💰 '+w2.wallet.toFixed(0)+' 金币</div>'; });
        b.innerHTML=t; info2.appendChild(b);
      }).catch(function(){});
    }catch(e){}
  }, 3000);
})();

// ===== [ext_hallfix] 会客厅对话修复 =====
(function(){
  function hallName(){ var b=mapData.buildings[currentBuilding]; return b?b.name+'·会客厅':''; }
  function ensureHall(cb){
    var b=mapData.buildings[currentBuilding]; if(!b){ return cb&&cb(); }
    api('/api/map').then(function(dd){
      mapData=dd;
      var rooms=(mapData.buildings[currentBuilding]||{}).rooms||[]; var hall=b.name+'·会客厅';
      if(rooms.indexOf(hall)>=0 || (mapData.rooms||{})[hall]){ return cb&&cb(); }
      api('/api/map/room',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({building_id:currentBuilding,name:'会客厅'})}).then(function(){ return cb&&cb(); }).catch(function(){ return cb&&cb(); });
    }).catch(function(){ return cb&&cb(); });
  }
  window.sendBMsg=function(){
    var inp=document.getElementById('bChatInput'); var content=inp.value.trim(); if(!content) return;
    ensureHall(function(){
      api('/api/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sender:userName,content:content,role:'user',room:hallName()})}).then(function(){ inp.value=''; loadBChat(); }).catch(function(e){ toast('❌ '+e.message); });
    });
  };
  var _orig=window.loadBChat;
  window.loadBChat=function(){ if(!currentBuilding||!bChatOn) return; ensureHall(function(){ if(_orig) _orig(); }); };
})();

// ===== [ext_mapimg] 地图图片上传 =====
(function(){
  var shown = false;
  function openMapImgUpload(inRegion){
    var kind = inRegion ? 'region' : 'main'; var label = '';
    if(inRegion){ label = currentRegion || ''; if(!label){ label = prompt('给哪个分区上传地图？（输入区域名）',''); } if(!label){ toast('未选择分区'); return; } }
    var f=document.createElement('input'); f.type='file'; f.accept='image/*';
    f.onchange=function(){
      var file=f.files[0]; if(!file) return;
      var rd=new FileReader();
      rd.onload=function(e){
        compressImage(e.target.result, 2000, 0.85, function(small){
          toast('⏳ 上传中…');
          api('/api/mapimg/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:userName,kind:kind,label:label,image:small})}).then(function(d){
            toast(d.ok?('✅ '+d.msg):('❌ '+d.msg)); if(d.ok){ setTimeout(function(){ location.reload(); }, 800); }
          }).catch(function(e){ toast('❌ '+e.message); });
        });
      };
      rd.readAsDataURL(file);
    };
    f.click();
  }
  window.openMapImgUpload = openMapImgUpload;
  function addBtn(){
    if(shown) return;
    [['mapView','main'],['regionView','region']].forEach(function(pair){
      var v=document.getElementById(pair[0]); if(!v) return;
      var top=v.querySelector('.map-top'); if(!top) return;
      var b=document.createElement('button'); b.className='hbtn'; b.style.marginLeft='4px'; b.textContent='🖼️ 上传地图';
      b.onclick=function(){ openMapImgUpload(pair[1]==='region'); };
      top.appendChild(b);
    });
    shown = true;
  }
  function tryAdd(){ api('/api/mapimg/status?user='+encodeURIComponent(userName)).then(function(d){ if(d && d.can_upload){ addBtn(); } }).catch(function(){}); }
  setTimeout(tryAdd, 600);
  setTimeout(tryAdd, 2000);
  setInterval(function(){ if(!shown) tryAdd(); }, 4000);
})();

// ===== [ext_nobtn] 我的页 =====
(function(){
  var _lastRefresh = 0;
  var _orig = window.renderMe;
  window.renderMe = function(){
    if(typeof _orig==='function') _orig();
    try{
      var el=document.getElementById('myBody'); if(!el) return;
      var ais=mapData.user_ais[userName]||[];
      el.querySelectorAll('.my-card').forEach(function(cd){
        var t=cd.querySelector('.m-title'); if(!t) return;
        var txt=t.textContent||'';
        if(txt.indexOf('一键上班')>=0 || txt.indexOf('常用')>=0){ cd.remove(); }
      });
      var eco=document.getElementById('ecoInfo');
      if(eco && !document.getElementById('meQuickWorkBtn')){
        var qb=document.createElement('button'); qb.className='btn'; qb.id='meQuickWorkBtn';
        qb.style.cssText='width:100%;margin-top:8px'; qb.textContent='💼 一键上班（我）';
        qb.onclick=function(){ quickWork(userName); };
        eco.parentNode.appendChild(qb);
      }
      var items=el.querySelectorAll('.wk-item');
      items.forEach(function(it){
        var nm=it.querySelector('.wk-name'); if(!nm) return;
        var txt=nm.textContent.replace('🤖 ','').replace('🤖','').trim();
        if(ais.indexOf(txt)>=0){ var btn=it.querySelector('button'); if(btn) btn.remove(); }
      });
      var loc=document.getElementById('aiLocInfo');
      if(loc){
        if(!ais.length){ loc.innerHTML='（先在设置里登记「我的 AI」）'; }
        else {
          // 先用缓存快速占位，避免闪烁
          var txt='';
          ais.forEach(function(ai){
            var l=(mapData.ai_location||{})[ai]||'未知';
            if(l==='main') l='💬 群聊中（不在具体场所）';
            var line='🤖 '+esc(ai)+'：📍 '+esc(l);
            txt+='<div style="padding:4px 0">'+line+'</div>';
          });
          loc.innerHTML=txt;
          // 立即用真实 API 覆盖
          if(typeof window.refreshMyAiLocations === 'function') window.refreshMyAiLocations();
        }
      }

      // ===== 群聊静音 + 原地待命 开关 =====
      try {
        var muteCard = document.getElementById('groupMuteCard');
        if (!muteCard) {
          var card2 = document.createElement('div');
          card2.className = 'my-card';
          card2.id = 'groupMuteCard';
          card2.innerHTML =
            '<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">' +
              '<label style="display:flex;align-items:center;gap:6px;font-size:13px;color:#cfe8ff;cursor:pointer">🔇 群聊静音' +
                '<label class="switch" style="margin:0"><input type="checkbox" id="groupMuteSwitch" onchange="toggleGroupMuteSimple(this.checked)"><span class="slider"></span></label>' +
              '</label>' +
              '<label style="display:flex;align-items:center;gap:6px;font-size:13px;color:#cfe8ff;cursor:pointer">🧘 原地待命' +
                '<label class="switch" style="margin:0"><input type="checkbox" id="stayPutSwitch" onchange="toggleStayPutSimple(this.checked)"><span class="slider"></span></label>' +
              '</label>' +
            '</div>' +
            '<div style="font-size:11px;color:#6d8bb0;margin-top:4px">💡 do的时候禁止离开或看手机哦</div>' +
            '<div id="groupMuteStatus" style="font-size:11px;color:#7fa8cf;margin-top:2px"></div>';
          el.insertBefore(card2, el.firstChild);
        }

        var ais = mapData.user_ais[userName] || [];
        if (ais.length) {
          var ai = ais[0];
          Promise.all([
            fetch('/api/ai/group_mute?user=' + encodeURIComponent(userName)).then(function(r) { return r.json(); }),
            fetch('/api/ai/stay_put?user=' + encodeURIComponent(userName)).then(function(r) { return r.json(); })
          ])
          .then(function(results) {
            var mutes = results[0].mutes || {};
            var stayPuts = results[1].stay_put || {};
            var isMuted = !!mutes[ai];
            var isStay = !!stayPuts[ai];
            document.getElementById('groupMuteSwitch').checked = isMuted;
            document.getElementById('stayPutSwitch').checked = isStay;
            updateGroupStatus(isMuted, isStay);
          })
          .catch(function() {});
        } else {
          document.getElementById('groupMuteStatus').textContent = '⚠️ 先在设置里登记「我的 AI」';
        }
      } catch(e) {}

      // ===== 确保 AI & 记录 卡片存在并含有召唤按钮 =====
      try {
        var existingCard = null;
        el.querySelectorAll('.my-card .m-title').forEach(function(t) {
          if (t.textContent.trim() === '📣 AI & 记录') existingCard = t.parentNode;
        });
        if (!existingCard) {
          var card = document.createElement('div');
          card.className = 'my-card';
          card.innerHTML = '<div class="m-title">📣 AI & 记录</div>' +
            '<div class="home-actions">' +
            '<button class="act-btn" onclick="summonAI()">📣 召唤AI</button>' +
            '<button class="act-btn" onclick="openTrail()">👣 轨迹</button>' +
            '<button class="act-btn" onclick="openBell()">🔔 来客</button>' +
            '<button class="act-btn" onclick="openMemoryModal()">📚 记忆库</button>' +
            '</div>';
          el.insertBefore(card, el.firstChild);
        } else {
          var actions = existingCard.querySelector('.home-actions');
          if (actions && !actions.querySelector('[onclick*="summonAI"]')) {
            var btn = document.createElement('button');
            btn.className = 'act-btn';
            btn.textContent = '📣 召唤AI';
            btn.onclick = function() { summonAI(); };
            actions.insertBefore(btn, actions.firstChild);
          }
        }
      } catch(e) {}

      // 不再主动拉 /api/map —— 直接用已有的 mapData
      // 如果 5 秒内没有地图数据，才拉一次
      var now=Date.now();
      if(!mapData.buildings || !Object.keys(mapData.buildings).length){
        if(now-_lastRefresh>10000){ _lastRefresh=now; loadMapData().then(function(){ if(curTab==='me') renderMe(); }); }
      }
    }catch(e){}
  };
  
  // ===== 补丁 2.2：AI 实时位置刷新 =====
  window.refreshMyAiLocations = function(){
    var ais = (mapData.user_ais[userName] || []);
    var el = document.getElementById('aiLocInfo');
    if(!el) return;
    if(!ais.length){
      el.innerHTML = '（先在设置里登记「我的 AI」）';
      return;
    }
    api('/api/ai/location?user=' + encodeURIComponent(userName)).then(function(d){
      if(!d || !d.ok) return;
      var locs = d.locations || {};
      var pend = d.pending_moves || {};
      // 同步 mapData 缓存（让地图标记等其他组件也能及时更新）
      mapData.ai_location = locs;
      mapData.ai_pending_moves = pend;
      // 用 API 返回值直接渲染（不依赖缓存）
      var txt = '';
      ais.forEach(function(ai){
        var l = locs[ai];
        if(l === undefined || l === null || l === '') l = '未知';
        if(l === 'main') l = '💬 群聊中（不在具体场所）';
        var line = '🤖 ' + esc(ai) + '：📍 ' + esc(l);
        var p = pend[ai];
        if(p && p.room){
          var left = Math.max(0, Math.ceil((p.at_ts - Date.now()/1000)/60));
          line += '　🚶 正赶往 ' + esc(p.room) + (left > 0 ? '（约 ' + left + ' 分钟）' : '');
        }
        line += ' <span style="color:#7fd0ff;cursor:pointer;font-size:12px" onclick="summonAIHere(currentRoom)">📣召唤</span>';
        txt += '<div style="padding:4px 0">' + line + '</div>';
      });
      el.innerHTML = txt;
    }).catch(function(e){
      console.log('[AI_LOCATION] refresh failed', e);
    });
  };

  // ===== 补丁 2.3：仅在「我的」页刷新 =====
  setInterval(function(){
    try {
      if(typeof curTab !== 'undefined' && curTab === 'me'){
        if(typeof window.refreshMyAiLocations === 'function'){
          window.refreshMyAiLocations();
        }
      }
    } catch(e){}
  }, 4000);
})();

// ===== 群聊静音切换函数 =====
window.toggleGroupMute = function(ai, checked) {
  fetch('/api/ai/group_mute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user: userName, ai: ai, muted: checked })
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    if (d.ok) {
      toast(checked ? '🔇 ' + ai + ' 群聊已静音' : '🔊 ' + ai + ' 群聊已开启');
      setTimeout(function() { if (typeof renderMe === 'function') renderMe(); }, 500);
    } else {
      toast('❌ ' + (d.msg || '设置失败'));
    }
  })
  .catch(function(e) {
    toast('❌ ' + e.message);
  });
};

window.toggleGroupMuteSimple = function(checked) {
  var ais = mapData.user_ais[userName] || [];
  if (!ais.length) { toast('请先登记 AI'); return; }
  var ai = ais[0];
  fetch('/api/ai/group_mute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user: userName, ai: ai, muted: checked })
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    if (d.ok) {
      toast(checked ? '🔇 群聊已静音' : '🔊 群聊已开启');
      updateGroupStatus(checked, document.getElementById('stayPutSwitch').checked);
    } else {
      toast('❌ ' + (d.msg || '设置失败'));
      document.getElementById('groupMuteSwitch').checked = !checked;
    }
  })
  .catch(function(e) {
    toast('❌ ' + e.message);
    document.getElementById('groupMuteSwitch').checked = !checked;
  });
};

window.toggleStayPutSimple = function(checked) {
  var ais = mapData.user_ais[userName] || [];
  if (!ais.length) { toast('请先登记 AI'); return; }
  var ai = ais[0];
  fetch('/api/ai/stay_put', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user: userName, ai: ai, on: checked })
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    if (d.ok) {
      toast(checked ? '🧘 已原地待命（不会自主离开）' : '⏳ 已恢复自由活动');
      updateGroupStatus(document.getElementById('groupMuteSwitch').checked, checked);
    } else {
      toast('❌ ' + (d.msg || '设置失败'));
      document.getElementById('stayPutSwitch').checked = !checked;
    }
  })
  .catch(function(e) {
    toast('❌ ' + e.message);
    document.getElementById('stayPutSwitch').checked = !checked;
  });
};

function updateGroupStatus(isMuted, isStay) {
  var el = document.getElementById('groupMuteStatus');
  if (!el) return;
  var parts = [];
  if (isMuted) parts.push('🔇 群聊已静音');
  else parts.push('🔊 群聊在线');
  if (isStay) parts.push('🧘 原地待命');
  else parts.push('⏳ 自由活动');
  el.textContent = '当前：' + parts.join(' · ');
}

// ===== [ext_shopui v3.0] 消费系统 UI =====
(function(){
  var st=document.createElement('style');
  st.textContent='.shop-card{background:#14283f;border:1px solid rgba(255,200,80,.3);border-radius:12px;padding:10px;margin:10px 0}.shop-card .sh-title{color:#ffd166;font-weight:bold;font-size:14px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center}.shop-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.shop-item{background:#13233d;border:1px solid rgba(80,180,255,.25);border-radius:10px;padding:8px;text-align:center}.shop-item .si-ic{font-size:26px}.shop-item .si-nm{font-size:12px;color:#fff;margin-top:2px}.shop-item .si-dc{font-size:10px;color:#6d8bb0;margin-top:2px;min-height:24px;line-height:1.3}.shop-item .si-pr{font-size:11px;color:#ffd166;margin:4px 0}.shop-item button{background:#0e9f6e;color:#fff;border:none;border-radius:7px;padding:5px 12px;font-size:12px;cursor:pointer}.inv-row{display:flex;align-items:center;gap:8px;background:#13233d;border:1px solid rgba(80,180,255,.2);border-radius:10px;padding:7px 10px;margin-bottom:6px;flex-wrap:wrap}.inv-row .iv-ic{font-size:22px}.inv-row .iv-nm{flex:1;color:#fff;font-size:13px;min-width:60px}.inv-row .iv-cnt{color:#9fd8ff;font-size:12px}.inv-row .iv-act{font-size:11px;color:#7fd0ff;cursor:pointer;padding:2px 6px;white-space:nowrap}.room-deco{font-size:11px;color:#ffd166;margin-top:4px;min-height:14px}';
  document.head.appendChild(st);

  var W=window;
  function api2(url,opt){ return fetch(url,opt).then(function(r){ if(!r.ok) return r.json().then(function(d){ throw new Error(d.detail||('HTTP '+r.status)); }); return r.json(); }); }
  function esc2(s){ var d=document.createElement('div'); d.textContent=s==null?'':String(s); return d.innerHTML; }

  function renderShopSection(){
      var el=document.getElementById('bvBody');
      if(!el||!window.currentBuilding) return;
      var b=window.mapData.buildings[window.currentBuilding]; if(!b) return;
      var bid=window.currentBuilding;

      var old=document.getElementById('shopBtnRow');
      if(old) old.remove();

      // 直接使用固定容器
      var container = document.getElementById('shopBtnRowContainer');
      if(!container) {
          // 万一容器不存在，兜底创建一个
          container = document.createElement('div');
          container.id = 'shopBtnRowContainer';
          container.style.marginTop = '8px';
          el.appendChild(container);
      }

      api2('/api/shop/menu?building='+encodeURIComponent(bid)+'&user='+encodeURIComponent(window.userName||'')).then(function(d){
          if(!d || !d.ok) return;

          if (container.querySelector('#shopBtnRow')) return;

          var nb=document.createElement('button');
          nb.className='act-btn';
          nb.id='shopBtnRow';
          nb.style.cssText='flex:1;min-width:0;padding:7px 2px;font-size:12px';

          if (d.has_menu) {
              nb.textContent='🛍️ 本店';
              nb.onclick=function(){ shopMenuModal(bid); };
          } else if (d.can_admin) {
              nb.textContent='⚙️ 管理本店';
              nb.onclick=function(){ shopAdmin(); };
          } else {
              return;
          }

          container.appendChild(nb);
      }).catch(function(){});
  }

  W.shopMenuModal=function(bid){
    if(!bid) bid=window.currentBuilding;
    if(!bid){ toast('请先进入建筑'); return; }
    api2('/api/shop/menu?building='+encodeURIComponent(bid)+'&user='+encodeURIComponent(window.userName||'')).then(function(d){
      if(!d || !d.ok){ toast('菜单加载失败'); return; }
      var m=document.createElement('div'); m.className='modal-mask show';
      m.onclick=function(){ if(event.target===m) m.remove(); };
      var box=document.createElement('div'); box.className='modal'; box.style.cssText='max-height:85%;overflow-y:auto';
      var adminBtn=d.can_admin?'　<span style="color:#7fd0ff;cursor:pointer" onclick="this.closest(\'.modal-mask\').remove();shopAdmin()">⚙️ 管理</span>':'';
      var h='<h3>🛍️ 本店菜单 · '+esc2(d.building||'')+'</h3>'
        +'<div class="tip" style="margin-bottom:8px">💰 余额：'+(d.wallet||0)+' 金币'+adminBtn+'</div>'
        +'<div class="shop-grid">';
      (d.categories||[]).forEach(function(cat){
        (cat.items||[]).forEach(function(it){
          h+='<div class="shop-item"><div class="si-ic">'+it.icon+'</div><div class="si-nm">'+esc2(it.name)+'</div><div class="si-dc">'+esc2(it.desc)+'</div><div class="si-pr">'+it.price+' 金币</div><button onclick="shopBuy(\''+esc2(it.id)+'\')">购买</button></div>';
        });
      });
      h+='</div>';
      if(!(d.categories||[]).length){
        var emptyMsg = d.can_admin ? '这家店还没上架商品，点右上「⚙️ 管理」去勾选吧' : '这家店暂未营业';
        h = '<h3>🛍️ 本店菜单 · '+esc2(d.building||'')+'</h3>'
          +'<div class="tip">'+emptyMsg+(d.can_admin?'　<span style="color:#7fd0ff;cursor:pointer" onclick="this.closest(\'.modal-mask\').remove();shopAdmin()">⚙️ 管理</span>':'')+'</div>'
          +'<button class="btn gray" style="width:100%;margin-top:8px" onclick="this.closest(\'.modal-mask\').remove()">关闭</button>';
      }
      h+='<button class="btn gray" style="width:100%;margin-top:8px" onclick="this.closest(\'.modal-mask\').remove()">关闭</button>';
      box.innerHTML=h;
      m.appendChild(box); document.querySelector('.app').appendChild(m);
      m.dataset.bid=bid;
    }).catch(function(e){ toast('❌ '+e.message); });
  };
  W.shopBuy=function(itemId){
    var m=document.querySelector('.modal-mask.show'); var bid=m?m.dataset.bid:window.currentBuilding;
    if(!bid){ toast('请先进入建筑'); return; }
    api2('/api/shop/buy',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:window.userName,building:bid,item_id:itemId,qty:1})}).then(function(d){
      if(d.msg) toast(d.msg); else toast('✅ 购买成功');
      if(m && d.wallet!=null){ var t=m.querySelector('.tip'); if(t) t.innerHTML=t.innerHTML.replace(/💰 余额：\d+/, '💰 余额：'+(d.wallet||0)); }
    }).catch(function(e){ toast('❌ '+e.message); });
  };
  W.shopAdmin=function(){
    document.querySelectorAll('.modal-mask.show').forEach(function(o){ o.remove(); });
    var bid=window.currentBuilding;
    if(!bid){ toast('请先进入建筑'); return; }
    api2('/api/shop/customize?building='+encodeURIComponent(bid)+'&user='+encodeURIComponent(window.userName||'')).then(function(d){
      if(!d.ok){ toast('❌ '+(d.msg||'无权管理')); return; }
      var m=document.createElement('div'); m.className='modal-mask show';
      m.onclick=function(){ if(event.target===m) m.remove(); };
      var box2=document.createElement('div'); box2.className='modal'; box2.style.cssText='max-height:85%;overflow-y:auto';
      var h='<h3>🛍️ 本店管理</h3><div class="tip" style="margin-bottom:8px">默认全部不上架；勾选要上架的商品；也可添加本店特供</div>';
      h+='<div style="font-size:13px;color:#9fd8ff;margin:6px 0">📦 系统商品（'+d.items.length+' 项）</div>';
      h+='<div style="display:flex;gap:6px;margin-bottom:6px"><button class="btn" style="flex:1;font-size:12px;margin:0" onclick="shopSetAll(true)">✅ 全选</button><button class="btn gray" style="flex:1;font-size:12px;margin:0" onclick="shopSetAll(false)">⬜ 全不选</button><button class="btn gray" style="flex:1;font-size:12px;margin:0" onclick="shopToggleItems(this)">▼ 展开</button></div>';
      h+='<div id="shopItemsWrap" style="display:none;max-height:38vh;overflow-y:auto;border:1px solid #1d3a5f;border-radius:8px;padding:4px">';
      (d.items||[]).forEach(function(it){
        h+='<div class="pair-item"><label style="display:flex;align-items:center;gap:8px;flex:1;cursor:pointer"><input type="checkbox" '+(it.on?'checked':'')+' onchange="shopCustomToggle(\''+esc2(it.id)+'\',this.checked)"> <span>'+it.icon+' '+esc2(it.name)+' · '+it.price+' 金币</span></label></div>';
      });
      h+='</div>';
      h+='<div style="font-size:13px;color:#9fd8ff;margin:10px 0 6px">🛒 本店特供（自定义，最多 50 个）</div>';
      if((d.custom||[]).length){
        d.custom.forEach(function(c){
          h+='<div class="pair-item"><span style="flex:1">'+esc2(c.icon)+' '+esc2(c.name)+' · '+c.price+' 金币'+(c.desc?'<br><span style="font-size:11px;color:#6d8bb0">'+esc2(c.desc)+'</span>':'')+'</span><span style="color:#7fd0ff;cursor:pointer" onclick="shopCustomEdit(\''+esc2(c.id)+'\')">✏️</span><span style="color:#ff6b6b;cursor:pointer" onclick="shopCustomDel(\''+esc2(c.id)+'\')">🗑️</span></div>';
        });
      } else h+='<div class="tip">还没有自定义商品</div>';
      h+='<div style="font-size:13px;color:#9fd8ff;margin:10px 0 6px">➕ 添加本店特供</div>'
        +'<input class="input" id="scName" placeholder="商品名"><div class="row"><input class="input" id="scIcon" placeholder="emoji" style="width:64px"><input class="input" id="scPrice" placeholder="价格" style="width:90px" type="number" min="1"></div>'
        +'<input class="input" id="scDesc" placeholder="描述（可选）"><button class="btn green" style="width:100%;margin:4px 0" onclick="shopCustomAdd()">➕ 添加商品</button>'
        +'<button class="btn gray" style="width:100%;margin-top:6px" onclick="this.closest(\'.modal-mask\').remove()">关闭</button>';
      box2.innerHTML=h;
      m.appendChild(box2);
      document.querySelector('.app').appendChild(m);
      m.dataset.bid=bid;
    }).catch(function(e){ toast('❌ '+e.message); });
  };
  W.shopToggleItems=function(btn){
    var wrap=document.getElementById('shopItemsWrap'); if(!wrap) return;
    var open=wrap.style.display!=='none';
    wrap.style.display=open?'none':'block';
    btn.textContent=open?'▼ 展开':'▲ 收起';
  };
  W.shopSetAll=function(on){
    var m=document.querySelector('.modal-mask.show'); var bid=m?m.dataset.bid:window.currentBuilding;
    api2('/api/shop/customize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:window.userName,building:bid,action:'set_all',on:on})}).then(function(){ toast(on?'✅ 已全选':'⬜ 已全不选'); shopAdmin(); }).catch(function(e){ toast('❌ '+e.message); });
  };
  W.shopCustomToggle=function(itemId,on){
    var m=document.querySelector('.modal-mask.show'); var bid=m?m.dataset.bid:window.currentBuilding;
    api2('/api/shop/customize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:window.userName,building:bid,action:'toggle',item_id:itemId})}).then(function(){}).catch(function(e){ toast('❌ '+e.message); });
  };
  W.shopCustomDel=function(itemId){
    if(!confirm('删除这个本店特供商品？')) return;
    var m=document.querySelector('.modal-mask.show'); var bid=m?m.dataset.bid:window.currentBuilding;
    api2('/api/shop/customize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:window.userName,building:bid,action:'del',item_id:itemId})}).then(function(){ toast('🗑️ 已删除'); shopAdmin(); }).catch(function(e){ toast('❌ '+e.message); });
  };
  W.shopCustomEdit=function(itemId){
    var m=document.querySelector('.modal-mask.show'); var bid=m?m.dataset.bid:window.currentBuilding;
    api2('/api/shop/customize?building='+encodeURIComponent(bid)+'&user='+encodeURIComponent(window.userName||'')).then(function(d){
      var c=null; (d.custom||[]).forEach(function(x){ if(x.id===itemId) c=x; });
      if(!c){ toast('商品不存在'); return; }
      var nm=prompt('商品名：', c.name); if(nm===null||!nm.trim()) return;
      var icon=prompt('emoji：', c.icon)||'🛍️';
      var price=parseInt(prompt('价格：', c.price),10)||c.price;
      var desc=prompt('描述：', c.desc||'')||'';
      api2('/api/shop/customize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:window.userName,building:bid,action:'edit',item_id:itemId,name:nm,icon:icon,price:price,desc:desc})}).then(function(){ toast('✅ 已编辑'); shopAdmin(); }).catch(function(e){ toast('❌ '+e.message); });
    }).catch(function(e){ toast('❌ '+e.message); });
  };
  W.shopCustomAdd=function(){
    var m=document.querySelector('.modal-mask.show'); var bid=m?m.dataset.bid:window.currentBuilding;
    var nm=document.getElementById('scName').value.trim();
    var icon=document.getElementById('scIcon').value.trim();
    var price=parseInt(document.getElementById('scPrice').value,10);
    var desc=document.getElementById('scDesc').value.trim();
    if(!nm||!price||price<1){ toast('填商品名和价格'); return; }
    api2('/api/shop/customize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:window.userName,building:bid,action:'add',name:nm,icon:icon,price:price,desc:desc})}).then(function(d){
      if(d.ok){ toast('✅ 已添加本店特供'); shopAdmin(); }
      else toast('❌ '+(d.msg||'失败'));
    }).catch(function(e){ toast('❌ '+e.message); });
  };

  function renderRoomDecor(){
    // 已废弃：不再在房间门上显示礼物
  }

  function renderMyItems(){
    var el=document.getElementById('myBody'); if(!el) return;
    var old=document.getElementById('myItemsBox'); if(old) old.remove();
    var box=document.createElement('div'); box.className='my-card'; box.id='myItemsBox';
    box.innerHTML='<div class="m-title">🎒 我的物品</div><div id="myItemsList"><div class="tip">加载中…</div></div>';
    el.appendChild(box);
    api2('/api/shop/inventory?user='+encodeURIComponent(window.userName||'')).then(function(d){
      var list=document.getElementById('myItemsList'); if(!list) return;
      if(!d.items.length){ list.innerHTML='<div class="tip">还没有物品。去商店（建筑页）买点东西吧～</div>'; return; }
      list.innerHTML='';
      d.items.forEach(function(it){
        var row=document.createElement('div'); row.className='inv-row';
        row.innerHTML='<span class="iv-ic">'+it.icon+'</span><span class="iv-nm">'+esc2(it.name)+'</span><span class="iv-cnt">×'+it.count+'</span><span class="iv-act" onclick="shopPlacePrompt(\''+esc2(it.id)+'\')">🏠 摆放</span><span class="iv-act" onclick="shopGiftPrompt(\''+esc2(it.id)+'\')">💝 送礼</span><span class="iv-act" style="color:#ff6b6b" onclick="shopDiscard(\''+esc2(it.id)+'\')">🗑️ 丢弃</span>';
        list.appendChild(row);
      });
    }).catch(function(){ var list=document.getElementById('myItemsList'); if(list) list.innerHTML='<div class="tip">加载失败</div>'; });
  }
  function myHomeRooms(){
    var out=[],seen={};
    Object.keys(window.mapData.buildings||{}).forEach(function(bid){
      var b=window.mapData.buildings[bid];
      if(b.type==='home' && b.owner===window.userName){
        (b.rooms||[]).forEach(function(r){
          if(!r.endsWith('·玄关') && !seen[r]){ seen[r]=1; out.push(r); }
        });
      }
    });
    return out;
  }
  W.shopPlacePrompt=function(itemId){
    var rooms=myHomeRooms();
    var options = [];
    if(rooms.length) options = options.concat(rooms);
    var bid = window.currentBuilding;
    var b = window.mapData.buildings[bid];
    if(b && b.type==='home' && b.owner===window.userName){
      options.push('玄关');
    }
    if(!options.length){ toast('先创建/设置自己的家（住宅）才能摆放'); return; }
    var m=document.createElement('div'); m.className='modal-mask show';
    m.onclick=function(){ if(event.target===m) m.remove(); };
    var box2=document.createElement('div'); box2.className='modal';
    var selHtml = options.map(function(r){
      var val = (r==='玄关') ? (b.name+'·玄关') : r;
      return '<option value="'+esc2(val)+'">'+esc2(r)+'</option>';
    }).join('');
    box2.innerHTML='<h3>🏠 摆放到哪个房间？</h3><select class="input" id="shopPlaceSel">'+selHtml+'</select><div class="row" style="margin-top:8px"><button class="btn green" id="shopPlaceOk">🏠 摆放</button><button class="btn gray" onclick="this.closest(\'.modal-mask\').remove()">取消</button></div>';
    m.appendChild(box2); document.querySelector('.app').appendChild(m);
    document.getElementById('shopPlaceOk').onclick=function(){
      var room=document.getElementById('shopPlaceSel').value;
      api2('/api/shop/place',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:window.userName,item_id:itemId,room:room})}).then(function(d){ toast(d.msg||'✅ 已摆放'); renderMyItems(); m.remove(); }).catch(function(e){ toast('❌ '+e.message); });
    };
  };
  W.shopGiftPrompt=function(itemId){
    var ais=(window.mapData.user_ais[window.userName]||[]);
    if(!ais.length){ toast('先登记你的 AI 才能送礼'); return; }
    try{ if(window.aiPing) window.aiPing(); }catch(e){}
    var pick=prompt('送给哪个 AI？（输入数字）\n'+ais.map(function(a,i){return (i+1)+'. '+a;}).join('\n'),'1');
    var to=ais[parseInt(pick||'1',10)-1]; if(!to){ toast('无效选择'); return; }
    api2('/api/shop/gift',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:window.userName,item_id:itemId,to:to})}).then(function(d){ toast(d.msg||'💝 已送出'); renderMyItems(); }).catch(function(e){ toast('❌ '+e.message); });
  };
  W.shopDiscard=function(itemId){
    if(!confirm('丢弃这个物品 1 件？（丢弃后不可恢复）')) return;
    api2('/api/shop/discard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:window.userName,item_id:itemId,qty:1})}).then(function(d){ toast(d.msg||'🗑️ 已丢弃'); renderMyItems(); }).catch(function(e){ toast('❌ '+e.message); });
  };

  function renderHomeDeco(){
    try{
      var el=document.getElementById('bvBody');
      if(!el||!window.currentBuilding) return;
      var b=window.mapData.buildings[window.currentBuilding];
      if(!b || b.type!=='home') return;
      var old=document.getElementById('homeDecoBox'); if(old) old.remove();
      api2('/api/shop/room_items?building='+encodeURIComponent(window.currentBuilding)).then(function(d){
        var rooms=d.rooms||{}; var any=false;
        Object.keys(rooms).forEach(function(r){ if((rooms[r]||[]).length) any=true; });
        if(!any) return;
        var box=document.createElement('div'); box.className='shop-card'; box.id='homeDecoBox';
        box.innerHTML='<div class="sh-title">🎁 本宅收藏</div>';
        var inner='';
        Object.keys(rooms).forEach(function(r){
          var its=rooms[r]||[]; if(!its.length) return;
          inner+='<div style="margin-bottom:6px;font-size:12px;color:#9fd8ff">📍 '+esc2(r)+'：<span style="font-size:14px;color:#ffd166">'+its.map(function(i){return i.icon;}).join(' ')+'</span></div>';
        });
        box.innerHTML+='<div>'+inner+'</div><div class="tip">这些装饰摆在家里，进房间格下方就能看到</div>';
        el.appendChild(box);
      }).catch(function(){});
    }catch(e){}
  }
  function tryInjectBuilding(){
    try{
      var el=document.getElementById('bvBody');
      if(!el||!window.currentBuilding) return;
      if(!document.getElementById('shopBtnRow')){ renderShopSection(); }
    }catch(e){}
  }
  function tryInjectMe(){
    try{
      var el=document.getElementById('myBody');
      if(!el) return;
      if(!document.getElementById('myItemsBox')) renderMyItems();
    }catch(e){}
  }
  var __om=window.renderMe;
  window.renderMe=function(){ try{ if(__om) __om(); }catch(e){} try{ renderMyItems(); }catch(e){} };
  function hook(el, fn){
    if(!el) return;
    try{
      var obs=new MutationObserver(function(){ setTimeout(fn, 60); });
      obs.observe(el, {childList:true, subtree:false});
    }catch(e){}
  }
  hook(document.getElementById('bvBody'), tryInjectBuilding);
  hook(document.getElementById('myBody'), tryInjectMe);
  if(!window.aiPing) window.aiPing=function(){ try{ api('/api/contact/ping?user='+encodeURIComponent(userName)).catch(function(){}); }catch(e){} };
  var _origSummon2=window.summonAI;
  window.summonAI=function(){
    if(currentRoom==='main'){ toast('💬 首页是群聊，不能召唤到群里～去房间/建筑里召唤吧'); return; }
    try{ if(window.aiPing) window.aiPing(); }catch(e){}
    if(typeof _origSummon2==='function') return _origSummon2.apply(this,arguments);
  };
  console.log('[app-map/shop] v3.0 已启动');
})();

// ===== [v2.6 增强] AI生活轨迹 / 我家纸条过滤 / 日记批注AI回复 =====
(function(){
  window.openTrail=function(){
    var ais=mapData.user_ais[userName]||[];
    document.getElementById('trailMask').classList.add('show');
    var el=document.getElementById('trailList'); if(!el) return;
    el.innerHTML='<div class="tip">加载 AI 生活轨迹…</div>';
    if(!ais.length){ el.innerHTML='<div class="tip">先在设置里登记「我的 AI」</div>'; return; }
    var all=[];
    var p=Promise.resolve();
    ais.forEach(function(ai){
      p=p.then(function(){ return api('/api/trails?user='+encodeURIComponent(ai)).then(function(d){ (d.trails||[]).forEach(function(t){ t.ai=ai; all.push(t); }); }).catch(function(){}); });
    });
    p.then(function(){
      if(!all.length){ el.innerHTML='<div class="tip">你的 AI 最近 7 天还没有生活轨迹（等 TA 们出门逛逛吧）</div>'; return; }
      all.sort(function(a,b){ return (a.time||'').localeCompare(b.time||''); }).reverse();
      var days={};
      all.forEach(function(t){ var ds=(t.time||'').slice(0,10); if(!days[ds])days[ds]=[]; days[ds].push(t); });
      el.innerHTML='';
      Object.keys(days).sort().reverse().forEach(function(ds){
        el.innerHTML+='<div style="margin-top:8px"><b style="color:#ffd166">📅 '+esc(ds)+'</b></div>';
        days[ds].forEach(function(t){
          var link=(t.room&&t.tab)?' <span style="color:#7fd0ff;cursor:pointer" onclick="goToTrailSpot(\''+esc(t.room)+'\',\''+esc(t.tab)+'\')">去看看 →</span>':'';
          el.innerHTML+='<div style="padding:4px 0;font-size:12px;color:#cfe8ff">🤖 '+esc(t.ai||'')+' · 🕐 '+esc(t.time)+' · '+esc(t.text)+link+'</div>';
        });
      });
    });
  };
  window.loadMemory=function(){
    var el=document.getElementById('memoryList'); var w=document.getElementById('memoryWrite');
    if(el) el.innerHTML='<div class="tip">加载中…</div>'; if(w) w.innerHTML='';
    api('/api/memories_all?user='+encodeURIComponent(userName)).then(function(d){
      memoryData=d;
      if(memoryTab==='note' && memoryData.notes){
        var myRooms={};
        Object.keys(mapData.buildings||{}).forEach(function(bid){
          var b=mapData.buildings[bid];
          if(b.type==='home' && b.owner===userName){ (b.rooms||[]).forEach(function(r){ myRooms[r]=1; }); }
        });
        memoryData.notes=(memoryData.notes||[]).filter(function(n){ return !n.room || myRooms[n.room]; });
      }
      if(typeof renderMemory==='function') renderMemory();
    }).catch(function(e){ if(el) el.innerHTML='<div class="tip">'+esc(e.message)+'</div>'; });
  };
  var _origComment=window.commentDiary;
  window.commentDiary=function(idx){
    if(typeof _origComment==='function') _origComment(idx);
    setTimeout(function(){
      try{
        api('/api/diaries?room='+encodeURIComponent(currentRoom)).then(function(d){
          var items=d.diaries||[]; var it=items[idx];
          if(it && it.author){
            api('/api/diaries/reply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({room:currentRoom,index:idx,ai:it.author})}).then(function(r2){
              if(r2 && r2.ok){ toast('💬 '+it.author+' 回复了你的批注'); setTimeout(function(){ if(typeof loadPriv==='function') loadPriv(); }, 300); }
            }).catch(function(){});
          }
        }).catch(function(){});
      }catch(e){}
    }, 6000);
  };
  var _origLoadPriv=window.loadPriv;
  window.loadPriv=function(){
    var r=_origLoadPriv? _origLoadPriv():undefined;
    if(privTab==='diary'){
      setTimeout(function(){
        try{
          api('/api/diaries?room='+encodeURIComponent(currentRoom)).then(function(d){
            var items2=d.diaries||[]; var len=items2.length;
            var cards=document.querySelectorAll('#privList .note-card');
            cards.forEach(function(card, i){
              var it2=items2[len-1-i];
              if(it2 && it2.comment && it2.comment.reply && !card.querySelector('.n-rep-reply')){
                var rep=document.createElement('div'); rep.className='n-reply n-rep-reply';
                rep.innerHTML='🤖 '+esc(it2.comment.reply.author)+' 回复：'+esc(it2.comment.reply.text)+'（'+esc((it2.comment.reply.time||'').slice(5,16))+'）';
                card.appendChild(rep);
              }
            });
          }).catch(function(){});
        }catch(e){}
      }, 700);
    }
    return r;
  };
  console.log('[app-map] v2.6 增强已启动');
})();

// ===== [ext_dateui v2.1] 约会系统 UI（coming/结束/收礼物，我的页不显示好感度） =====
(function(){
  function api3(url,opt){ return fetch(url,opt).then(function(r){ return r.json(); }); }
  function isDateBldg(b){ var f=b.features||[]; return f.indexOf('date')>=0||f.indexOf('food')>=0||f.indexOf('fun')>=0; }
  function addDateBtn(){
    try{
      var el=document.getElementById('bvBody'); if(!el||!window.currentBuilding) return;
      var b=window.mapData.buildings[window.currentBuilding]; if(!b||!isDateBldg(b)) return;
      if(document.getElementById('dateBtnRow')) return;
      var ais=mapData.user_ais[userName]||[]; if(!ais.length) return;
      var row=null; el.querySelectorAll('.act-btn').forEach(function(btn){ if(!row&&(btn.textContent||'').indexOf('召唤')>=0) row=btn.parentNode; });
      if(!row) return;
      var nb=document.createElement('button'); nb.className='act-btn'; nb.id='dateBtnRow';
      nb.style.cssText='flex:1;min-width:0;padding:7px 2px;font-size:12px;color:#ff8fab';
      nb.textContent='💞 约会';
      nb.onclick=function(){
        var ai=ais[0]; if(!ai){ toast('先登记「我的 AI」'); return; }
        api3('/api/date/invite',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:userName,ai:ai,building_id:window.currentBuilding})}).then(function(d){ toast(d.msg||'💌 已邀请'); setTimeout(refreshDate,1000); }).catch(function(e){ toast('❌ '+(e.message||'请求失败')); });
      };
      row.appendChild(nb);
    }catch(e){}
  }
  function renderDateStatus(){
    var el=document.getElementById('bvBody'); if(!el||!window.currentBuilding) return;
    api3('/api/date/status?user='+encodeURIComponent(userName||'')).then(function(d){
      if(!d||!d.ok) return;
      var lines=[];
      var acts=(d.by_building||{})[window.currentBuilding]||[];
      acts.forEach(function(dd){
        if(dd.status==='active'){
          var giftBtn = (dd.bring_gift && dd.gift_item && !dd.gift_accepted) ? ' <span style="color:#ffd166;cursor:pointer" onclick="acceptGift()">💐 收下礼物</span>' : '';
          lines.push('💞 <b>'+esc(dd.user)+'</b> ❤️ <b>'+esc(dd.ai)+'</b> 正在这里约会'+giftBtn+' <span style="color:#ff8fab;cursor:pointer" onclick="endMyDate()">❤️ 结束</span>');
        } else if(dd.status==='coming'){
          var left = Math.max(0, Math.ceil((dd.arrive_at - Date.now()/1000)/60));
          lines.push('🚶 <b>'+esc(dd.ai)+'</b> 正赶往这里赴约（约 '+left+' 分钟后到）');
        }
      });
      (d.invites||[]).forEach(function(iv){
        if(iv.building_id===window.currentBuilding){
          lines.push('💌 等 <b>'+esc(iv.ai)+'</b> 回应约会邀请…');
        }
      });
      var old=document.getElementById('dateStatusBar');
      var html=lines.join('<br>');
      if(!lines.length){ if(old) old.remove(); return; }
      if(old && old.getAttribute('data-html')===html) return;
      var bar=document.createElement('div'); bar.id='dateStatusBar'; bar.setAttribute('data-html',html);
      bar.style.cssText='background:linear-gradient(90deg,rgba(255,140,170,.18),rgba(255,140,170,.04));border:1px solid rgba(255,140,170,.5);border-radius:10px;padding:8px 10px;margin-bottom:8px;font-size:13px;color:#ff8fab';
      bar.innerHTML=html;
      if(old) old.remove();
      el.insertBefore(bar, el.firstChild);
    }).catch(function(){});
  }
  function renderMeDate(){
    var el=document.getElementById('myBody'); if(!el) return;
    api3('/api/date/status?user='+encodeURIComponent(userName||'')).then(function(d){
      if(!d||!d.ok) return;
      var old=document.getElementById('myDateCard');
      var html='';
      var act=null, coming=null, pend=null;
      (d.my||[]).forEach(function(dd){ if(dd.status==='active') act=dd; else if(dd.status==='coming'&&!coming) coming=dd; });
      pend=(d.invites||[])[0];
      if(act){
        var b=window.mapData.buildings[act.building_id]; var bn=b?b.name:act.room;
        html='<div class="m-title" style="color:#ff8fab">💞 我的约会</div>'
          +'<div class="tip">正在和 <b>'+esc(act.ai)+'</b> 在 <b>'+esc(bn)+'</b> 约会</div>'
          +'<button class="btn" style="width:100%;margin-top:6px" onclick="endMyDate()">❤️ 结束约会</button>';
      } else if(coming){
          var left = Math.max(0, Math.ceil((coming.arrive_at - Date.now()/1000)/60));
          html='<div class="m-title" style="color:#ff8fab">💞 我的约会</div>'
            +'<div class="tip">🚶 <b>'+esc(coming.ai)+'</b> 正赶往约会地点，约 '+left+' 分钟后到</div>'
            +'<button class="btn" style="width:100%;margin-top:6px;background:#8b2a3a;color:#fff;border:none;padding:6px 0;border-radius:8px;cursor:pointer" onclick="cancelComingDate()">❌ 取消赴约</button>';
      } else if(pend){
        html='<div class="m-title" style="color:#ff8fab">💌 约会邀请</div>'
          +'<div class="tip">正在等 <b>'+esc(pend.ai)+'</b> 回应…（他可能在上班或考虑中）</div>';
      }
      if(!html){ if(old) old.remove(); }
      else if(!old || old.getAttribute('data-html')!==html){
        var card=document.createElement('div'); card.className='my-card'; card.id='myDateCard'; card.setAttribute('data-html',html);
        card.innerHTML=html;
        if(old) old.remove();
        el.insertBefore(card, el.firstChild);
      }

      // ===== 我的红点：有 AI 主动邀约 / 正在赴约时显示 =====
      try {
        var myDot = document.getElementById('myDot');
        if(myDot){
          var hasPending = !!(d.pending_invites && d.pending_invites.length);
          var hasComing = !!(d.comings && d.comings.length);
          var shouldDot = hasPending || hasComing;
          if(shouldDot && curTab !== 'me'){
            myDot.style.display = '';
          } else if(curTab === 'me'){
            myDot.style.display = 'none';
          } else {
            myDot.style.display = 'none';
          }
        }
      } catch(e) {}
    }).catch(function(){});
  }
  
  window.endMyDate=function(){
    api3('/api/date/end',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:userName})}).then(function(d){ toast(d.msg||'💞 已结束'); setTimeout(function(){ refreshDate(); },500); }).catch(function(e){ toast('❌ '+(e.message||'请求失败')); });
  };

  // ===== 新增取消赴约函数 =====
  window.cancelComingDate = function(){
      if(!confirm('确定要取消赴约吗？')) return;
      api3('/api/date/end', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({user: userName})
      }).then(function(d){
          toast(d.msg || '💞 已取消赴约');
          setTimeout(function(){ refreshDate(); }, 500);
      }).catch(function(e){
          toast('❌ ' + (e.message || '请求失败'));
      });
  };
  // ===== 新增结束 =====
  
  window.acceptGift=function(){
    api3('/api/date/accept_gift',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:userName})}).then(function(d){ toast(d.msg||'💝 已收下'); setTimeout(function(){ refreshDate(); },500); }).catch(function(e){ toast('❌ '+(e.message||'请求失败')); });
  };
  window.refreshDate=function(){ try{ addDateBtn(); renderDateStatus(); renderMeDate(); }catch(e){} };
  function hook3(el,fn){ if(!el) return; try{ var o=new MutationObserver(function(){ setTimeout(fn,80); }); o.observe(el,{childList:true,subtree:false}); }catch(e){} }
  hook3(document.getElementById('bvBody'), refreshDate);
  hook3(document.getElementById('myBody'), refreshDate);
  setInterval(function(){ try{ renderDateStatus(); renderMeDate(); }catch(e){} }, 4000);
  setTimeout(refreshDate, 800);
  setTimeout(refreshDate, 2500);
  console.log('[app-map/date] v2.1 约会 UI（coming/结束/收礼物）已启动');
})();

// ===== [ext_navback v2] 底部导航 + 层级返回修复 =====
(function(){
  window._lastBuilding = window._lastBuilding || null;

  // 核心层级返回逻辑
  window.goBackHomeStep = function(){
    try{
      if(window.buildingState === 'rooms'){
        window.buildingState = 'entrance';
      } else if(window.buildingState === 'entrance'){
        window.buildingState = 'exterior';
      } else {
        if(window.backFromBuilding) window.backFromBuilding();
        else if(window.showMap) window.showMap();
        return;
      }
      if(window.renderBuilding) window.renderBuilding();
    } catch(e){ console.warn('goBackHomeStep error', e); }
  };

  function isInBuilding(){
    try{ var bv=document.getElementById('buildingView'); return bv && bv.style.display!=='none'; }catch(e){ return false; }
  }

  window.goBack = function(){
    try{
      if(isInBuilding()){
        if(window.currentBuilding && window.mapData && window.mapData.buildings[window.currentBuilding] && window.mapData.buildings[window.currentBuilding].type === 'home'){
          window.goBackHomeStep();
          return;
        }
        if(window.backFromBuilding) window.backFromBuilding();
        else if(window.showMap) window.showMap();
        return;
      }
      if(window._lastBuilding && window.showBuilding){
        window.showBuilding(window._lastBuilding);
        return;
      }
      if(window.showChat) window.showChat();
    }catch(e){}
  };

  setInterval(function(){
    try{
      if(window.currentBuilding) window._lastBuilding = window.currentBuilding;
    }catch(e){}
  }, 1500);

  function injectBackBtn(){
    try{
      var navs = document.querySelectorAll('.tabbar, .bottom-nav, #navBar, .nav, nav, #bottomBar, .tabs, .bottom-bar');
      if(!navs.length) return;
      var nav = navs[0];
      if(nav.querySelector('#appBackBtn')) return;
      var b = document.createElement('button');
      b.id='appBackBtn'; b.textContent='⬅';
      b.title='返回上一页';
      b.style.cssText='flex:none;width:44px;height:44px;font-size:18px;background:transparent;color:#9fd8ff;border:none;cursor:pointer';
      b.onclick = function(){ window.goBack(); };
      nav.insertBefore(b, nav.firstChild);
    }catch(e){}
  }
  setInterval(injectBackBtn, 1500);
  setTimeout(injectBackBtn, 800);
  console.log('[app-map/navback v2] 层级返回已启动');
})();

// ===== [ext_uiplus] 公共/自然景观页 + 住宅外观页/玄关页/房间页（修复公共建筑本店按钮） =====
(function(){
  window.summonAIHere = function(room){
    if(!room || room==='main'){ toast('💬 首页是群聊，不能召唤到群里～去房间/建筑里召唤吧'); return; }
    var ais=(mapData.user_ais[userName]||[]);
    if(!ais.length){ toast('请先在设置里登记「我的 AI」'); return; }
    var ai=ais.length===1?ais[0]:ais[parseInt(prompt('召唤哪个 AI？\n'+ais.map(function(a,i){return (i+1)+'. '+a;}).join('\n'),'1')||'1',10)-1];
    if(!ai) return;
    api('/api/summon',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ai:ai,room:room})}).then(function(d){ toast('📣 '+d.msg); }).catch(function(e){ toast('❌ '+e.message); });
  };
  function setupHeaderSummon(){
    var btn=document.getElementById('privBtn'); if(!btn) return;
    if(currentRoom==='main'){
      btn.style.display='none';
      btn.onclick=function(){};
      return;
    }
    btn.style.display='';
    if(btn.getAttribute('data-summon')) return;
    btn.setAttribute('data-summon','1'); btn.innerHTML='📣'; btn.title='召唤我的 AI';
    btn.onclick=function(){ summonAIHere(currentRoom); };
  }
  window.togglePanel=function(id){ var d=document.getElementById(id); if(!d) return; d.style.display=(d.style.display==='none'?'block':'none'); };
  window.FEAT_CN = {work:'工作', shop:'购物', fun:'娱乐', date:'约会', food:'餐饮', medical:'医疗', culture:'文化', service:'服务', transport:'交通', special:'特殊'};
  window.FEAT_EN = {'工作':'work', '购物':'shop', '娱乐':'fun', '约会':'date', '餐饮':'food', '医疗':'medical', '文化':'culture', '服务':'service', '交通':'transport', '特殊':'special'};
  var FEAT_DESC={work:'公司/事务所，AI 可打工',shop:'商场/超市/花店，可购物',fun:'影院/游戏厅/海边，可娱乐',date:'咖啡厅/餐厅，可约会',food:'餐厅/面馆，可吃饭',medical:'医院/诊所/药房，可体检',culture:'博物馆/图书馆/学校，可参观',service:'银行/邮局/政务，可办业务',transport:'车站/机场，可候车歇脚',special:'警察局/神秘场所，有特殊事件'};
  var FEAT_ALL=['work','shop','fun','date','food','medical','culture','service','transport','special'];
  window.showBuildSheet=function(){
    if(!canEdit()){ toast('🔒 访客只读模式'); return; }
    var g=document.getElementById('buildGrid');
    if(!currentRegion){ g.innerHTML='<div class="s-item" onclick="startPlace(\'region\')"><span class="ic">📍</span><span class="nm">区域</span></div>'; }
    else { g.innerHTML='<div class="s-item" onclick="startPlace(\'home\')"><span class="ic">🏠</span><span class="nm">住宅</span></div>'+'<div class="s-item" onclick="startPlace(\'npc\')"><span class="ic">🏙️</span><span class="nm">公共建筑</span></div>'+'<div class="s-item" onclick="startPlace(\'nature\')"><span class="ic">🌳</span><span class="nm">自然景观</span></div>'+'<div class="s-item" onclick="setMyHome()"><span class="ic">💗</span><span class="nm">设为我的家</span></div>'; }
    document.getElementById('buildMask').classList.add('show');
  };
  window.setBuildingFeatures=function(){
    var b=mapData.buildings[currentBuilding];
    if(!b||(b.type!=='npc'&&b.type!=='nature')){ toast('只有公共建筑/自然景观可设功能'); return; }
    var cur=b.features||[];
    var m=document.createElement('div'); m.className='modal-mask show';
    m.onclick=function(){ if(event.target===m) m.remove(); };
    var box=document.createElement('div'); box.className='modal';
    var h='<h3>⚙️ 设置建筑功能</h3><div class="tip" style="margin-bottom:8px">勾选这个建筑能做什么（可多选）；选「工作」才填时薪</div>';
    FEAT_ALL.forEach(function(k){
      h+='<div class="pair-item"><label style="display:flex;align-items:center;gap:8px;flex:1;cursor:pointer"><input type="checkbox" class="feat-cb" value="'+k+'" '+(cur.indexOf(k)>=0?'checked':'')+'> <span>'+FEAT_CN[k]+' <span style="font-size:11px;color:#6d8bb0">· '+FEAT_DESC[k]+'</span></span></label></div>';
    });
    h+='<div id="featSalRow" style="display:'+(cur.indexOf('work')>=0?'block':'none')+';margin-top:8px"><label style="font-size:13px;color:#7fa8cf;display:block;margin-bottom:4px">💰 时薪（金币/小时，0=不可工作）</label><input class="input" id="featSal" type="number" min="0" value="'+(b.salary||50)+'"></div>';
    h+='<div class="row" style="margin-top:10px"><button class="btn green" onclick="saveBuildingFeats()" style="flex:1">💾 保存</button><button class="btn gray" onclick="this.closest(\'.modal-mask\').remove()">取消</button></div>';
    box.innerHTML=h;
    m.appendChild(box); document.querySelector('.app').appendChild(m);
    m.querySelectorAll('.feat-cb').forEach(function(cb){ cb.onchange=function(){ var hasWork=false; m.querySelectorAll('.feat-cb').forEach(function(c){ if(c.value==='work'&&c.checked) hasWork=true; }); document.getElementById('featSalRow').style.display=hasWork?'block':'none'; }; });
  };
  window.saveBuildingFeats=function(){
    var m=document.querySelector('.modal-mask.show'); if(!m) return;
    var feats=[]; m.querySelectorAll('.feat-cb').forEach(function(cb){ if(cb.checked) feats.push(cb.value); });
    var sal=parseFloat(document.getElementById('featSal').value)||0;
    api('/api/building/features',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({building_id:currentBuilding,features:feats,salary:sal})}).then(function(d){ toast('✅ '+d.msg); m.remove(); loadMapData().then(renderBuilding); }).catch(function(e){ toast('❌ '+e.message); });
  };
  window.deleteNpc=function(name){
    if(!confirm('确定删除 NPC「'+name+'」？')) return;
    api('/api/npc/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({building_id:currentBuilding,name:name})}).then(function(){ loadMapData().then(renderBuilding); }).catch(function(e){ toast('❌ '+e.message); });
  };

  // ============================================================
  // 住宅三层页面：函数定义（从正式服版本移植）
  // ============================================================
  window.buildingState = 'exterior';
  window.entranceWallpaper = localStorage.getItem('entranceWallpaper') || 'wallpaper-dark';
  const WALLPAPER_LIST = ['wallpaper-dark', 'wallpaper-warm', 'wallpaper-cool', 'wallpaper-light'];
  const WALLPAPER_STYLES = {
    'wallpaper-dark': 'background: #1a1a2e;',
    'wallpaper-warm': 'background: linear-gradient(135deg, #2d1b11, #1a0f0a);',
    'wallpaper-cool': 'background: linear-gradient(135deg, #0f1a2e, #1a2a3a);',
    'wallpaper-light': 'background: linear-gradient(135deg, #2a2a3a, #3a3a4a);'
  };

  window.cycleWallpaper = function(){
    var idx = WALLPAPER_LIST.indexOf(window.entranceWallpaper);
    idx = (idx + 1) % WALLPAPER_LIST.length;
    window.entranceWallpaper = WALLPAPER_LIST[idx];
    localStorage.setItem('entranceWallpaper', window.entranceWallpaper);
    if(window.renderBuilding) window.renderBuilding();
  };

  function getHomeDisplayNames(b){
    var owner = b.owner || '房主';
    var ais = mapData.user_ais[owner] || [];
    var aiName = ais.length ? ais[0] : '';
    return [owner, aiName];
  }

  window.renderExterior = function(b){
    var bid = currentBuilding;
    var owner = b.owner || '';
    var isOwner = (owner === userName);
    var exteriorUrl = b.exterior_image || '';
    var names = getHomeDisplayNames(b);
    var title = names[1] ? (names[0] + ' 和 ' + names[1] + ' 的家') : (names[0] + ' 的家');
    var desc = b.description || '暂无简介';

    var html = '<div style="text-align:center;padding:20px 10px;min-height:200px;background:rgba(0,0,0,0.2);border-radius:12px;">';
    if(exteriorUrl){
      html += '<img src="'+esc(exteriorUrl)+'" style="max-width:100%;max-height:300px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.6);margin-bottom:12px;" alt="房屋外观">';
    } else {
      html += '<div style="font-size:80px;padding:40px 0;background:rgba(30,50,80,0.4);border-radius:12px;border:2px dashed rgba(80,180,255,0.3);margin-bottom:12px;">🏠</div>';
    }
    html += '<h2 style="color:#ffd166;font-size:20px;margin:0 0 8px;">'+esc(title)+'</h2>';
    html += '<div style="background:rgba(16,29,51,0.8);border-left:4px solid #ffd166;border-radius:6px;padding:8px 14px;margin:8px auto 16px;max-width:90%;display:inline-block;text-align:left;">';
    html += '<span style="font-size:13px;color:#cfe8ff;line-height:1.5;">📝 '+esc(desc)+'</span>';
    html += '</div>';
    html += '<div style="display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;">';
    if(isOwner){
      html += '<button class="upload-icon-btn" style="background:rgba(255,255,255,0.1);border:1px dashed rgba(255,255,255,0.3);border-radius:50%;width:40px;height:40px;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;font-size:20px;color:#9fd8ff;" onclick="uploadExterior(\''+bid+'\')" title="上传房屋外观">📷</button>';
    }
    html += '<button class="btn green" style="font-size:16px;padding:10px 30px;" onclick="window.buildingState=\'entrance\';renderBuilding();">🏠 进入</button>';
    html += '</div>';
    html += '</div>';
    return html;
  };

  window.renderEntrance = function(b){
    var bid = currentBuilding;
    var owner = b.owner || '';
    var isOwner = (owner === userName);
    var photos = b.entrance_photos || [];
    var entranceRoom = b.name + '·玄关';
    var giftItems = [];
    try{
      var roomItems = mapData.shop_room_items && mapData.shop_room_items[entranceRoom] ? mapData.shop_room_items[entranceRoom] : [];
      giftItems = roomItems.map(function(itemId){
        return window._findShopItem ? window._findShopItem(itemId) : null;
      }).filter(function(it){ return it; });
    }catch(e){}

    var wallpaperStyle = WALLPAPER_STYLES[window.entranceWallpaper] || WALLPAPER_STYLES['wallpaper-dark'];

    var html = '<div style="padding:10px;">';
    html += '<div style="display:flex;gap:10px;margin-bottom:16px;">';
    html += '<button class="btn gray" onclick="window.buildingState=\'exterior\';renderBuilding();">⬅ 返回外观</button>';
    html += '<button class="btn" onclick="window.buildingState=\'rooms\';renderBuilding();">🚪 住宅首页</button>';
    html += '</div>';

    html += '<div style="margin-bottom:20px;border-radius:12px;padding:12px;'+wallpaperStyle+'min-height:120px;">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">';
    html += '<span style="color:#fff;font-weight:bold;text-shadow:0 1px 3px rgba(0,0,0,0.8);">🖼️ 照片墙</span>';
    html += '<div style="display:flex;gap:8px;">';
    if(isOwner){
      html += '<button class="btn" style="font-size:12px;padding:3px 10px;background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.2);color:#fff;" onclick="uploadEntrancePhoto(\''+bid+'\')">➕ 添加照片</button>';
    }
    html += '<button class="btn" style="font-size:12px;padding:3px 10px;background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.2);color:#fff;" onclick="cycleWallpaper()">🎨 换壁纸</button>';
    html += '</div></div>';

    if(photos.length){
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:12px;">';
      photos.forEach(function(p, idx){
        html += '<div style="cursor:pointer;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.5);position:relative;border:2px solid rgba(255,255,255,0.2);" onclick="viewPhoto(\''+esc(p.url)+'\')">';
        html += '<img src="'+esc(p.url)+'" style="width:100%;aspect-ratio:1;object-fit:cover;display:block;">';
        if(isOwner){
          html += '<span style="position:absolute;top:4px;right:4px;background:rgba(0,0,0,0.7);color:#ff6b6b;padding:2px 6px;border-radius:12px;font-size:12px;cursor:pointer;" onclick="event.stopPropagation();deleteEntrancePhoto(\''+bid+'\',\''+esc(p.id)+'\')">✕</span>';
        }
        html += '</div>';
      });
      html += '</div>';
    } else {
      html += '<div class="tip" style="color:rgba(255,255,255,0.7);">还没有照片，上传一些温馨的回忆吧～</div>';
    }
    html += '</div>';

    html += '<div style="margin-top:16px;">';
    html += '<div style="color:#9fd8ff;font-weight:bold;margin-bottom:8px;">🎁 礼物角</div>';
    if(giftItems.length){
      html += '<div style="display:flex;flex-wrap:wrap;gap:10px;">';
      giftItems.forEach(function(it){
        html += '<div style="background:#1c2f4d;padding:8px 12px;border-radius:8px;border:1px solid rgba(255,200,80,0.3);display:flex;align-items:center;gap:6px;">';
        html += '<span style="font-size:24px;">'+it.icon+'</span>';
        html += '<span style="font-size:13px;color:#fff;">'+esc(it.name)+'</span>';
        html += '</div>';
      });
      html += '</div>';
    } else {
      html += '<div class="tip">这里还没有礼物，去商店买点东西摆进来吧～</div>';
    }
    html += '</div>';
    html += '</div>';
    return html;
  };

  window.renderRoomsList = function(b){
      var bid = currentBuilding;
      var rooms = b.rooms || [];
      rooms = rooms.filter(function(r){ return !r.endsWith('·玄关'); });

      var html = '<div style="padding:10px;">';
      html += '<button class="btn gray" style="margin-bottom:12px;" onclick="window.buildingState=\'entrance\';renderBuilding();">⬅ 返回玄关</button>';
      html += '<div style="font-weight:bold;color:#9fd8ff;margin-bottom:8px;">🚪 房间列表（长按可管理）</div>';
      if(rooms.length){
        html += '<div class="room-grid" id="roomGridContainer">';
        rooms.forEach(function(r){
          var hall = r.indexOf('·会客厅')>=0;
          var granted = canEnterRoom(r);
          var stateCls = hall?'hall':(granted?'open':'locked');
          var lockTxt = hall?'<span class="r-hall">🛋️ 公共会客区</span>':(granted?'<span class="r-hall">✅ 已开放</span>':'<span class="r-lock">🔒 私密·需申请</span>');
          var rdesc = (mapData.rooms && mapData.rooms[r] && mapData.rooms[r].description)||'';
          
          // 获取房间背景图
          var roomBg = (mapData.room_bg && mapData.room_bg[r]) ? mapData.room_bg[r] : '';
          var bgStyle = roomBg ? 'background-image: url(' + roomBg + '); background-size: cover; background-position: center;' : '';
          
          // 添加 data-room 属性和长按支持（在 JS 中通过事件委托）
          html += '<div class="room-cell '+stateCls+'" data-room="'+esc(r)+'" data-hall="'+hall+'" onclick="enterRoom(\''+esc(r)+'\')" style="position:relative; overflow:hidden; ' + bgStyle + '">';
          
          if(roomBg){
              html += '<div style="position:absolute; top:0; left:0; width:100%; height:100%; background:rgba(13,20,36,0.5); pointer-events:none; z-index:1;"></div>';
          }
          
          html += '<div style="position:relative; z-index:2;">';
          html += '<span class="r-emoji">'+(hall?'🛋️':'🚪')+'</span>';
          html += '<span class="r-name">'+esc(r)+'</span>'+lockTxt;
          if(rdesc) html += '<span style="font-size:10px;color:#6d8bb0;display:block;margin-top:2px">'+esc(rdesc.slice(0,12))+(rdesc.length>12?'…':'')+'</span>';
          html += '</div>';
          html += '</div>';
        });
        if(canEdit()){
          html += '<div class="room-cell add" onclick="createBuildingRoom()">+</div>';
        }
        html += '</div>';
      } else {
        html += '<div class="tip">还没有房间，点「+」创建吧</div>';
      }
      html += '</div>';
      return html;
  };  

  // ===== 背景相关 =====
  function hallBgNow(){ if(!mapData.hall_bg) return ''; var h=new Date().getHours(); var hb=mapData.hall_bg; if(h>=6 && h<16) return hb.day||''; if(h>=16 && h<20) return hb.dusk||''; return hb.night||''; }
  function norm(s){ return String(s||'').replace(/\s+/g,''); }
  function findRoomBg(room){
    if(!mapData || !mapData.room_bg) return '';
    if(mapData.room_bg[room]) return mapData.room_bg[room];
    var keys=Object.keys(mapData.room_bg); var rn=norm(room);
    for(var i=0;i<keys.length;i++){ if(norm(keys[i])===rn) return mapData.room_bg[keys[i]]; }
    for(var j=0;j<keys.length;j++){ var kn=norm(keys[j]); if(rn && (kn.indexOf(rn)>=0 || rn.indexOf(kn)>=0)) return mapData.room_bg[keys[j]]; }
    return '';
  }
  function setAreaBg(area, bg){ if(bg){ area.style.backgroundImage='url('+bg+')'; area.style.backgroundSize='cover'; area.style.backgroundPosition='center'; area.style.backgroundRepeat='no-repeat'; area.style.backgroundColor='rgba(15,26,46,.6)'; } else { area.style.backgroundImage='none'; area.style.backgroundColor='#0f1a2e'; } }
  window.applyBg=function(room){ var area=document.getElementById('msgArea'); if(!area) return; var bg=(room==='main')?hallBgNow():findRoomBg(room); setAreaBg(area, bg); };
  function applyBuildingBg(){ var body=document.getElementById('bvBody'); if(!body) return; var b=mapData.buildings[currentBuilding]; if(!b||!b.bg||!b.bg.url){ body.style.backgroundImage='none'; body.style.backgroundColor=''; return; } var op=(b.bg.opacity!=null&&b.bg.opacity!=='' )?b.bg.opacity:0.5; body.style.backgroundImage='url('+b.bg.url+')'; body.style.backgroundSize='cover'; body.style.backgroundPosition='center'; body.style.backgroundRepeat='no-repeat'; body.style.backgroundColor='rgba(13,20,36,'+op+')'; }
  if(!window.setHallBgUI){
    window.setHallBgUI=function(){
      if(currentRoom && currentRoom!=='main'){
        var f=document.createElement('input'); f.type='file'; f.accept='image/*';
        f.onchange=function(){ var file=f.files[0]; if(!file) return; var reader=new FileReader(); reader.onload=function(e){ compressImage(e.target.result,1400,0.8,function(small){ api('/api/room/bg',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({room:currentRoom,user:userName,image:small})}).then(function(d){ toast('✅ 房间背景已更新'); loadMapData().then(function(){ applyBg(currentRoom); }); }).catch(function(e){ toast('❌ '+e.message); }); }); }; reader.readAsDataURL(file); };
        f.click(); return;
      }
      var m=document.createElement('div'); m.className='modal-mask show'; m.id='hallBgMask';
      m.onclick=function(){ if(event.target===m) m.remove(); };
      var box=document.createElement('div'); box.className='modal';
      box.innerHTML='<h3>🌇 大厅三时段背景</h3>'+'<div class="tip" style="margin-bottom:8px">白天 6-16 / 黄昏 16-20 / 夜晚 20-6；只传一张就一直是那张</div>'+'<button class="btn" style="width:100%;margin-bottom:6px" onclick="pickHallBg(\'day\')">☀️ 白天背景</button>'+'<button class="btn" style="width:100%;margin-bottom:6px" onclick="pickHallBg(\'dusk\')">🌇 黄昏背景</button>'+'<button class="btn" style="width:100%;margin-bottom:6px" onclick="pickHallBg(\'night\')">🌙 夜晚背景</button>'+'<button class="btn gray" style="width:100%" onclick="document.getElementById(\'hallBgMask\').remove()">关闭</button>';
      m.appendChild(box); document.querySelector('.app').appendChild(m);
    };
    window.pickHallBg=function(kind){
      var f=document.createElement('input'); f.type='file'; f.accept='image/*';
      f.onchange=function(){ var file=f.files[0]; if(!file) return; var reader=new FileReader(); reader.onload=function(e){ compressImage(e.target.result,1600,0.8,function(small){ var body={user:userName}; body[kind]=small; api('/api/hall_bg',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(d){ toast('✅ 已上传'); loadMapData().then(function(){ if(currentRoom==='main') applyBg('main'); }); }).catch(function(e){ toast('❌ '+e.message); }); }); }; reader.readAsDataURL(file); };
      f.click();
    };
  }
  function injectHallBgBtn(){
    var bar=document.getElementById('roomDescBar'); if(!bar) return;
    if(currentRoom==='main'){ bar.style.display='flex'; var kids=bar.children; for(var i=0;i<kids.length;i++){ if(!kids[i].classList.contains('hall-bg-btn')) kids[i].style.display='none'; } }
    if(bar.querySelector('.hall-bg-btn')) return;
    if(currentRoom!=='main') return;
    var admin=false; try{ admin=!!(window.isAdminUser&&isAdminUser()); }catch(e){}
    if(!admin) return;
    var sp=document.createElement('span'); sp.className='hall-bg-btn'; sp.style.cssText='cursor:pointer;flex-shrink:0'; sp.title='大厅三时段背景'; sp.textContent='🌇'; sp.onclick=setHallBgUI; bar.appendChild(sp);
  }
  window.setBuildingBgUI=function(){
    var b=mapData.buildings[currentBuilding]; if(!b) return;
    var f=document.createElement('input'); f.type='file'; f.accept='image/*';
    f.onchange=function(){ var file=f.files[0]; if(!file) return; var cur=(b.bg&&b.bg.opacity!=null)?b.bg.opacity:0.5; var op=prompt('背景透明度（0.1~1）：',cur); if(op===null) return; op=Math.max(0.1,Math.min(1,parseFloat(op)||0.5)); var reader=new FileReader(); reader.onload=function(e){ compressImage(e.target.result,1400,0.8,function(small){ api('/api/building/bg',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({building_id:currentBuilding,user:userName,image:small,opacity:op})}).then(function(d){ toast('✅ '+(d.msg||'背景已更新')); loadMapData().then(renderBuilding); }).catch(function(e){ toast('❌ '+e.message); }); }); }; reader.readAsDataURL(file); };
    f.click();
  };
  (function(){ var st=document.createElement('style'); st.textContent='.bchat-wrap{height:60%!important}#bvBody{text-shadow:0 1px 2px rgba(0,0,0,.95),0 0 8px rgba(0,0,0,.65)}#bvBody .act-btn,#bvBody .npc-card,#bvBody .btn,#bvBody .n-desc{text-shadow:none}#msgArea .meta{text-shadow:0 1px 2px rgba(0,0,0,.9),0 0 6px rgba(0,0,0,.6)}#msgArea .msg.system .bubble{color:#ffd166;text-shadow:0 1px 2px rgba(0,0,0,.75)}body.in-main #privBtn,body.in-main [onclick*="summon"],body.in-main [onclick*="召唤"]{display:none!important}#appBackBtn{font-weight:bold}.upload-icon-btn{transition:all 0.2s}.upload-icon-btn:hover{background:rgba(255,255,255,0.25)!important;border-color:rgba(255,255,255,0.6)!important;transform:scale(1.05)}'; document.head.appendChild(st); })();
    var _lastMainBgUrl = '';
  var _lastBldBgKey = '';
  setInterval(function(){
    try{
      // 1. 主厅按钮显隐（只在 main 判断一次，避免重复操作 DOM）
      var isMain = (currentRoom === 'main');
      var bodyHasClass = document.body.classList.contains('in-main');
      if(isMain && !bodyHasClass){
        document.body.classList.add('in-main');
        var _pb2=document.getElementById('privBtn');
        if(_pb2){ _pb2.style.display='none'; _pb2.onclick=function(){}; }
        document.querySelectorAll('#privBtn,[onclick*="summon"],[onclick*="召唤"]').forEach(function(b){ b.style.display='none'; b.onclick=function(){}; });
      } else if(!isMain && bodyHasClass){
        document.body.classList.remove('in-main');
      }
      
      // 2. 头部召唤按钮（幂等，不重复设置）
      setupHeaderSummon();
      
      // 3. 大厅背景按钮（幂等）
      injectHallBgBtn();
      
      // 4. 建筑背景：只在真正变化时应用
      var b = mapData && mapData.buildings ? mapData.buildings[currentBuilding] : null;
      var bldKey = (b && b.bg && b.bg.url) ? (b.bg.url + '|' + (b.bg.opacity||0.5)) : '';
      if(bldKey !== _lastBldBgKey){ _lastBldBgKey = bldKey; applyBuildingBg(); }
      
      // 5. 主厅背景：只在真正变化时应用
      if(isMain){
        var wantMain = hallBgNow();
        if(wantMain !== _lastMainBgUrl){ _lastMainBgUrl = wantMain; applyBg('main'); }
      }
    }catch(e){}
  }, 2000);
})();

// ============================================================
// 核心：window.renderBuilding（保留住宅 + 还原公共建筑）
// ============================================================
// 保存旧版 renderBuilding（来自 index.html 的简陋版本，公共建筑不再使用它）
var _origRenderBuilding = window.renderBuilding;

window.renderBuilding = function(){
  var bid = currentBuilding;
  if(!bid) return;
  var b = mapData.buildings[bid];
  if(!b) return;

  // ===== 1. 住宅建筑：三层结构（完全保留当前版本） =====
  if(b.type === 'home'){
    if(!window.buildingState) window.buildingState = 'exterior';
    var content = '';
    if(window.buildingState === 'exterior'){
      content = window.renderExterior(b);
    } else if(window.buildingState === 'entrance'){
      content = window.renderEntrance(b);
    } else {
      content = window.renderRoomsList(b);
    }
    var el = document.getElementById('bvBody');
    if(el){
      el.innerHTML = content;
      document.getElementById('bEmoji').textContent = b.emoji;
      document.getElementById('bTitle').textContent = b.name;

      var topBar = document.querySelector('.building-view .map-top .header-btns');
      if(topBar){
        var backBtn = topBar.querySelector('.hbtn');
        if(backBtn && backBtn.textContent.includes('返回')){
          backBtn.onclick = function(e){
            e.stopPropagation();
            window.goBackHomeStep();
          };
        }
      }
    }
    return;
  }

    // ===== 2. 公共建筑（npc / nature）：直接完整渲染 =====
    document.getElementById('bEmoji').textContent = b.emoji;
    document.getElementById('bTitle').textContent = b.name;
    var ce = canEdit();
    var el2 = document.getElementById('bvBody');
    if(!el2) return;

    // 获取建筑功能
    var feats = (b.features || []).map(function(f){ return window.FEAT_CN[f] || f; });
    var hasWork = feats.indexOf('工作') >= 0;

    var html = '';

    // 1. 创建者
    html += '<div style="font-size:13px;margin-bottom:8px"><span style="color:#e6f1ff">👑 创建者：</span><span style="color:#ffd166;font-weight:bold">'+esc(b.owner||'?')+'</span></div>';

    // 2. 按钮行：常驻/下班/召唤/背景/对话
    html += '<div style="display:flex;gap:5px;margin-bottom:8px;flex-wrap:nowrap">';
    if(hasWork){
        html += '<button class="act-btn" style="flex:1;min-width:0;padding:7px 2px;font-size:12px" onclick="setHomeJobHere()">🏠常驻</button>';
        html += '<button class="act-btn" style="flex:1;min-width:0;padding:7px 2px;font-size:12px" onclick="stopWorkHere()">🏃下班</button>';
    }
    html += '<button class="act-btn" style="flex:1;min-width:0;padding:7px 2px;font-size:12px" onclick="summonAIHere(hallRoomOf(currentBuilding))">📣召唤</button>';
    html += '<button class="act-btn" style="flex:1;min-width:0;padding:7px 2px;font-size:12px" onclick="setBuildingBgUI()">🖼️背景</button>';
    html += '<button class="act-btn" style="flex:1;min-width:0;padding:7px 2px;font-size:12px" onclick="toggleBChat()">💬对话</button>';
    html += '</div>';

    // 3. 功能标签
    html += '<div style="margin-bottom:8px;display:flex;align-items:center;gap:6px;flex-wrap:wrap">';
    html += feats.map(function(f){
        return '<span style="background:rgba(10,25,45,.55);border:1px solid rgba(80,180,255,.4);color:#9fd8ff;border-radius:10px;padding:2px 8px;font-size:11px;text-shadow:none">'+esc(f)+'</span>';
    }).join('');
    if(ce){
        html += '<span style="cursor:pointer;color:#7fd0ff;font-size:13px;text-shadow:none" onclick="setBuildingFeatures()">⚙️ 设置功能</span>';
    }
    html += '</div>';

    // 4. 时薪（只有工作功能才显示）
    if(hasWork){
        html += '<div style="color:#ffd166;font-size:12px;margin-bottom:8px">💰 时薪：'+((b.salary||0).toFixed(0))+' 金币/小时</div>';
    }

    // 5. 简介（可折叠）
    var desc2 = b.description || '';
    html += '<div style="margin-bottom:8px;cursor:pointer" onclick="togglePanel(\'bDescFull\')">';
    html += '<span style="font-weight:bold;color:#fff">简介</span>';
    html += '<span style="color:#9fd8ff;font-size:13px">：'+esc(desc2.slice(0,28))+(desc2.length>28?'…':'')+'</span>';
    html += '<div id="bDescFull" style="display:none;color:#e6f1ff;font-size:13px;margin-top:5px;line-height:1.6;word-break:break-word">'+esc(desc2||'暂无简介')+'</div>';
    html += '</div>';

    // 6. 常驻于此列表
    if(hasWork){
        var hjHere = Object.keys(mapData.home_jobs || {}).filter(function(n){ return mapData.home_jobs[n] === b.name; });
        if(hjHere.length){
            html += '<div style="color:#7fd0ff;font-size:12px;margin-bottom:8px">🏠 常驻于此：<span style="color:#e6f1ff">'+hjHere.map(esc).join('、')+'</span></div>';
        }
        var wsNames = Object.keys(mapData.work_sessions || {}).filter(function(n){ return mapData.work_sessions[n].building_id === currentBuilding; });
        if(wsNames.length){
            html += '<div style="margin-bottom:8px"><div style="font-size:12px;color:#9fd8ff">👔 正在此工作：</div><div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:4px">';
            wsNames.forEach(function(n){
                var av = avatars[n];
                var ch = (n||'?').charAt(0);
                html += '<div style="cursor:pointer;text-align:center" onclick="smsTo(\''+esc(n)+'\')" title="给'+esc(n)+'发短信">';
                if(av){
                    html += '<img src="'+av+'" style="width:30px;height:30px;border-radius:50%">';
                } else {
                    html += '<div style="width:30px;height:30px;border-radius:50%;background:#0e9f6e;color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;margin:0 auto;text-shadow:none">'+esc(ch)+'</div>';
                }
                html += '<div style="font-size:10px;color:#e6f1ff">'+esc(n)+'</div>';
                html += '</div>';
            });
            html += '</div></div>';
        }
    }

    // 7. NPC
    var npcs = (mapData.npcs[currentBuilding] || []);
    html += '<div style="margin-bottom:8px"><span style="font-weight:bold;color:#fff">👥 NPC</span>';
    html += '<span style="color:#9fd8ff;font-size:12px">（'+npcs.length+' 人）</span>';
    if(ce){
        html += '<span style="cursor:pointer;color:#7fd0ff;font-size:14px;margin-left:6px;text-shadow:none" onclick="addNpcPrompt()" title="添加 NPC">➕</span>';
    }
    html += '</div>';
    npcs.forEach(function(n){
        var d = (n.desc||'');
        html += '<div class="npc-card" style="cursor:pointer" onclick="togglePanel(\'npcDesc_'+esc(n.name)+'\')">';
        html += '<span class="n-emoji">'+esc(n.emoji)+'</span>';
        html += '<div><div class="n-name">'+esc(n.name)+'</div>';
        html += '<div class="n-desc" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+esc(d.slice(0,24))+(d.length>24?'…':'')+'</div>';
        html += '<div class="n-desc" id="npcDesc_'+esc(n.name)+'" style="display:none;word-break:break-word">'+esc(d||'')+'</div>';
        html += '</div>';
        if(ce){
            html += '<span style="cursor:pointer;color:#7fd0ff;font-size:14px;margin-left:auto;text-shadow:none" onclick="event.stopPropagation();editNpc(\''+esc(n.name)+'\')">✏️</span>';
            html += '<span style="cursor:pointer;color:#ff6b6b;font-size:14px;margin-left:8px;text-shadow:none" onclick="event.stopPropagation();deleteNpc(\''+esc(n.name)+'\')">🗑️</span>';
        }
        html += '</div>';
    });

    // 8. 剧情簿
    html += '<div style="margin:10px 0"><button class="btn" style="width:100%" onclick="loadStoryModal()">🎬 剧情簿</button></div>';

    // 9. 插入本店按钮（由 renderShopSection 负责，但这里也补一个兜底）
    // 如果 renderShopSection 没加载，这里作为后备
    html += '<div id="shopBtnRowContainer" style="margin-top:8px"></div>';

    el2.innerHTML = html;

    // 10. 尝试触发本店按钮加载
    if(typeof renderShopSection === 'function'){
        setTimeout(function(){
            var row = document.querySelector('#bvBody .home-actions');
            if(row && !document.getElementById('shopBtnRow')){
                renderShopSection();
            }
        }, 500);
    }

  // ===== 本店按钮由 renderShopSection + tryInjectBuilding 负责，不在这里添加 =====
};

// ===== 照片上传和删除函数 =====
window.uploadExterior = function(bid){
  var f=document.createElement('input'); f.type='file'; f.accept='image/*';
  f.onchange=function(){
    var file=f.files[0]; if(!file) return;
    var rd=new FileReader();
    rd.onload=function(e){
      compressImage(e.target.result, 1200, 0.7, function(small){
        api('/api/building/exterior',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({building_id:bid,user:userName,image:small})}).then(function(d){
          if(d.ok){ toast('✅ 外观已更新'); loadMapData().then(renderBuilding); } else toast('❌ '+d.msg);
        }).catch(function(e){ toast('❌ '+e.message); });
      });
    };
    rd.readAsDataURL(file);
  };
  f.click();
};

window.uploadEntrancePhoto = function(bid){
  var f=document.createElement('input'); f.type='file'; f.accept='image/*';
  f.onchange=function(){
    var file=f.files[0]; if(!file) return;
    var rd=new FileReader();
    rd.onload=function(e){
      compressImage(e.target.result, 1200, 0.7, function(small){
        api('/api/building/entrance_photos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({building_id:bid,user:userName,image:small})}).then(function(d){
          if(d.ok){ toast('✅ 照片已添加'); loadMapData().then(renderBuilding); } else toast('❌ '+d.msg);
        }).catch(function(e){ toast('❌ '+e.message); });
      });
    };
    rd.readAsDataURL(file);
  };
  f.click();
};

window.deleteEntrancePhoto = function(bid, photoId){
  if(!confirm('删除这张照片？')) return;
  api('/api/building/entrance_photos?building_id='+encodeURIComponent(bid)+'&photo_id='+encodeURIComponent(photoId)+'&user='+encodeURIComponent(userName), {method:'DELETE'}).then(function(d){
    if(d.ok){ toast('🗑️ 已删除'); loadMapData().then(renderBuilding); } else toast('❌ '+d.msg);
  }).catch(function(e){ toast('❌ '+e.message); });
};

window.viewPhoto = function(url){
  var m=document.createElement('div'); m.className='modal-mask show';
  m.onclick=function(){ if(event.target===m) m.remove(); };
  var box=document.createElement('div'); box.className='modal'; box.style.cssText='text-align:center;';
  box.innerHTML = '<img src="'+esc(url)+'" style="max-width:100%;max-height:80vh;border-radius:8px;">';
  m.appendChild(box); document.querySelector('.app').appendChild(m);
};

// ===== 辅助：缓存物品详情 =====
window._allShopItems = {};
window._findShopItem = function(itemId){
  return {id:itemId, name:itemId, icon:'🎁'};
};

// ===== 修正 myHomeRooms 过滤玄关 =====
var _origMyHomeRooms = window.myHomeRooms;
window.myHomeRooms = function(){
  var out=[],seen={};
  Object.keys(window.mapData.buildings||{}).forEach(function(bid){
    var b=window.mapData.buildings[bid];
    if(b.type==='home' && b.owner===window.userName){
      (b.rooms||[]).forEach(function(r){
        if(!r.endsWith('·玄关') && !seen[r]){ seen[r]=1; out.push(r); }
      });
    }
  });
  return out;
};

function initHome(){
  if(window.currentBuilding && window.mapData && window.mapData.buildings[window.currentBuilding] && window.mapData.buildings[window.currentBuilding].type==='home'){
    if(!window.buildingState) window.buildingState = 'exterior';
  }
}
setTimeout(initHome, 500);

// ===== [ext_arrivetext] 到达提示统一 =====
(function(){
  function fix(){
    try{
      ['msgList','msgArea','bChatList'].forEach(function(id){
        var c=document.getElementById(id); if(!c) return;
        c.querySelectorAll('div,span').forEach(function(n){
          if(n.children.length===0){
            var t=n.textContent||'';
            if(/🚶 .* 回来了/.test(t)){
              var to=(window.currentRoom&&window.currentRoom!=='main')?window.currentRoom:'临空市';
              n.textContent=t.replace(/🚶 (.+?) 回来了/, '📍 $1 来到了 '+to);
            }
          }
        });
      });
    }catch(e){}
  }
  setInterval(fix, 2000);
  console.log('[app-map/arrivetext] 到达提示统一已启动');
})();

// ===== 长按房间弹出管理菜单 =====
(function(){
    var longPressTimer = null;
    var longPressTriggered = false;

    function showRoomMenu(room, hall) {
        if (hall) {
            toast('会客厅是公共区域，不能编辑或删除');
            return;
        }
        // 使用已有的模态框
        var mask = document.createElement('div');
        mask.className = 'modal-mask show';
        mask.id = 'roomMenuMask';
        mask.onclick = function(e){ if(e.target === mask) hideRoomMenu(); };

        var modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.cssText = 'max-width:360px;';

        var html = '<h3 style="text-align:center;margin-bottom:12px;">🚪 ' + esc(room) + '</h3>';
        html += '<div style="display:flex;flex-direction:column;gap:10px;">';
        html += '<button class="btn" style="width:100%;" onclick="editRoomDescByName(\''+esc(room)+'\');hideRoomMenu();">✏️ 编辑描述</button>';
        html += '<button class="btn red" style="width:100%;" onclick="if(confirm(\'确定删除房间「'+esc(room)+'」吗？\')){deleteRoomConfirm(\''+esc(room)+'\');hideRoomMenu();}">🗑️ 删除房间</button>';
        html += '<button class="btn gray" style="width:100%;" onclick="hideRoomMenu();">取消</button>';
        html += '</div>';

        modal.innerHTML = html;
        mask.appendChild(modal);
        document.querySelector('.app').appendChild(mask);
    }

    function hideRoomMenu() {
        var mask = document.getElementById('roomMenuMask');
        if(mask) mask.remove();
    }
    window.hideRoomMenu = hideRoomMenu;

    function handlePointerDown(e) {
        var cell = e.currentTarget;
        // 忽略会客厅和添加按钮
        if (cell.classList.contains('add')) return;
        if (cell.dataset.hall === 'true') return;
        if (!canEdit()) return;

        longPressTriggered = false;
        longPressTimer = setTimeout(function() {
            longPressTriggered = true;
            // 阻止默认点击（进入房间）
            e.preventDefault();
            var room = cell.dataset.room;
            if (room) {
                showRoomMenu(room, false);
            }
        }, 600); // 600ms 长按
    }

    function handlePointerUp(e) {
        if (longPressTimer) {
            clearTimeout(longPressTimer);
            longPressTimer = null;
        }
        // 如果触发了长按，阻止点击进入房间
        if (longPressTriggered) {
            e.preventDefault();
            longPressTriggered = false;
        }
    }

    function handlePointerLeave(e) {
        if (longPressTimer) {
            clearTimeout(longPressTimer);
            longPressTimer = null;
        }
    }

    function initRoomLongPress() {
        var container = document.getElementById('roomGridContainer');
        if (!container) return;
        // 移除旧监听器（避免重复绑定）
        var cells = container.querySelectorAll('.room-cell:not(.add)');
        cells.forEach(function(cell) {
            cell.removeEventListener('pointerdown', handlePointerDown);
            cell.removeEventListener('pointerup', handlePointerUp);
            cell.removeEventListener('pointerleave', handlePointerLeave);
            cell.addEventListener('pointerdown', handlePointerDown);
            cell.addEventListener('pointerup', handlePointerUp);
            cell.addEventListener('pointerleave', handlePointerLeave);
        });
    }

    // 在 renderBuilding 完成后调用（在住宅首页渲染时）
    var origRenderBuilding = window.renderBuilding;
    window.renderBuilding = function() {
        origRenderBuilding.apply(this, arguments);
        // 如果是住宅首页（buildingState === 'rooms'），初始化长按
        if (window.currentBuilding && window.buildingState === 'rooms') {
            setTimeout(initRoomLongPress, 100);
        }
    };

    // 另外在切换 buildingState 时也可能需要重新初始化
    var origGoBackHomeStep = window.goBackHomeStep;
    window.goBackHomeStep = function() {
        origGoBackHomeStep.apply(this, arguments);
        setTimeout(function() {
            if (window.buildingState === 'rooms') {
                initRoomLongPress();
            }
        }, 150);
    };

    // 暴露给外部手动调用
    window.initRoomLongPress = initRoomLongPress;
})();

// ===== 🎆 烟花自动轮询 =====
(function() {
  var lastCheck = 0;
  function checkFireworks() {
    var now = Date.now();
    if(now - lastCheck < 10000) return;
    lastCheck = now;
    fetch('/api/fireworks/status')
      .then(function(r){ return r.json(); })
      .then(function(data){
        if(data.active && window.currentBuilding === data.building_id){
          if(typeof window.startFireworks === 'function') window.startFireworks();
        } else {
          if(typeof window.stopFireworks === 'function') window.stopFireworks();
        }
      })
      .catch(function(){});
  }
  setInterval(checkFireworks, 10000);
  setTimeout(checkFireworks, 1000);
})();

