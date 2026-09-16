// 恋与临空 前端插件加载器 v4：经 /api/ext_js/load 加载；禁止缓存（每次都拿最新插件）；跳过错误JSON；单文件失败不影响其他
(function(){
  function loadExt(name){
    // 加时间戳参数 + no-store，强制拿最新插件，杜绝“更新了但没生效”
    return fetch('/api/ext_js/load?name='+encodeURIComponent(name)+'&t='+Date.now(), {cache:'no-store'})
      .then(function(r){ return r.text(); })
      .then(function(code){
        var t=(code||'').trim();
        if(t.charAt(0)==='{'){ console.warn('[ext] 跳过 '+name); return; }
        var s=document.createElement('script'); s.textContent=code; document.head.appendChild(s);
        console.log('[ext] 已加载 '+name+' @'+Date.now());
      })
      .catch(function(e){ console.warn('[ext] 加载失败 '+name, e); });
  }
  function loadList(){
    return fetch('/api/ext_js', {cache:'no-store'}).then(function(r){ return r.json(); });
  }
  loadList()
    .then(function(d){
      var files=(d.files||[]).filter(function(f){ return /^[a-zA-Z0-9_-]+\.js$/.test(f); });
      var p=Promise.resolve();
      files.forEach(function(f){ p=p.then(function(){ return loadExt(f); }); });
    })
    .catch(function(){
      var s=document.createElement('script'); s.src='/ext/app2.js?'+Date.now(); document.head.appendChild(s);
    });
})();
