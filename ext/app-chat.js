// 恋与临空 前端聊天插件（合并版 app-chat）v1.1：bchatfix+bubbleops+group+perf+restorefix+真人互动记录
// ===== [ext_bchatfix] 公共建筑对话框布局 + 气泡操作 =====
(function(){
  function renderBMsgOK(m){
    var d=document.createElement('div');
    var isMe=m.sender===userName;
    if(m.sender==='system'){ var b0=document.createElement('div'); b0.style.cssText='background:transparent;color:#6d8bb0;font-size:12px;text-align:center;width:100%'; b0.textContent=m.content; d.appendChild(b0); return d; }
    d.style.cssText='display:flex;align-items:flex-start;margin-bottom:10px;'+(isMe?'justify-content:flex-end;':'');
    var av=document.createElement('div'); var a=avatars[m.sender];
    av.style.cssText='width:32px;height:32px;border-radius:50%;background:#1d3150;display:flex;align-items:center;justify-content:center;font-size:13px;overflow:hidden;flex-shrink:0;'+(isMe?'order:2;margin-left:6px;':'order:0;margin-right:6px;');
    av.innerHTML=a?'<img src="'+a+'" style="width:100%;height:100%;object-fit:cover">':esc((m.sender||'?').charAt(0));
    var col=document.createElement('div'); col.style.cssText='max-width:72%;min-width:0;display:flex;flex-direction:column;'+(isMe?'align-items:flex-end;':'');
    var meta=document.createElement('div'); meta.style.cssText='font-size:10px;color:#8fa8c8;margin-bottom:2px;text-shadow:0 1px 2px rgba(0,0,0,.85);text-align:'+(isMe?'right':'left')+';'; meta.textContent=(isMe?'我 · ':'')+m.sender+' · '+(m.time||'');
    var b=document.createElement('div'); b.style.cssText='display:inline-block;max-width:100%;padding:7px 11px;border-radius:9px;font-size:14px;line-height:1.5;word-break:break-word;background:'+(isMe?'#95ec69':'#1c2f4d')+';color:'+(isMe?'#000':'#e6f1ff')+';'+(isMe?'':'border:1px solid rgba(255,255,255,.1);'); b.textContent=m.content;
    try{ var ops=window._bubbleOps? window._bubbleOps(m, hallRoomOf(currentBuilding)) : null; if(ops) b.appendChild(ops); }catch(e){}
    col.appendChild(meta); col.appendChild(b); d.appendChild(av); d.appendChild(col); return d;
  }
  function install(){
    window.loadBChat=function(){
      if(!currentBuilding||!bChatOn) return;
      var hall=hallRoomOf(currentBuilding);
      document.getElementById('bChatTitle').textContent=hall;
      api('/api/messages?room='+encodeURIComponent(hall)+'&user='+encodeURIComponent(userName)).then(function(d){
        var el=document.getElementById('bChatList'); if(!el) return;
        var stick=(el.scrollTop+el.clientHeight>=el.scrollHeight-60);
        el.innerHTML='';
        (d.messages||[]).forEach(function(m){ el.appendChild(renderBMsgOK(m)); });
        if(stick) el.scrollTop=el.scrollHeight;
      }).catch(function(){});
    };
  }
  install();
  [1200,2500,4000,6000].forEach(function(d){ setTimeout(install, d); });
  var _ot=window.toggleBChat;
  window.toggleBChat=function(){ install(); if(typeof _ot==='function') _ot(); };
  setInterval(install, 10000);
})();

