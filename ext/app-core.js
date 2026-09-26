// 恋与临空 前端核心插件（合并版 app-core）：app2 + ext_admin_ui + ext_memfix

// ===== [app2] 记忆库按月折叠 + 通知中心(ai_move) + 地图人/AI配色 =====
(function(){
  var st=document.createElement('style');
  st.textContent='.holo.me .core{color:#ff5252;--glow:#ff5252;--bord:#ff5252aa}.holo.me .lbl{color:#ffd2d2;border-color:#ff5252aa}.holo.other .core{color:#4dd2ff;--glow:#4dd2ff;--bord:#4dd2ffaa}.mem-month{background:#13233d;border:1px solid rgba(80,180,255,.25);border-radius:10px;padding:8px 10px;margin-bottom:8px}.mem-month summary{cursor:pointer;color:#ffd166;font-size:14px;font-weight:bold;outline:none}.mem-month .note-card{margin:8px 0 0}';
  document.head.appendChild(st);

  function renderMonths(el, list, makeCard){
    var months={};
    list.forEach(function(it){ var mm=(it.time||'').slice(0,7)||'未分类'; if(!months[mm])months[mm]=[]; months[mm].push(it); });
    Object.keys(months).sort().reverse().forEach(function(mm){
      var de=document.createElement('details'); de.className='mem-month';
      var sum=document.createElement('summary'); sum.textContent='📅 '+mm+'（'+months[mm].length+'）'; de.appendChild(sum);
      // ✅ 新增：月内按时间从新到旧排序
      var items = months[mm].slice().sort(function(a,b){
        return (b.time||'').localeCompare(a.time||'');
      });
      items.forEach(function(it){ de.appendChild(makeCard(it)); });
      el.appendChild(de);
    });
  }
  window.renderMonths=renderMonths;

  function memCard(it, editF, delF){
    var loc=editF==='editStoryItem'?('🏗️ '+(it.building||it.building_id)):('📍 '+(it.room||''));
    var d=document.createElement('div'); d.className='note-card';
    var author=document.createElement('div'); author.className='n-author'; author.textContent=esc(it.author)+' · '+esc(loc);
    var text=document.createElement('div'); text.className='n-text'; text.textContent=it.text;
    var time=document.createElement('div'); time.className='n-time'; time.textContent=(it.time||'').slice(5,16);
    var ops=document.createElement('span'); ops.style.cssText='float:right';
    var ebtn=document.createElement('span'); ebtn.className='mem-edit'; ebtn.textContent='✏️ 编辑';
    ebtn.onclick=function(){ var fn=window[editF]; if(fn) fn(it.room||'', it.building_id||'', it.index); };
    var dbtn=document.createElement('span'); dbtn.style.cssText='color:#ff6b6b;cursor:pointer'; dbtn.textContent='🗑️';
    dbtn.onclick=function(){ var fn=window[delF]; if(fn) fn(it.room||'', it.building_id||'', it.index); };
    ops.appendChild(ebtn); ops.appendChild(dbtn); time.appendChild(ops);
    d.appendChild(author); d.appendChild(text); d.appendChild(time);
    return d;
  }

  renderMemory = function(){
    var el=document.getElementById('memoryList'); var w=document.getElementById('memoryWrite'); el.innerHTML=''; w.innerHTML='';
    var ais=mapData.user_ais[userName]||[];
    if(memoryTab==='mem'){
      // ---- 新功能：显示“印象备忘录” ----
      if(!ais.length){
        w.innerHTML = '<div class="tip">你还没有 AI。先在 设置→通用 里登记「我的 AI」</div>';
        el.innerHTML = '';
        return;
      }

      // 构建选择器 + 刷新按钮
      w.innerHTML = '<div class="row"><select class="input" id="impressionAiSel" style="flex:1">' +
        ais.map(function(a){ return '<option value="'+esc(a)+'">'+esc(a)+'</option>'; }).join('') +
        '</select><button class="btn green" onclick="refreshCurrentImpression()" style="margin-left:8px">🔄 刷新</button></div>';

      // 加载当前选中的 AI 的印象
      function loadImpression(){
        var aiName = document.getElementById('impressionAiSel').value;
        if(!aiName) return;
        api('/api/ai/impression?ai='+encodeURIComponent(aiName)).then(function(d){
          if(d.ok){
            var text = d.impression || '（TA 还没有形成对你的印象，多互动几天吧）';
            el.innerHTML = '<div class="note-card" style="background:#0d1f3a;padding:16px;border-radius:8px;border-left:4px solid #ffd166;">' +
              '<div style="color:#a8c8ff;font-size:12px;margin-bottom:8px;">💭 ' + esc(aiName) + ' 当前对你的印象：</div>' +
              '<div style="white-space:pre-wrap;line-height:1.8;color:#e6f1ff;">' + esc(text) + '</div>' +
              '<div style="color:#6d8bb0;font-size:11px;margin-top:12px;">📌 印象会在每天深夜自动更新</div>' +
              '</div>';
          } else {
            el.innerHTML = '<div class="tip">' + esc(d.msg || '加载失败') + '</div>';
          }
        }).catch(function(e){
          el.innerHTML = '<div class="tip">加载失败：' + esc(e.message) + '</div>';
        });
      }

      // 监听下拉切换
      var sel = document.getElementById('impressionAiSel');
      if(sel){
        sel.onchange = loadImpression;
        // 自动加载第一个
        setTimeout(loadImpression, 100);
      }

      // 暴露手动刷新函数（供按钮调用）
      window.refreshCurrentImpression = function(){
        var aiName = document.getElementById('impressionAiSel').value;
        if(!aiName) return;
        toast('🔄 正在刷新印象...');
        api('/api/admin/generate_impression?user='+encodeURIComponent(userName)+'&ai='+encodeURIComponent(aiName), {method:'GET'}).then(function(d){
          if(d.ok){
            var result = d.results[aiName] || '未知结果';
            toast('✅ ' + result);
            loadImpression(); // 重新加载
          } else {
            toast('❌ ' + (d.msg || '刷新失败'));
          }
        }).catch(function(e){ toast('❌ '+e.message); });
      };

      return;
    }

    var key=memoryTab==='note'?'notes':(memoryTab==='diary'?'diaries':'stories');
    var list=memoryData[key]||[];
    if(!list.length){ el.innerHTML='<div class="tip">这个分类还没有内容（显示你和你的 AI 写下的）</div>'; return; }
    var editF=key==='notes'?'editNoteItem':(key==='diaries'?'editDiaryItem':'editStoryItem');
    var delF=key==='notes'?'delNoteItem':(key==='diaries'?'delDiaryItem':'delStoryItem');
    renderMonths(el, list, function(it){ return memCard(it, editF, delF); });
  };

  checkBell = function(){
    api('/api/notifications?user='+encodeURIComponent(userName)).then(function(d){
      var items=d.notifications||[]; var seen=localStorage.getItem('gc_notify_seen')||'';
      document.getElementById('bellDot').style.display=(items.length && items[0].time>seen)?'':'none';
    }).catch(function(){});
  };
  openBell = function(){
      api('/api/notifications?user='+encodeURIComponent(userName)).then(function(d){
        var items=d.notifications||[]; var el=document.getElementById('bellList'); el.innerHTML='';
        document.getElementById('bellMask').classList.add('show');
        document.getElementById('bellMask').querySelector('h3').textContent='🔔 通知';
        if(!items.length){ el.innerHTML='<div class="tip">还没有新动态～有人来你家 / 留纸条 / 申请权限 / AI 出门时会提醒你。</div>'; }
        else {
          var ic={visit:'🚶',note:'💌',diary:'📖',request:'📨',ai_note:'💌',ai_diary:'📖',ai_story:'🎬',ai_move:'📍'};
          items.forEach(function(n){
            var icon=ic[n.type]||'🔔';
            var act='';
            if(n.type==='note'||n.type==='ai_note') act='<span class="mem-edit" onclick="openNotifyRoom(\''+esc(n.room||'')+'\',\'note\')">去看看</span>';
            if(n.type==='diary'||n.type==='ai_diary') act='<span class="mem-edit" onclick="openNotifyRoom(\''+esc(n.room||'')+'\',\'diary\')">去看看</span>';
            if(n.type==='request') act='<span class="mem-edit" onclick="openNotifyBid(\''+esc(n.building_id||'')+'\')">去处理</span>';
            if(n.type==='ai_story') act='<span class="mem-edit" onclick="openNotifyRoom(\''+esc(n.room||'')+'\',\'story\')">去看看</span>';
            if(n.type==='ai_move') act='<span class="mem-edit" onclick="openNotifyRoom(\''+esc(n.room||'')+'\',\'chat\')">去看看</span>';
            var div=document.createElement('div'); div.className='bell-item';
            div.innerHTML='<span class="b-text">'+icon+' '+esc(n.text)+'<br><span style="color:#6d8bb0;font-size:11px">'+esc((n.time||'').slice(5,16))+'</span> '+act+'</span>';
            el.appendChild(div);
          });
        }
        if(items.length) localStorage.setItem('gc_notify_seen', items[0].time);
        document.getElementById('bellDot').style.display='none';
      }).catch(function(e){ toast('❌ '+e.message); });
  };

  window.openNotifyRoom = function(room, tab){
    if(!room) return;

    try{
        // 先根据 room 找到所属建筑
        var bid = null;
        for(var k in (mapData.buildings || {})){
            var b = mapData.buildings[k];
            if((b.rooms || []).indexOf(room) >= 0){
                bid = k;
                break;
            }
        }

        // 如果能找到建筑，先建立正确的 currentBuilding / privBuildingId
        if(bid){
            var b2 = mapData.buildings[bid];

            currentBuilding = bid;
            privBuildingId = bid;

            // 记录当前建筑，方便返回
            try{ window._lastBuilding = bid; }catch(e){}

            // 建筑页本身不强制打开，通知最终目标仍然是具体 room
        }

        // 使用正常的房间切换流程
        if(typeof switchRoom === 'function'){
            switchRoom(room, localStorage.getItem('gc_pwd_'+room) || '');
        }else{
            currentRoom = room;
            localStorage.setItem('gc_room', room);
        }

        // 进入聊天视图
        if(typeof showChat === 'function'){
            showChat();
        }

        // 等房间状态完成后打开对应内容
        setTimeout(function(){

            if(tab === 'story'){
                // 剧情通知：直接打开当前房间的剧情簿
                if(typeof loadStoryModal === 'function'){
                    loadStoryModal();
                }
                return;
            }

            if(tab === 'note' || tab === 'diary'){
                // 纸条 / 随笔：打开私人空间对应标签
                if(typeof togglePrivate === 'function'){
                    privTab = tab;
                    togglePrivate();
                }
                return;
            }

            // 普通聊天通知
            if(tab === 'chat'){
                if(typeof showChat === 'function') showChat();
                return;
            }

            // 其他情况保留原来的轨迹跳转
            if(typeof goToTrailSpot === 'function'){
                goToTrailSpot(room, tab);
            }

        }, 500);

    }catch(e){
        console.warn('[notify] openNotifyRoom error', e);
        try{
            if(typeof goToTrailSpot === 'function'){
                goToTrailSpot(room, tab);
            }
        }catch(e2){}
    }
};

  window.openNotifyBid=function(bid){ if(bid) openBuilding(bid); };

  var __origRenderMarkers = renderMarkers;
  renderMarkers = function(canvasId, scope, regionName){
    __origRenderMarkers(canvasId, scope, regionName);
    try{
      var canvas=document.getElementById(canvasId);
      canvas.querySelectorAll('.holo').forEach(function(mm){
        var core=mm.querySelector('.core'); if(!core) return;
        var t=core.textContent;
        if(t==='💗'||t==='🤖'||t==='👤') mm.remove();
      });
      function inScope(b){ return (scope==='map'&&!b.region)||(scope==='region'&&b.region===regionName); }
      function mk(name,bid,x,y,cls,icon){
        var mm=document.createElement('div'); mm.className='holo '+cls;
        mm.style.left=x+'%'; mm.style.top=y+'%';
        mm.innerHTML='<span class="core">'+icon+'</span><span class="lbl">'+esc(name)+'</span>';
        mm.onclick=function(){ if(editMode&&canEdit()){openOp('building',bid);} else { openBuilding(bid); } };
        canvas.appendChild(mm);
      }
      Object.keys(mapData.ai_location||{}).forEach(function(ai){
        var r=mapData.ai_location[ai]; var bid=null;
        for(var k in mapData.buildings){ if((mapData.buildings[k].rooms||[]).indexOf(r)>=0){bid=k;break;} }
        if(!bid) return; var b=mapData.buildings[bid]; if(!inScope(b)) return;
        var isMine=(mapData.user_ais[userName]||[]).indexOf(ai)>=0;
        mk(ai, bid, b.x, b.y, isMine?'homepink':'npc', isMine?'💗':'🤖');
      });
      var myBid=null;
      for(var k2 in mapData.buildings){ if((mapData.buildings[k2].rooms||[]).indexOf(currentRoom)>=0){myBid=k2;break;} }
      if(myBid){ var mb=mapData.buildings[myBid]; mk(userName+' (我)', myBid, mb.x, mb.y, 'me', '👤'); }
      // 直接用 mapData 里已有的 presence（心跳每 3 秒已在更新）
      var pres = (window.mapData && window.mapData.presence) || [];
      pres.forEach(function(p){
        if(p.name===userName) return;
        var r2=p.page; var bid2=null;
        for(var k3 in mapData.buildings){ if((mapData.buildings[k3].rooms||[]).indexOf(r2)>=0){bid2=k3;break;} }
        if(!bid2) return; var b3=mapData.buildings[bid2]; if(!inScope(b3)) return;
        mk(p.name, bid2, b3.x, b3.y, 'other', '👤');
      });
    }catch(e){}
  };
})();

