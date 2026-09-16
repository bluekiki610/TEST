// app-instance.js - 副本系统 v9（修复进入/暂离逻辑 + 加载优化）
(function() {
    'use strict';
    console.log('[ext] app-instance.js v9 加载...');

    // ---------- 全局状态 ----------
    let currentUser = null;
    let allAis = [];
    let selectedAi = null;
    let selectedOwner = null;
    let instances = {};
    let userTags = [];
    let currentFilterTag = '全部';
    let currentInstanceId = null;
    let instanceBg = '';
    let isReadOnly = false;
    let publicInstancesMap = {};
    let currentEditingInstance = null;

    // ---------- 工具函数 ----------
    function esc(s) { return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    function toast(msg) { if (window.toast) window.toast(msg); else alert('[Toast] ' + msg); }
    function api(url, options) { return fetch(url, options).then(r => { if(!r.ok) return r.json().then(d => { throw new Error(d.detail || d.msg || 'HTTP '+r.status); }); return r.json(); }); }
    function isAdmin() { return window.isAdminUser ? window.isAdminUser() : false; }

    // ---------- 修改地图栏 ----------
    function modifyMapBar() {
        const bar = document.querySelector('#mapView .map-bar');
        if (!bar) return;
        const btns = bar.querySelectorAll('.bar-btn');
        btns.forEach(btn => {
            const txt = btn.textContent.trim();
            if (txt === '＋' || txt === '－') {
                btn.remove();
            }
        });
        const instanceBtn = document.createElement('button');
        instanceBtn.className = 'bar-btn';
        instanceBtn.textContent = '🎬 副本';
        instanceBtn.onclick = function() { openInstanceHome(); };
        bar.appendChild(instanceBtn);
        const earthBtn = document.createElement('button');
        earthBtn.className = 'bar-btn';
        earthBtn.textContent = '🌍 地球';
        earthBtn.onclick = function() { toast('🌍 多元宇宙功能开发中…'); };
        bar.appendChild(earthBtn);
        console.log('[ext] 地图栏已改造');
    }

    // ---------- 覆盖层 ----------
    function createOverlay() {
        const app = document.querySelector('.app');
        const overlay = document.createElement('div');
        overlay.id = 'instanceOverlay';
        overlay.style.cssText = `
            position: absolute; top:0; left:0; right:0; bottom:0; 
            background: #f5f2ef; z-index: 200; display: none; 
            flex-direction: column; overflow: hidden;
            font-family: 'PingFang SC','Microsoft YaHei',sans-serif;
        `;
        overlay.innerHTML = `
            <div id="instanceHeader" style="background:rgba(255,255,255,0.85); backdrop-filter:blur(6px); padding:10px 16px; display:flex; align-items:center; justify-content:space-between; flex-shrink:0; border-bottom:1px solid rgba(0,0,0,0.05);">
                <span style="font-weight:600; font-size:16px; color:#3a3a3a;">🎬 叙事副本</span>
                <div style="display:flex; gap:10px; align-items:center;">
                    <span id="instanceUserDisplay" style="color:#6a6a6a; font-size:13px;"></span>
                    <button onclick="closeInstanceOverlay()" style="background:transparent; border:none; color:#999; font-size:20px; cursor:pointer;">✕</button>
                </div>
            </div>
            <div id="instanceContent" style="flex:1; overflow-y:auto; padding:12px 16px; background:#f5f2ef;"></div>
        `;
        app.appendChild(overlay);

        window.closeInstanceOverlay = async function() {
            // 如果当前有活跃副本，自动暂离
            if (currentInstanceId && instances[currentInstanceId] && instances[currentInstanceId].status === 'active') {
                try {
                    await api('/api/instance/' + currentInstanceId + '/pause', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user: currentUser })
                    });
                    toast('⏸ 已暂离副本，AI 回到现实世界');
                } catch (e) {
                    toast('⚠️ 暂离失败：' + e.message);
                }
            }
            document.getElementById('instanceOverlay').style.display = 'none';
            currentInstanceId = null;
            selectedAi = null;
            selectedOwner = null;
            currentEditingInstance = null;
        };
        window.openInstanceHome = function() {
            currentUser = window.userName || localStorage.getItem('gc_name') || '访客';
            document.getElementById('instanceOverlay').style.display = 'flex';
            document.getElementById('instanceUserDisplay').textContent = currentUser;
            loadInstanceBg();
            loadAllAisAndPublic();
        };
    }

    // ---------- 背景管理 ----------
    function loadInstanceBg() {
        api('/api/instance/bg?user=' + encodeURIComponent(currentUser))
            .then(d => { instanceBg = d.bg || ''; applyBgToSelection(); })
            .catch(() => {});
    }
    function applyBgToSelection() {
        const container = document.querySelector('.ai-select-container');
        if (!container) return;
        const bg = instanceBg || getMainBg();
        container.style.backgroundImage = bg ? `url(${bg})` : 'none';
        container.style.backgroundSize = 'cover';
        container.style.backgroundPosition = 'center';
    }
    function getMainBg() {
        return (window.mapData && window.mapData.room_bg && window.mapData.room_bg['main']) || '';
    }
    window.uploadInstanceBg = function() {
        if (!isAdmin()) { toast('只有站长可以上传背景'); return; }
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = function(e) {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(ev) {
                const dataUrl = ev.target.result;
                api('/api/instance/bg', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user: currentUser, bg: dataUrl })
                }).then(d => {
                    toast('✅ 背景已更新');
                    instanceBg = dataUrl;
                    applyBgToSelection();
                }).catch(err => toast('❌ ' + err.message));
            };
            reader.readAsDataURL(file);
        };
        input.click();
    };

    // ---------- 加载所有AI及公开副本 ----------
    function loadAllAisAndPublic() {
        const content = document.getElementById('instanceContent');
        content.innerHTML = '<div style="text-align:center; color:#999; padding:40px;">⏳ 加载中...</div>';
        const allUserAis = window.mapData && window.mapData.user_ais ? window.mapData.user_ais : {};
        allAis = [];
        for (const [owner, ais] of Object.entries(allUserAis)) {
            ais.forEach(ai => {
                allAis.push({ name: ai, owner: owner, isMine: (owner === currentUser) });
            });
        }
        // 并行请求公开副本
        api('/api/instance/public/all')
            .then(d => {
                publicInstancesMap = d.public_instances || {};
                renderAiSelection();
            })
            .catch(e => {
                publicInstancesMap = {};
                renderAiSelection();
                toast('⚠️ 加载公开副本失败，仅显示自己的AI');
            });
    }

    // ---------- AI选择页 ----------
    function renderAiSelection() {
        const content = document.getElementById('instanceContent');
        const bg = instanceBg || getMainBg();
        const bgStyle = bg ? `background-image: url(${bg}); background-size: cover; background-position: center;` : 'background: #f5f2ef;';
        let html = `
            <div class="ai-select-container" style="position:relative; width:100%; min-height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:20px 16px 30px; ${bgStyle}">
                ${isAdmin() ? `<button onclick="uploadInstanceBg()" style="position:absolute; top:12px; right:16px; background:rgba(255,255,255,0.7); border:1px solid #ddd; border-radius:20px; padding:4px 14px; font-size:12px; cursor:pointer; color:#555; backdrop-filter:blur(4px);">🖼️ 上传背景</button>` : ''}
                <div style="text-align:right; width:100%; max-width:480px; margin-bottom:10px; padding-right:8px;">
                    <div style="font-size:14px; color:#888; letter-spacing:2px; font-weight:300;">选择</div>
                    <div style="font-size:28px; font-weight:700; color:#3a3a3a; line-height:1.2; margin-top:-4px;">你的他</div>
                </div>
                <div style="position:relative; width:100%; max-width:480px; min-height:280px; display:flex; flex-wrap:wrap; justify-content:center; gap:20px 30px; padding:16px 0;">
        `;
        const offsets = [0, 20, -10, 30, 5, 15, -5, 25];
        allAis.forEach((item, index) => {
            const ai = item.name;
            const owner = item.owner;
            const isMine = item.isMine;
            const avatar = (window.avatars && window.avatars[ai]) || '';
            const initial = (ai || '?').charAt(0);
            const offset = offsets[index % offsets.length];
            const label = isMine ? '我' : owner;
            const labelColor = isMine ? '#27ae60' : '#3498db';
            html += `
                <div onclick="selectAi('${esc(ai)}', '${esc(owner)}', ${isMine})" style="cursor:pointer; text-align:center; width:80px; margin-top:${offset}px; transition:transform .2s;" 
                     onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                    <div style="width:80px; height:80px; border-radius:50%; background:${avatar ? 'transparent' : 'rgba(255,255,255,0.3)'}; 
                         backdrop-filter:blur(4px); border:1.5px solid rgba(255,255,255,0.5); box-shadow:0 4px 16px rgba(0,0,0,0.08); 
                         overflow:hidden; margin:0 auto; position:relative; display:flex; align-items:center; justify-content:center;">
                        ${avatar ? `<img src="${avatar}" style="width:100%;height:100%;object-fit:cover;">` : `<span style="font-size:32px;color:#666;">${esc(initial)}</span>`}
                        <div style="position:absolute; bottom:2px; left:20%; right:20%; height:2px; background:linear-gradient(90deg, transparent, #ff6b81, transparent); border-radius:2px; opacity:0.6;"></div>
                    </div>
                    <div style="font-size:14px; color:#444; margin-top:8px; font-weight:500;">${esc(ai)}</div>
                    <div style="font-size:11px; color:${labelColor}; margin-top:-2px;">${esc(label)}</div>
                </div>
            `;
        });
        html += `
                </div>
                <div style="margin-top:20px; font-size:13px; color:#aaa; letter-spacing:1px; text-align:center; border-top:1px solid rgba(0,0,0,0.04); padding-top:16px; width:100%; max-width:480px;">
                    副本世界与现实世界独立存在
                </div>
            </div>
        `;
        content.innerHTML = html;
        content.dataset.page = 'ai-select';
        applyBgToSelection();
    }

    // ---------- 选择AI ----------
    window.selectAi = function(ai, owner, isMine) {
        selectedAi = ai;
        selectedOwner = owner;
        isReadOnly = !isMine;
        if (isReadOnly) {
            const publicList = publicInstancesMap[ai] || [];
            renderPublicLibrary(publicList, owner);
        } else {
            loadInstanceLibrary(ai);
        }
    };

    // ---------- 加载自己的副本库 ----------
    function loadInstanceLibrary(ai) {
        const content = document.getElementById('instanceContent');
        content.innerHTML = '<div style="text-align:center; color:#999; padding:40px;">⏳ 加载副本...</div>';
        api('/api/instances?user=' + encodeURIComponent(currentUser))
            .then(d => {
                const allInst = d.instances || {};
                userTags = d.tags || [];
                const filtered = {};
                for (const [id, inst] of Object.entries(allInst)) {
                    const participants = inst.participants || [];
                    if (participants.some(p => p.type === 'ai' && p.name === ai)) {
                        filtered[id] = inst;
                    }
                }
                instances = filtered;
                renderLibrary();
            })
            .catch(e => {
                content.innerHTML = `<div style="color:#c0392b; text-align:center; padding:30px;">❌ ${esc(e.message)}</div>`;
            });
    }

    // ---------- 渲染自己的副本库 ----------
    function renderLibrary() {
        const content = document.getElementById('instanceContent');
        const allTags = ['全部', ...userTags];
        const filteredIds = Object.keys(instances).filter(id => {
            if (currentFilterTag === '全部') return true;
            return (instances[id].tags || []).includes(currentFilterTag);
        });
        let html = `
            <div style="max-width:960px; margin:0 auto; padding-bottom:20px;">
                <div style="display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-bottom:16px; padding:10px 0; border-bottom:1px solid rgba(0,0,0,0.04);">
                    <span style="font-size:13px; color:#888; margin-right:4px;">🏷️</span>
                    ${allTags.map(tag => `
                        <span onclick="setFilterTag('${esc(tag)}')" style="cursor:pointer; padding:4px 14px; border-radius:20px; font-size:13px; background:${currentFilterTag === tag ? '#d4cdc4' : 'transparent'}; color:${currentFilterTag === tag ? '#333' : '#777'}; border:1px solid ${currentFilterTag === tag ? '#d4cdc4' : '#ddd'}; transition:all .2s;">
                            ${esc(tag)}
                        </span>
                    `).join('')}
                    <span style="flex:1;"></span>
                    <button onclick="createNewInstance()" style="background:#c0392b; color:#fff; border:none; padding:6px 16px; border-radius:20px; font-size:13px; cursor:pointer; box-shadow:0 2px 6px rgba(192,57,43,0.2);">+ 创建副本</button>
                </div>
                <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:16px;">
        `;
        if (filteredIds.length === 0) {
            html += `<div style="grid-column:1/-1; text-align:center; color:#aaa; padding:60px 0;">📭 还没有副本，点击上方创建</div>`;
        } else {
            filteredIds.forEach(id => {
                const inst = instances[id];
                const cover = inst.cover || '';
                const name = inst.name || '未命名';
                const status = inst.status || 'draft';
                const isEnded = status === 'ended';
                const isActive = status === 'active';
                const isPaused = status === 'paused';
                const statusLabel = isActive ? '● 进行中' : (isPaused ? '⏸ 已暂离' : (isEnded ? '✓ 已结束' : ''));
                html += `
                    <div onclick="openInstanceCard('${id}')" style="cursor:pointer; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.04); transition:transform .2s, box-shadow .2s; border:1px solid rgba(0,0,0,0.04);" 
                         onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(0,0,0,0.06)';" 
                         onmouseout="this.style.transform='none'; this.style.boxShadow='0 2px 8px rgba(0,0,0,0.04)';">
                        <div style="aspect-ratio: 3/4; background:${cover ? `url(${cover}) center/cover` : '#eae7e3'}; position:relative;">
                            ${statusLabel ? `<span style="position:absolute; top:8px; right:8px; background:rgba(0,0,0,0.6); color:#fff; padding:2px 10px; border-radius:12px; font-size:11px; backdrop-filter:blur(4px);">${statusLabel}</span>` : ''}
                        </div>
                        <div style="padding:10px 12px 12px;">
                            <div style="font-weight:500; font-size:15px; color:#333; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${esc(name)}</div>
                            ${inst.tags && inst.tags.length ? `<div style="font-size:11px; color:#999; margin-top:2px;">${inst.tags.slice(0,2).map(esc).join(' · ')}</div>` : ''}
                        </div>
                    </div>
                `;
            });
        }
        html += `</div></div>`;
        content.innerHTML = html;
        content.dataset.page = 'library';
    }

    // ---------- 渲染他人AI的公开副本 ----------
    function renderPublicLibrary(publicList, owner) {
        const content = document.getElementById('instanceContent');
        if (!publicList.length) {
            content.innerHTML = `
                <div style="text-align:center; color:#aaa; padding:60px 20px; background:rgba(255,255,255,0.6); border-radius:16px; margin:20px;">
                    <div style="font-size:48px; margin-bottom:16px;">📭</div>
                    <div style="font-size:18px; font-weight:500; color:#555;">${esc(selectedAi)} 还没有公开的已结束副本</div>
                    <div style="font-size:14px; color:#999; margin-top:8px;">只有创建者本人可以创作和编辑</div>
                </div>
            `;
            return;
        }
        let html = `
            <div style="max-width:960px; margin:0 auto;">
                <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px; padding:8px 0; border-bottom:1px solid rgba(0,0,0,0.04);">
                    <span style="font-size:18px; font-weight:600; color:#333;">📖 ${esc(selectedAi)} 的公开副本</span>
                    <span style="font-size:13px; color:#888;">（${esc(owner)} 创作）</span>
                    <span style="flex:1;"></span>
                    <button onclick="backToAiSelection()" style="background:transparent; border:1px solid #ddd; border-radius:20px; padding:4px 14px; font-size:12px; cursor:pointer; color:#555;">← 返回</button>
                </div>
                <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:16px;">
        `;
        publicList.forEach(item => {
            html += `
                <div onclick="viewPublicSummary('${esc(item.id)}', '${esc(item.owner)}')" style="cursor:pointer; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.04); border:1px solid rgba(0,0,0,0.04);">
                    <div style="aspect-ratio: 3/4; background:${item.cover ? `url(${item.cover}) center/cover` : '#eae7e3'};"></div>
                    <div style="padding:10px 12px 12px;">
                        <div style="font-weight:500; font-size:15px; color:#333;">${esc(item.name)}</div>
                        ${item.tags && item.tags.length ? `<div style="font-size:11px; color:#999; margin-top:2px;">${item.tags.slice(0,2).map(esc).join(' · ')}</div>` : ''}
                    </div>
                </div>
            `;
        });
        html += `</div></div>`;
        content.innerHTML = html;
        content.dataset.page = 'public';
    }

    // ---------- 查看公开副本总结 ----------
    window.viewPublicSummary = function(id, owner) {
        const item = publicInstancesMap[selectedAi]?.find(i => i.id === id);
        if (!item || !item.summary) {
            toast('该副本暂无总结');
            return;
        }
        alert(`📖 剧情总结（${item.name}）\n\n${item.summary}`);
    };

    // ---------- 返回AI选择 ----------
    window.backToAiSelection = function() {
        renderAiSelection();
    };

    // ---------- 筛选标签 ----------
    window.setFilterTag = function(tag) {
        currentFilterTag = tag;
        renderLibrary();
    };

    // ---------- 创建新副本 ----------
    window.createNewInstance = function() {
        if (!selectedAi) {
            toast('请先选择一个AI');
            return;
        }
        if (isReadOnly) {
            toast('这是他人的AI，不能创建副本');
            return;
        }
        const name = prompt('给副本起个名字：', '新冒险');
        if (!name || !name.trim()) return;
        const participants = [
            { name: currentUser, type: 'user', profile: '' },
            { name: selectedAi, type: 'ai', profile: '' }
        ];
        api('/api/instance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: currentUser, name: name.trim(), participants: participants })
        }).then(d => {
            toast('✅ 副本已创建');
            loadInstanceLibrary(selectedAi);
        }).catch(e => toast('❌ ' + e.message));
    };

    // ---------- 打开卡片模态框 ----------
        window.openInstanceCard = function(id) {
        if (isReadOnly) {
            toast('只读模式，无法编辑');
            return;
        }
        const inst = instances[id];
        if (!inst) {
            toast('❌ 副本数据不存在，请刷新重试');
            return;
        }
        currentInstanceId = id;
        // 深拷贝时保留 id
        currentEditingInstance = JSON.parse(JSON.stringify(inst));
        currentEditingInstance.id = id;  // ← 新增这行
        try {
            showInstanceModal(currentEditingInstance);
        } catch (err) {
            toast('❌ 打开编辑界面失败：' + err.message);
            console.error(err);
        }
    };

    // ========== 模态框（深色样式 + 四按钮） ==========
    function showInstanceModal(inst) {
        console.log('[DEBUG] showInstanceModal called for', inst.id);
        try {
            const globalUserProfile = (window.mapData && window.mapData.user_profiles && window.mapData.user_profiles[currentUser]) || '';
            const globalAiProfile = (window.mapData && window.mapData.ai_profiles && window.mapData.ai_profiles[currentUser] && window.mapData.ai_profiles[currentUser].persona) || '';

            const participants = inst.participants || [];
            const userPart = participants.find(p => p.type === 'user') || { name: currentUser, profile: '' };
            const aiPart = participants.find(p => p.type === 'ai') || { name: selectedAi, profile: '' };
            const npcs = participants.filter(p => p.type === 'npc') || [];

            if (!selectedAi) {
                toast('⚠️ 未选中AI，请返回重试');
                return;
            }

            const modal = document.createElement('div');
            modal.id = 'instanceModal';
            modal.style.cssText = 'position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.6); z-index:300; display:flex; align-items:center; justify-content:center; backdrop-filter:blur(2px);';
            modal.onclick = function(e) { if(e.target === this) this.remove(); };

            const isEnded = inst.status === 'ended';
            const isActive = inst.status === 'active';
            const isPaused = inst.status === 'paused';

            modal.innerHTML = `
                <div style="background:#0d1a2e; border-radius:16px; width:94%; max-width:600px; max-height:90vh; overflow-y:auto; padding:24px 20px; box-shadow:0 12px 40px rgba(0,0,0,0.6); border:1px solid rgba(80,180,255,0.2); color:#cfe8ff;">
                    <h3 style="margin-top:0; margin-bottom:16px; font-weight:600; display:flex; align-items:center; gap:8px; color:#9fd8ff;">
                        ${isActive ? '🟢' : (isPaused ? '⏸' : (isEnded ? '✅' : '📝'))} ${esc(inst.name)}
                        ${isEnded ? '<span style="font-size:13px; color:#6d8bb0; font-weight:400;">（已结束）</span>' : (isPaused ? '<span style="font-size:13px; color:#f39c12; font-weight:400;">（已暂离）</span>' : '')}
                    </h3>

                    <!-- 封面上传 -->
                    <div style="margin-bottom:12px;">
                        <label style="font-size:13px; color:#7fa8cf; display:block; margin-bottom:4px;">封面图片</label>
                        <div style="display:flex; gap:10px; align-items:center;">
                            <div id="coverPreview" style="width:80px; height:80px; border-radius:8px; background:${inst.cover ? `url(${inst.cover}) center/cover` : '#1d3150'}; flex-shrink:0; border:1px solid #2a4a75;"></div>
                            <input type="file" id="coverFileInput" accept="image/*" style="flex:1; font-size:13px; color:#cfe8ff; background:#13233d; border:1px solid #1d3a5f; border-radius:6px; padding:4px;">
                        </div>
                    </div>

                    <!-- 名称 -->
                    <div style="margin-bottom:12px;">
                        <label style="font-size:13px; color:#7fa8cf; display:block; margin-bottom:4px;">副本名称</label>
                        <input id="editName" class="input" value="${esc(inst.name)}" style="width:100%; border:1px solid #1d3a5f; border-radius:8px; padding:8px 12px; font-size:14px; background:#13233d; color:#e6f1ff;">
                    </div>

                    <!-- 标签 -->
                    <div style="margin-bottom:12px;">
                        <label style="font-size:13px; color:#7fa8cf; display:block; margin-bottom:4px;">标签（逗号分隔）</label>
                        <input id="editTags" class="input" value="${esc((inst.tags || []).join(','))}" style="width:100%; border:1px solid #1d3a5f; border-radius:8px; padding:8px 12px; font-size:14px; background:#13233d; color:#e6f1ff;">
                    </div>

                    <!-- 公开 -->
                    <div style="margin-bottom:12px; display:flex; align-items:center; gap:8px;">
                        <input type="checkbox" id="editPublic" ${inst.public ? 'checked' : ''} style="accent-color:#0e7fd4;">
                        <label for="editPublic" style="font-size:13px; color:#7fa8cf;">公开（他人可查看已结束副本的总结）</label>
                    </div>

                    <!-- 人设 -->
                    <div style="margin-bottom:12px; border-top:1px solid #1d3a5f; padding-top:12px;">
                        <div style="font-size:13px; font-weight:500; color:#9fd8ff; margin-bottom:6px;">👤 用户人设（留空则使用全局人设）</div>
                        <textarea id="editUserProfile" class="input" rows="2" style="width:100%; border:1px solid #1d3a5f; border-radius:8px; padding:8px 12px; font-size:14px; background:#13233d; color:#e6f1ff;">${esc(userPart.profile || '')}</textarea>
                        <div style="font-size:11px; color:#6d8bb0; margin-top:2px;">全局人设：${esc(globalUserProfile || '未设置')}</div>
                    </div>
                    <div style="margin-bottom:12px;">
                        <div style="font-size:13px; font-weight:500; color:#9fd8ff; margin-bottom:6px;">🤖 AI（${esc(selectedAi)}）人设（留空则使用全局人设）</div>
                        <textarea id="editAiProfile" class="input" rows="2" style="width:100%; border:1px solid #1d3a5f; border-radius:8px; padding:8px 12px; font-size:14px; background:#13233d; color:#e6f1ff;">${esc(aiPart.profile || '')}</textarea>
                        <div style="font-size:11px; color:#6d8bb0; margin-top:2px;">全局人设：${esc(globalAiProfile || '未设置')}</div>
                    </div>

                    <!-- NPC -->
                    <div style="margin-bottom:12px; border-top:1px solid #1d3a5f; padding-top:12px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size:13px; font-weight:500; color:#9fd8ff;">NPC 及人设</span>
                            <button onclick="addNpcField()" style="background:transparent; border:1px dashed #2a4a75; border-radius:8px; padding:2px 10px; font-size:12px; cursor:pointer; color:#7fd0ff;">+ 添加NPC</button>
                        </div>
                        <div id="npcContainer">
                            ${npcs.map((n, idx) => `
                                <div class="npc-entry" style="display:flex; gap:8px; margin-top:6px;">
                                    <input class="npc-name" value="${esc(n.name)}" placeholder="名字" style="flex:1; border:1px solid #1d3a5f; border-radius:6px; padding:6px 8px; font-size:13px; background:#13233d; color:#e6f1ff;">
                                    <input class="npc-profile" value="${esc(n.profile || '')}" placeholder="人设" style="flex:2; border:1px solid #1d3a5f; border-radius:6px; padding:6px 8px; font-size:13px; background:#13233d; color:#e6f1ff;">
                                    <button onclick="removeNpc(this)" style="border:none; background:transparent; color:#ff6b6b; cursor:pointer;">✕</button>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <!-- 剧情时间和背景 -->
                    <div style="margin-bottom:12px;">
                        <label style="font-size:13px; color:#7fa8cf; display:block; margin-bottom:4px;">剧情时间/背景设定（如：五千年前，你是司命神明）</label>
                        <textarea id="editTime" class="input" rows="2" style="width:100%; border:1px solid #1d3a5f; border-radius:8px; padding:8px 12px; font-size:14px; background:#13233d; color:#e6f1ff;">${esc(inst.time_setting || '')}</textarea>
                    </div>
                    <div style="margin-bottom:12px;">
                        <label style="font-size:13px; color:#7fa8cf; display:block; margin-bottom:4px;">场景背景描述</label>
                        <textarea id="editBg" class="input" rows="2" style="width:100%; border:1px solid #1d3a5f; border-radius:8px; padding:8px 12px; font-size:14px; background:#13233d; color:#e6f1ff;">${esc(inst.background || '')}</textarea>
                    </div>
                    <div style="margin-bottom:12px;">
                        <label style="font-size:13px; color:#7fa8cf; display:block; margin-bottom:4px;">前情提要</label>
                        <textarea id="editPremise" class="input" rows="3" style="width:100%; border:1px solid #1d3a5f; border-radius:8px; padding:8px 12px; font-size:14px; background:#13233d; color:#e6f1ff;">${esc(inst.premise || '')}</textarea>
                    </div>

                    <!-- 底部四按钮 -->
                    <div style="display:flex; gap:8px; margin-top:12px; flex-wrap:wrap;">
                        <button class="btn green" data-action="save" data-id="${inst.id}" style="flex:1; background:#0e9f6e; color:#fff; border:none; padding:8px; border-radius:8px; cursor:pointer;">💾 保存</button>
                        ${!isEnded ? `<button class="btn" data-action="enter" data-id="${inst.id}" style="flex:1; background:#0e7fd4; color:#fff; border:none; padding:8px; border-radius:8px; cursor:pointer;">▶ 进入</button>` : ''}
                        ${isActive ? `<button class="btn" data-action="pause" data-id="${inst.id}" style="flex:1; background:#f39c12; color:#fff; border:none; padding:8px; border-radius:8px; cursor:pointer;">⏸ 暂离</button>` : ''}
                        <button class="btn red" data-action="delete" data-id="${inst.id}" style="flex:1; background:#c0392b; color:#fff; border:none; padding:8px; border-radius:8px; cursor:pointer;">🗑️ 删除</button>
                        <button class="btn gray" data-action="exit" data-id="${inst.id}" style="flex:1; background:#2a4a75; color:#cfe8ff; border:none; padding:8px; border-radius:8px; cursor:pointer;">✕ 退出</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            // --- 事件委托绑定 ---
            modal.addEventListener('click', function(e) {
                const btn = e.target.closest('button[data-action]');
                if (!btn) return;
                const action = btn.dataset.action;
                const id = btn.dataset.id;
                console.log('[DEBUG] Modal button clicked:', action, id);
                if (!id) {
                    toast('缺少副本ID');
                    return;
                }
                switch (action) {
                    case 'save':
                        saveInstance(id);
                        break;
                    case 'enter':
                        enterInstanceDirect(id);
                        break;
                    case 'pause':
                        pauseInstance(id);
                        break;
                    case 'delete':
                        deleteInstance(id);
                        break;
                    case 'exit':
                        closeModalAndRefresh(id);
                        break;
                    default:
                        toast('未知操作');
                }
            });

            // 封面预览
            const coverInput = modal.querySelector('#coverFileInput');
            if (coverInput) {
                coverInput.addEventListener('change', function(e) {
                    const file = e.target.files[0];
                    if (!file) return;
                    const reader = new FileReader();
                    reader.onload = function(ev) {
                        const preview = modal.querySelector('#coverPreview');
                        if (preview) {
                            preview.style.backgroundImage = `url(${ev.target.result})`;
                            preview.style.backgroundSize = 'cover';
                            preview.style.backgroundPosition = 'center';
                            if (currentEditingInstance) {
                                currentEditingInstance._newCover = ev.target.result;
                            }
                        }
                    };
                    reader.readAsDataURL(file);
                });
            }
        } catch (err) {
            toast('❌ 渲染编辑界面失败：' + err.message);
            console.error(err);
        }
    }

    // ---------- 关闭模态框并刷新库 ----------
    window.closeModalAndRefresh = function(id) {
        console.log('[DEBUG] closeModalAndRefresh called for', id);
        const modal = document.getElementById('instanceModal');
        if (modal) modal.remove();
        toast('已退出编辑');
        currentEditingInstance = null;
        if (isReadOnly) {
            const publicList = publicInstancesMap[selectedAi] || [];
            renderPublicLibrary(publicList, selectedOwner);
        } else {
            loadInstanceLibrary(selectedAi);
        }
    };

    // ---------- NPC 操作 ----------
    window.addNpcField = function() {
        const container = document.getElementById('npcContainer');
        if (!container) return;
        const entry = document.createElement('div');
        entry.className = 'npc-entry';
        entry.style.cssText = 'display:flex; gap:8px; margin-top:6px;';
        entry.innerHTML = `
            <input class="npc-name" placeholder="名字" style="flex:1; border:1px solid #1d3a5f; border-radius:6px; padding:6px 8px; font-size:13px; background:#13233d; color:#e6f1ff;">
            <input class="npc-profile" placeholder="人设" style="flex:2; border:1px solid #1d3a5f; border-radius:6px; padding:6px 8px; font-size:13px; background:#13233d; color:#e6f1ff;">
            <button onclick="removeNpc(this)" style="border:none; background:transparent; color:#ff6b6b; cursor:pointer;">✕</button>
        `;
        container.appendChild(entry);
    };
    window.removeNpc = function(btn) {
        const entry = btn.closest('.npc-entry');
        if (entry) entry.remove();
    };

    // ---------- 保存 ----------
    window.saveInstance = function(id) {
        console.log('[DEBUG] saveInstance called for', id);
        const modal = document.getElementById('instanceModal');
        if (!modal) { toast('模态框不存在'); return; }
        const inst = currentEditingInstance;
        if (!inst || inst.id !== id) { toast('❌ 编辑数据丢失，请重新打开'); return; }
        try {
            const coverInput = modal.querySelector('#coverFileInput');
            let cover = inst.cover || '';
            if (inst._newCover) cover = inst._newCover;
            const name = modal.querySelector('#editName')?.value?.trim() || '';
            const tags = modal.querySelector('#editTags')?.value?.split(',').map(s => s.trim()).filter(Boolean) || [];
            const isPublic = modal.querySelector('#editPublic')?.checked || false;
            const userProfile = modal.querySelector('#editUserProfile')?.value || '';
            const aiProfile = modal.querySelector('#editAiProfile')?.value || '';
            const timeSetting = modal.querySelector('#editTime')?.value || '';
            const background = modal.querySelector('#editBg')?.value || '';
            const premise = modal.querySelector('#editPremise')?.value || '';

            const npcEntries = modal.querySelectorAll('.npc-entry');
            const npcs = [];
            npcEntries.forEach(entry => {
                const nameInput = entry.querySelector('.npc-name');
                const profInput = entry.querySelector('.npc-profile');
                if (nameInput && nameInput.value.trim()) {
                    npcs.push({ name: nameInput.value.trim(), type: 'npc', profile: profInput ? profInput.value : '' });
                }
            });

            const participants = [
                { name: currentUser, type: 'user', profile: userProfile },
                { name: selectedAi, type: 'ai', profile: aiProfile },
                ...npcs
            ];

            const body = {
                user: currentUser,
                name: name || '未命名',
                cover: cover,
                tags: tags,
                public: isPublic,
                time_setting: timeSetting,
                background: background,
                premise: premise,
                participants: participants
            };

            toast('⏳ 正在保存...');
            api('/api/instance/' + id, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            }).then(() => {
                toast('✅ 副本已保存');
                if (modal) modal.remove();
                currentEditingInstance = null;
                loadInstanceLibrary(selectedAi);
            }).catch(e => {
                toast('❌ 保存失败：' + e.message);
                console.error(e);
            });
        } catch (err) {
            toast('❌ 保存异常：' + err.message);
            console.error(err);
        }
    };

    // ---------- 进入副本 ----------
    window.enterInstanceDirect = function(id) {
        console.log('[DEBUG] enterInstanceDirect called for', id);
        let inst = currentEditingInstance;
        if (!inst || inst.id !== id) inst = instances[id];
        if (!inst) { toast('❌ 副本数据不存在'); return; }
        if (inst.status === 'ended') { toast('该副本已结束，无法进入'); return; }

        // 如果已经是 active，直接进入聊天（不调用 API）
        if (inst.status === 'active') {
            const modal = document.getElementById('instanceModal');
            if (modal) modal.remove();
            currentEditingInstance = null;
            currentInstanceId = id;
            renderChatRoom(inst.chat_history || [], {
                name: inst.name,
                time_setting: inst.time_setting,
                background: inst.background,
                premise: inst.premise,
                participants: inst.participants
            });
            return;
        }

        // 否则调用 enter API 激活
        const modal = document.getElementById('instanceModal');
        if (modal) modal.remove();
        currentEditingInstance = null;
        toast('⏳ 进入副本...');
        api('/api/instance/' + id + '/enter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: currentUser })
        }).then(d => {
            if (instances[id]) {
                instances[id].chat_history = d.chat_history || [];
                instances[id].status = 'active';
            } else {
                instances[id] = {
                    ...inst,
                    chat_history: d.chat_history || [],
                    status: 'active'
                };
            }
            currentInstanceId = id;
            renderChatRoom(d.chat_history || [], d.settings);
        }).catch(e => {
            toast('❌ 进入失败：' + e.message);
            console.error(e);
        });
    };

    // ---------- 暂离副本 ----------
    window.pauseInstance = function(id) {
        console.log('[DEBUG] pauseInstance called for', id);
        if (!id) { toast('⚠️ 缺少副本ID'); return; }
        const modal = document.getElementById('instanceModal');
        toast('⏸ 暂离副本...');
        api('/api/instance/' + id + '/pause', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: currentUser })
        }).then(() => {
            toast('✅ 已暂离，AI 回到现实世界');
            if (modal) modal.remove();
            currentEditingInstance = null;
            // 刷新图鉴
            if (isReadOnly) {
                const publicList = publicInstancesMap[selectedAi] || [];
                renderPublicLibrary(publicList, selectedOwner);
            } else {
                loadInstanceLibrary(selectedAi);
            }
        }).catch(e => {
            toast('❌ 暂离失败：' + e.message);
            console.error(e);
        });
    };

    // ---------- 删除副本 ----------
    window.deleteInstance = function(id) {
        console.log('[DEBUG] deleteInstance called for', id);
        if (!confirm('确定删除这个副本？所有内容将丢失！')) return;
        const modal = document.getElementById('instanceModal');
        toast('⏳ 删除中...');
        api('/api/instance/' + id + '?user=' + encodeURIComponent(currentUser), {
            method: 'DELETE'
        }).then(() => {
            toast('🗑️ 副本已删除');
            if (modal) modal.remove();
            currentEditingInstance = null;
            loadInstanceLibrary(selectedAi);
        }).catch(e => {
            toast('❌ 删除失败：' + e.message);
            console.error(e);
        });
    };

    // ---------- 聊天界面（含暂离按钮） ----------
    function renderChatRoom(history, settings) {
        const content = document.getElementById('instanceContent');
        let inst = instances[currentInstanceId];
        if (!inst) {
            if (currentEditingInstance && currentEditingInstance.id === currentInstanceId) {
                inst = currentEditingInstance;
            } else if (settings && settings.name) {
                inst = {
                    id: currentInstanceId,
                    name: settings.name || '未命名',
                    time_setting: settings.time_setting || '',
                    background: settings.background || '',
                    premise: settings.premise || '',
                    participants: settings.participants || [],
                    chat_history: history || []
                };
                instances[currentInstanceId] = inst;
            } else {
                toast('副本数据丢失，请返回重试');
                if (isReadOnly) {
                    const publicList = publicInstancesMap[selectedAi] || [];
                    renderPublicLibrary(publicList, selectedOwner);
                } else {
                    loadInstanceLibrary(selectedAi);
                }
                return;
            }
        }
        if (history && history.length > 0) inst.chat_history = history;
        else if (!inst.chat_history) inst.chat_history = [];

        content.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-shrink:0; background:rgba(255,255,255,0.8); padding:8px 12px; border-radius:8px;">
                <div>
                    <span onclick="backToLibraryFromChat()" style="cursor:pointer; color:#3498db; font-size:14px; margin-right:12px;">← 返回</span>
                    <span style="font-weight:600; font-size:16px; color:#333;">${esc(inst.name)}</span>
                    <span style="color:#888; font-size:12px; margin-left:8px;">${esc(inst.time_setting || '')}</span>
                </div>
                <div>
                    <button class="btn" onclick="pauseInstance('${currentInstanceId}')" style="background:#f39c12; color:#fff; border:none; padding:4px 12px; border-radius:6px; cursor:pointer; font-size:12px;">⏸ 暂离</button>
                    <button class="btn red" onclick="endInstance('${currentInstanceId}')" style="background:#c0392b; color:#fff; border:none; padding:4px 12px; border-radius:6px; cursor:pointer; font-size:12px;">🏁 结束剧情</button>
                    <button class="btn gray" onclick="closeInstanceOverlay()" style="background:#ddd; color:#333; border:none; padding:4px 12px; border-radius:6px; cursor:pointer; font-size:12px; margin-left:6px;">✕ 关闭</button>
                </div>
            </div>
            <div style="margin-bottom:8px; display:flex; gap:10px; font-size:12px; color:#777; flex-wrap:wrap; background:rgba(255,255,255,0.6); padding:6px 12px; border-radius:8px;">
                <span>📖 ${esc(inst.background || '无背景')}</span>
                <span>📝 ${esc(inst.premise || '无前情')}</span>
                <span onclick="setChatBg()" style="cursor:pointer; color:#3498db;">🖼️ 设背景</span>
            </div>
            <div id="instanceMsgArea" style="flex:1; overflow-y:auto; padding:10px; background:#f5f2ef; border-radius:8px; min-height:300px; background-size:cover; background-position:center;">
                ${(inst.chat_history || []).length ? inst.chat_history.map(m => `
                    <div style="display:flex; margin-bottom:10px; ${m.sender === currentUser ? 'justify-content:flex-end;' : ''}">
                        <div style="max-width:75%; padding:8px 14px; border-radius:10px; background:${m.sender === currentUser ? '#d4cdc4' : '#ffffff'}; color:#333; word-break:break-word; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                            <div style="font-size:11px; color:#888; margin-bottom:2px;">${esc(m.sender)}</div>
                            ${esc(m.content)}
                        </div>
                    </div>
                `).join('') : '<div style="color:#aaa; text-align:center; padding:40px;">✨ 空荡荡的，开始你的冒险吧...</div>'}
            </div>
            <div style="display:flex; gap:8px; margin-top:8px; flex-shrink:0;">
                <input id="instanceChatInput" style="flex:1; border:1px solid #ddd; border-radius:8px; padding:8px 12px; background:#fff; color:#333; outline:none;" placeholder="说点什么…" onkeydown="if(event.key==='Enter') sendInstanceMsg()">
                <button class="btn" onclick="sendInstanceMsg()" style="background:#3498db; color:#fff; border:none; padding:8px 16px; border-radius:8px; cursor:pointer;">发送</button>
            </div>
        `;
        const area = document.getElementById('instanceMsgArea');
        if (area) area.scrollTop = area.scrollHeight;
    }

    // ---------- 聊天相关辅助函数 ----------
    window.backToLibraryFromChat = function() {
        if (isReadOnly) {
            const publicList = publicInstancesMap[selectedAi] || [];
            renderPublicLibrary(publicList, selectedOwner);
        } else {
            loadInstanceLibrary(selectedAi);
        }
        currentInstanceId = null;
    };
    window.setChatBg = function() {
        const url = prompt('输入背景图片URL：');
        if (url) document.getElementById('instanceMsgArea').style.backgroundImage = 'url(' + url + ')';
    };
    window.sendInstanceMsg = function() {
        const input = document.getElementById('instanceChatInput');
        const content = input.value.trim();
        if (!content || !currentInstanceId) return;
        input.value = '';
        toast('⏳ 发送中...');
        api('/api/instance/' + currentInstanceId + '/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: currentUser, content: content })
        }).then(() => {
            setTimeout(refreshInstanceChat, 500);
            setTimeout(refreshInstanceChat, 2000);
        }).catch(e => {
            toast('❌ 发送失败：' + e.message);
            console.error(e);
        });
    };
    function refreshInstanceChat() {
        if (!currentInstanceId) return;
        api('/api/instances?user=' + encodeURIComponent(currentUser))
            .then(d => {
                const inst = d.instances[currentInstanceId];
                if (inst) {
                    instances = d.instances;
                    const area = document.getElementById('instanceMsgArea');
                    if (area) {
                        const hist = inst.chat_history || [];
                        area.innerHTML = hist.length ? hist.map(m => `
                            <div style="display:flex; margin-bottom:10px; ${m.sender === currentUser ? 'justify-content:flex-end;' : ''}">
                                <div style="max-width:75%; padding:8px 14px; border-radius:10px; background:${m.sender === currentUser ? '#d4cdc4' : '#ffffff'}; color:#333; word-break:break-word; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                                    <div style="font-size:11px; color:#888; margin-bottom:2px;">${esc(m.sender)}</div>
                                    ${esc(m.content)}
                                </div>
                            </div>
                        `).join('') : '<div style="color:#aaa; text-align:center; padding:40px;">✨ 空荡荡的...</div>';
                        area.scrollTop = area.scrollHeight;
                    }
                }
            }).catch(() => {});
    }
    window.endInstance = function(id) {
        if (!confirm('结束剧情冒险？将生成总结并传送 AI 回住宅。')) return;
        toast('⏳ 生成总结中...');
        api('/api/instance/' + id + '/end', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: currentUser })
        }).then(d => {
            toast('✅ 剧情结束！AI 已传送回住宅。');
            alert('📖 剧情总结：\n\n' + d.summary);
            currentInstanceId = null;
            if (isReadOnly) {
                const publicList = publicInstancesMap[selectedAi] || [];
                renderPublicLibrary(publicList, selectedOwner);
            } else {
                loadInstanceLibrary(selectedAi);
            }
        }).catch(e => {
            toast('❌ 结束失败：' + e.message);
            console.error(e);
        });
    };

    // ---------- 外部查看他人副本 ----------
    window.viewUserInstances = function(targetUser) {
        if (!targetUser || targetUser === currentUser) {
            toast('输入要查看的用户名');
            return;
        }
        api('/api/instance/public/' + encodeURIComponent(targetUser))
            .then(d => {
                const insts = d.instances || {};
                const keys = Object.keys(insts);
                if (!keys.length) {
                    toast('该用户还没有公开的已结束副本');
                    return;
                }
                let msg = '📚 ' + targetUser + ' 的公开副本：\n';
                keys.forEach(k => {
                    const i = insts[k];
                    msg += `\n【${i.name}】\n${i.summary || '（无总结）'}\n`;
                });
                alert(msg);
            }).catch(e => toast('❌ ' + e.message));
    };

    // ---------- 初始化 ----------
    function init() {
        modifyMapBar();
        createOverlay();
        console.log('[ext] 副本插件 v9 加载完成（修复进入/暂离逻辑）');
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();