// ===== [ext_bubbleops] 气泡操作 =====
(function(){
  function isAiName(n){ try{ var ua=(mapData&&mapData.user_ais)||{}; for(var k in ua){ if((ua[k]||[]).indexOf(n)>=0) return true; } }catch(e){} return false; }
  function deleteMsg(m, room){
    if(!confirm('删除这条消息？')) return;
    api('/api/messages/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({room:room||currentRoom,sender:m.sender,content:m.content,time:m.time,user:userName})})
      .then(function(d){ if(d.ok!==false){ toast('🗑️ 已删除'); loadMessages(true); } else toast('❌ '+(d.msg||'无法删除')); })
      .catch(function(e){ toast('❌ '+e.message); });
  }
  function regenerateMsg(m, room){
    if(!confirm('让 '+m.sender+' 重新说一遍？')) return;
    api('/api/ai/regenerate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({room:room||currentRoom,ai:m.sender,content:m.content,time:m.time})})
      .then(function(d){ if(d.ok!==false){ toast('🔄 '+(d.msg||'重新生成中')); loadMessages(true); } else toast('❌ '+(d.msg||'失败')); })
      .catch(function(e){ toast('❌ '+e.message); });
  }
  window.deleteMsg=deleteMsg; window.regenerateMsg=regenerateMsg;
  window._bubbleOps=function(m, room){
    if(!m || m.sender==='system') return null;
    var ops=document.createElement('span'); ops.style.cssText='float:right;margin-left:8px;font-size:11px;line-height:1;user-select:none;white-space:nowrap;';
    var ai=isAiName(m.sender);
    var canDel=(m.sender===userName)||ai;
    try{ if(window.isAdminUser&&isAdminUser()) canDel=true; }catch(e){}
    if(ai){
      var rf=document.createElement('span'); rf.textContent='🔄'; rf.title='重新生成'; rf.style.cssText='cursor:pointer;margin-right:4px;';
      rf.onclick=function(e){ e.stopPropagation(); e.preventDefault(); regenerateMsg(m, room); }; ops.appendChild(rf);
    }
    if(canDel){
      var del=document.createElement('span'); del.textContent='🗑️'; del.title='删除'; del.style.cssText='cursor:pointer;';
      del.onclick=function(e){ e.stopPropagation(); e.preventDefault(); deleteMsg(m, room); }; ops.appendChild(del);
    }
    return ops.childNodes.length?ops:null;
  };
  var _origRM2=window.renderMsg;
  window.renderMsg=function(m){
    var d=_origRM2? _origRM2(m):null;
    if(!d) return d;
    try{ var ops=window._bubbleOps(m, currentRoom); if(ops){ var bubble=d.querySelector('.bubble'); if(bubble) bubble.appendChild(ops); } }catch(e){}
    return d;
  };
})();

// ===== [ext_group] 临空社区群 =====
(function(){
  var _rl = window.roomLabel; window.roomLabel = function(r){ return r==='main' ? '💬 临空社区' : (_rl ? _rl(r) : r); };
  var _pl = window.pageLabel; window.pageLabel = function(p){ return p==='main' ? '💬 临空社区' : (_pl ? _pl(p) : p); };
  function refreshUI(){
    try{
      document.querySelectorAll('.hbtn').forEach(function(b){
        if(b.getAttribute('data-grpdone')) return;
        if((b.textContent||'').indexOf('大厅')>=0){ b.innerHTML='💬社区'; b.setAttribute('data-grpdone','1'); }
      });
      var rn=document.getElementById('roomName');
      if(rn && (rn.textContent==='公共大厅'||rn.textContent==='临空社区')) rn.textContent='💬 临空社区';
    }catch(e){}
  }
  setTimeout(refreshUI, 600);
  setInterval(refreshUI, 2000);
  var _osg = window.openSettingsGroup;
  window.openSettingsGroup = function(name){
    var r = _osg ? _osg(name) : undefined;
    if(name==='ai_toggle'){
      setTimeout(function(){
        try{
          var body=document.getElementById('groupBody');
          if(!body || document.getElementById('grpCoolBox')) return;
          var d=document.createElement('div'); d.className='set-group'; d.id='grpCoolBox';
          d.innerHTML='<label>💬 社区群聊 · AI 回复冷却</label>'+'<select class="input" id="grpCoolSel"><option value="30">30 秒</option><option value="45">45 秒</option><option value="60">60 秒</option></select>'+'<button class="btn" onclick="saveGrpCool()">保存</button>'+'<div class="tip">AI 在社区群里两次自主发言的间隔（主人说话不受限；没真人时 AI 合计聊 5-10 条就停）</div>';
          body.appendChild(d);
          api('/api/ai/group_config').then(function(c){ if(c.cooldown!=null) document.getElementById('grpCoolSel').value=String(c.cooldown); }).catch(function(){});
        }catch(e){}
      }, 400);
    }
    return r;
  };
  window.saveGrpCool = function(){
    try{
      var v=parseInt(document.getElementById('grpCoolSel').value,10)||30;
      api('/api/ai/group_config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:userName,cooldown:v})})
        .then(function(d){ toast('✅ 群聊冷却已设为 '+d.cooldown+' 秒'); }).catch(function(e){ toast('❌ '+e.message); });
    }catch(e){}
  };
})();

// ===== [ext_perf] 性能三合一 =====
(function(){
  var _origLM = window.loadMessages;
  window.loadMessages = function(silent){
    if(silent){ try{ var chat=document.getElementById('chatView'); if(chat && chat.style.display==='none'){ return; } }catch(e){} }
    if(typeof _origLM==='function') _origLM(silent);
  };
  var _lastRoom = null; var _lastKeys = [];
  var _keyOf = function(m){ return (m.sender||'')+'|'+(m.content||'')+'|'+(m.time||''); };
  function appendOne(area, m){ if(m.sender==='system') area.appendChild(renderSystem(m.content)); else area.appendChild(renderMsg(m)); }
  function fullRender(area, msgs){
    var stick = area.scrollTop+area.clientHeight>=area.scrollHeight-50;
    area.innerHTML='';
    if(!msgs || !msgs.length){ area.innerHTML='<div class="sys-tip">✨ 欢迎来到 '+esc(roomLabel(currentRoom))+'，说点什么吧~</div>'; return; }
    var i=0, chunk=60;
    function next(){ var end=Math.min(i+chunk, msgs.length); for(; i<end; i++){ appendOne(area, msgs[i]); } if(i<msgs.length){ requestAnimationFrame(next); } else if(stick){ area.scrollTop=area.scrollHeight; } }
    next();
  }
  window.renderMessages = function(msgs){
    var area=document.getElementById('msgArea'); if(!area) return;
    msgs = msgs||[]; var room = currentRoom; var keys = msgs.map(_keyOf);
    if(_lastRoom !== room || !_lastKeys.length){ _lastRoom = room; _lastKeys = keys; fullRender(area, msgs); return; }
    var lastKey = _lastKeys[_lastKeys.length-1];
    var idx = keys.lastIndexOf(lastKey);
    if(idx >= 0){
      var added = msgs.slice(idx+1);
      if(added.length){ var stick = area.scrollTop+area.clientHeight>=area.scrollHeight-50; for(var j=0;j<added.length;j++){ appendOne(area, added[j]); } if(stick) area.scrollTop=area.scrollHeight; }
      _lastKeys = keys; return;
    }
    _lastRoom = room; _lastKeys = keys; fullRender(area, msgs);
  };
  var _origWS = window.worldSnapshot;
  window.worldSnapshot = function(){
    try{
      var now = Date.now(); var last = parseInt(localStorage.getItem('gc_ws_last')||'0',10);
      if(now - last < 30*60*1000) return;
      localStorage.setItem('gc_ws_last', String(now));
      setTimeout(function(){ if(typeof _origWS==='function') _origWS(); }, 3000);
    }catch(e){}
  };
})();

// ===== [ext_restorefix] restoreCache =====
(function(){
  window.restoreCache=function(){
    if(currentRoom==='main' || (currentRoom && currentRoom.indexOf('·会客厅')>=0)){ return Promise.resolve(); }
    var a=JSON.parse(localStorage.getItem(cacheKey())||'[]');
    if(!a.length) return Promise.resolve();
    return api('/api/restore',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:a,room:currentRoom,password:roomPassword})}).catch(function(){});
  };
})();