// ===== [ext_admin_ui] 站长总览 + 开发者登录 =====
(function(){
  window.isAdminUser = function(){
    return localStorage.getItem('gc_dev')==='1' || userName === globalPairsAdmin || !globalPairsAdmin;
  };

  window.devUnlock = function(){
    var pwd = prompt('🔐 请输入开发者密码：','');
    if(!pwd) return;
    api('/api/dev/unlock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:userName,pwd:pwd})}).then(function(d){
      if(d.ok){ localStorage.setItem('gc_dev','1'); toast('✅ 开发者模式已解锁'); setTimeout(function(){ location.reload(); },500); }
      else toast('❌ '+(d.msg||'密码错误'));
    }).catch(function(e){ toast('❌ '+e.message); });
  };
  window.devLogout = function(){ localStorage.removeItem('gc_dev'); location.reload(); };

  function esc0(s){ return String(s==null?'':s).replace(/[&<>"']/g,function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }

  function renderOverview(body){
    api('/api/admin/overview?user='+encodeURIComponent(userName)).then(function(d){
      if(!d || !d.ok){ body.innerHTML='<button class="btn gray" style="width:100%;margin:0" onclick="devUnlock()">🔐 开发者登录（站长）</button><div style="font-size:11px;color:#7fa8cf;margin-top:4px">输入开发者密码后可查看用户与 AI 在线总览</div>'; return; }
      var h='<div style="font-size:11px;color:#e6f1ff;line-height:1.7">';
      h+='🔘 AI 总开关：'+(d.ai_enabled?'✅ 开':'⏸ 关')+' ｜ 部署总闸：'+(d.ai_gate?'✅':'⛔')+'<br>';
      h+='👤 当前在线真人：'+(d.online_users&&d.online_users.length?d.online_users.map(esc0).join('、'):'无')+'</div>';
      h+='<div style="margin-top:6px;border-top:1px solid #1d3a5f;padding-top:6px">';
      (d.rows||[]).forEach(function(r){
        var keyTxt=r.key?('✅ '+(esc0(r.provider||'')+'/'+(esc0(r.model||'默认')))):'❌ 无Key';
        var actTxt=r.last_act?('🕒 '+esc0(r.last_act)):(r.visited>0?'✅ 活跃过':'— 从未行动');
        h+='<div class="wk-item" style="font-size:12px"><span class="wk-name">'+esc0(r.owner)+' → '+esc0(r.ai)+'<br><span style="font-size:11px;color:#7fa8cf">Key:'+keyTxt+' ｜ 📍 '+esc0(r.loc)+' ｜ '+actTxt+'</span></span></div>';
      });
      if(!(d.rows||[]).length) h+='<div class="tip" style="font-size:11px">还没有登记任何 AI</div>';
      h+='</div>';
      h+='<button class="btn gray" style="width:100%;margin-top:8px" onclick="devLogout()">🔐 退出开发者模式</button>';
      body.innerHTML=h;
    }).catch(function(){});
  }

  function injectInto(target){
    if(!target || target.querySelector('.dev-overview')) return;
    var box=document.createElement('div'); box.className='dev-overview'; box.style.margin='8px 0 0'; box.style.padding='8px'; box.style.border='1px solid #1d3a5f'; box.style.borderRadius='8px';
    box.innerHTML='<div class="set-label" style="color:#7aa2ff">👑 用户与 AI 在线总览</div><div class="dev-body" style="margin-top:4px">加载中…</div>';
    target.appendChild(box);
    var body=box.querySelector('.dev-body');
    renderOverview(body);
    setInterval(function(){ if(document.body.contains(box)) renderOverview(body); }, 10000);
  }

  function tryInject(){
    var g=document.getElementById('adminGroup');
    if(!g) return;
    var mask=document.getElementById('settingsMask');
    if(mask && !mask.classList.contains('show')) return;
    injectInto(g);
  }

  // 只在打开设置面板时注入一次，不再每秒轮询
  document.addEventListener('click', function(e) {
    try {
      var t = e.target;
      if (t && t.closest && t.closest('[onclick*="openSettings"]')) {
        setTimeout(function(){ tryInject(); }, 200);
      }
    } catch(err){}
  }, true);
  // 兜底：每 5 秒检查一次（只在设置面板打开时才真正执行）
  setInterval(function(){
    try {
      var mask = document.getElementById('settingsMask');
      if (mask && mask.classList.contains('show')) tryInject();
    } catch(e){}
  }, 5000);
})();

// ===== [ext_memfix] 记忆库宽松拉取 + 改名自动迁移 =====
(function(){
  window.loadMemory = function(){
    var el=document.getElementById('memoryList'); var w=document.getElementById('memoryWrite');
    if(!el) return;
    el.innerHTML='<div class="tip">加载中…</div>'; if(w) w.innerHTML='';
    api('/api/memories_all?user='+encodeURIComponent(userName)).then(function(d){
      memoryData=d; if(typeof renderMemory==='function') renderMemory();
    }).catch(function(e){ el.innerHTML='<div class="tip">'+esc(e.message)+'</div>'; });
  };

  window.saveName = function(){
    var n=document.getElementById('setName').value.trim();
    if(!n){ toast('名字不能为空'); return; }
    var oldName=userName;
    api('/api/rename_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:oldName,new_name:n})}).then(function(d){
      if(d.ok){
        userName=n;
        if (window.reinitSSE) window.reinitSSE(n); 
        localStorage.setItem('gc_name',n);
        toast('✅ '+(d.msg||'改名成功，数据已跟随'));
        loadAvatars();
      } else toast('❌ '+(d.msg||'改名失败'));
    }).catch(function(e){ toast('❌ '+e.message); });
  };

// ===== [SSE 主动推送] =====
(function(){
    var sse = null;
    var sseConnected = false;
    var reconnectTimer = null;
    var unreadCount = 0;                // 🆕 未读计数

    // ---------- 角标更新函数 ----------
    function updateBadge(count) {
        // 1. 更新网页标题（所有环境通用）
        if (count > 0) {
            document.title = '(' + count + ') 恋与临空';
        } else {
            document.title = '恋与临空';
        }

        // 2. 尝试设置桌面/移动端角标
        try {
            // 优先判断是否为 Capacitor 原生环境（打包的 APK）
            if (window.Capacitor && window.Capacitor.isNativePlatform()) {
                if (window.Capacitor.Plugins && window.Capacitor.Plugins.App) {
                    window.Capacitor.Plugins.App.setBadge({ count: count }).catch(function(e) {
                        console.warn('[Badge] Capacitor setBadge error:', e);
                    });
                }
            } 
            // 其次尝试 PWA / 标准浏览器 API（HTTPS 或 localhost）
            else if (navigator.setAppBadge) {
                if (count > 0) {
                    navigator.setAppBadge(count);
                } else {
                    navigator.clearAppBadge();
                }
            }
        } catch (e) {
            // 如果设备不支持，静默忽略
            console.debug('[Badge] 当前环境不支持角标:', e);
        }
    }

    // ---------- 清空未读标记（供外部调用） ----------
    function clearUnreadBadge() {
        unreadCount = 0;
        updateBadge(0);
    }
    window.clearUnreadBadge = clearUnreadBadge;

    // ---------- 初始化 SSE 连接 ----------
    function initSSE(user) {
        if (!user) return;
        // 关闭旧连接
        if (sse) {
            try { sse.close(); } catch(e) {}
            sse = null;
            sseConnected = false;
        }
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
        }
        // 如果浏览器不支持 EventSource，直接返回
        if (typeof EventSource === 'undefined') return;

        var url = '/api/stream?user=' + encodeURIComponent(user);
        sse = new EventSource(url);
        sseConnected = true;

        sse.addEventListener('update', function(e) {
            try {
                var data = JSON.parse(e.data);
                console.log('[SSE] 收到推送:', data);
                var type = data.type;
                var payload = data.payload || {};

                if (type === 'new_message') {
                    var room = payload.room;
                    if (room && window.currentRoom === room) {
                        if (typeof loadMessages === 'function') {
                            loadMessages(room);   // 刷新当前房间消息
                        }
                    } else {
                        // 🆕 不在当前房间 → 增加未读计数
                        unreadCount++;
                        updateBadge(unreadCount);

                        var sender = payload.sender || '某人';
                        var brief = payload.content ? payload.content.substring(0, 20) : '';
                        toast('💬 ' + sender + ' 在 ' + room + ' 发来消息：' + brief);
                        markRoomUnread(room);
                    }
                } else if (type === 'new_sms') {
                    // 🆕 新短信 → 增加未读计数
                    unreadCount++;
                    updateBadge(unreadCount);

                    if (typeof loadSms === 'function') {
                        loadSms();
                    }
                    var from = payload.from || '某人';
                    var content = payload.content || '';
                    toast('📩 来自 ' + from + ' 的短信：' + content.substring(0, 30));
                } else if (type === 'new_notification') {
                    if (typeof checkBell === 'function') {
                        checkBell();
                    }
                    toast('🔔 有新通知');
                } else if (type === 'ping') {
                    // 心跳包，无需处理
                }
            } catch (err) {
                console.warn('[SSE] 处理推送事件出错:', err);
            }
        });

        sse.onerror = function(err) {
            console.warn('[SSE] 连接错误，尝试重连...', err);
            sseConnected = false;
            if (sse) {
                try { sse.close(); } catch(e) {}
                sse = null;
            }
            if (reconnectTimer) clearTimeout(reconnectTimer);
            reconnectTimer = setTimeout(function() {
                reconnectTimer = null;
                if (window.userName) {
                    initSSE(window.userName);
                }
            }, 5000);
        };
    }

    // ---------- 标记房间未读（UI 红点） ----------
    function markRoomUnread(room) {
        try {
            var items = document.querySelectorAll('#roomList .room-item');
            for (var i = 0; i < items.length; i++) {
                var el = items[i];
                if (el.textContent.trim() === room) {
                    if (!el.querySelector('.unread-dot')) {
                        var dot = document.createElement('span');
                        dot.className = 'unread-dot';
                        dot.textContent = '●';
                        dot.style.cssText = 'color:#ff6b6b;margin-left:6px;font-size:14px';
                        el.appendChild(dot);
                    }
                    break;
                }
            }
        } catch(e) { /* 静默失败 */ }
    }
    window.markRoomUnread = markRoomUnread;

    // ---------- 重连接口（供改名后调用） ----------
    window.reinitSSE = function(newUser) {
        if (newUser) {
            initSSE(newUser);
        }
    };

    // ---------- 自动初始化 ----------
    function autoInit() {
        if (window.userName) {
            initSSE(window.userName);
        } else {
            var check = setInterval(function() {
                if (window.userName) {
                    clearInterval(check);
                    initSSE(window.userName);
                }
            }, 500);
            setTimeout(function() { clearInterval(check); }, 5000);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoInit);
    } else {
        autoInit();
    }
})();
})();