// ===== [真人互动记录] AI 主动关心：真人说话/发短信即记录 =====
(function(){
  if(!window.aiPing) window.aiPing=function(){ try{ api('/api/contact/ping?user='+encodeURIComponent(userName)).catch(function(){}); }catch(e){} };
  var _origSM=window.sendMessage;
  window.sendMessage=function(){ try{ if(window.aiPing) window.aiPing(); }catch(e){} if(typeof _origSM==='function') return _origSM.apply(this,arguments); };
  var _origSS=window.sendSmsTo;
  window.sendSmsTo=function(){ try{ if(window.aiPing) window.aiPing(); }catch(e){} if(typeof _origSS==='function') return _origSS.apply(this,arguments); };
})();
// ===== [新增] 检查 AI 主动约会邀请（显示横幅） =====
function checkPendingInvite() {
    api('/api/date/status?user=' + encodeURIComponent(userName)).then(function(d) {
        if (d.pending_invites && d.pending_invites.length) {
            var inv = d.pending_invites[0];
            var banner = document.getElementById('inviteBanner');
            if (!banner) {
                banner = document.createElement('div');
                banner.id = 'inviteBanner';
                banner.style.cssText = 'background:rgba(255,140,170,.2);border:1px solid #ff8fab;border-radius:8px;padding:6px 10px;margin:4px 10px;font-size:13px;color:#ff8fab;text-align:center';
                var area = document.getElementById('msgArea');
                if (area && area.parentNode) {
                    area.parentNode.insertBefore(banner, area);
                }
            }
            banner.innerHTML = '💞 ' + esc(inv.ai) + ' 约你去「' + esc(inv.building) + '」约会！直接在聊天框回复「好」或「不」就行～';
            banner.style.display = 'block';
        } else {
            var b2 = document.getElementById('inviteBanner');
            if (b2) b2.style.display = 'none';
        }
    }).catch(function() {});
}

setInterval(checkPendingInvite, 5000);

var _origLoadMsg = window.loadMessages;
window.loadMessages = function(silent) {
    if (typeof _origLoadMsg === 'function') _origLoadMsg(silent);
    setTimeout(checkPendingInvite, 500);
};