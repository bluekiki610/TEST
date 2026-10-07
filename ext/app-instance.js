// app-instance.js - 副本系统 v13（返回首页=暂离事务确认 + 进入/重激活以服务器状态为准 + 卡片暂停角标 + 聊天背景存文件）
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
    let thinkingActive = false;   // 「AI 正在思考」状态（独立于 DOM，重绘后保持）

    // ---------- 工具函数 ----------
    function esc(s) { return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
    function toast(msg) { if (window.toast) window.toast(msg); else alert('[Toast] ' + msg); }
    function api(url, options) { return fetch(url, options).then(r => { if(!r.ok) return r.json().then(d => { throw new Error(d.detail || d.msg || 'HTTP '+r.status); }); return r.json(); }); }
    function isAdmin() { return window.isAdminUser ? window.isAdminUser() : false; }
    function escAttr(s) { return esc(s).replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
    function isAssistantMsg(m) {
        if (!m) return false;
        if (m.role === 'assistant') return true;
        if (m.role) return false;
        // 兼容没有 role 的历史数据
        return !!(m.sender && m.sender !== currentUser && m.sender !== 'system');
    }
    function countAssistantMsgs(hist) {
        return (hist || []).filter(isAssistantMsg).length;
    }

    // ==================================================================
    // 副本聊天页外壳样式
    // 复用住宅聊天（index.html）的 .msg / .msg.me / .bubble / .avatar / .meta
    // 全局样式，这里只补副本聊天页自己需要的壳层（顶栏 / 状态条 / 底部输入区）。
    // 结构：InstanceChatShell > Header / StoryHeader / MessageList / Composer
    // ==================================================================
    function injectInstanceChatStyles() {
        if (document.getElementById('instanceChatStyles')) return;
        const st = document.createElement('style');
        st.id = 'instanceChatStyles';
        st.textContent = `
            .inst-shell { display:flex; flex-direction:column; flex:1; min-height:0; height:100%; background:#0f1a2e; }
            /* 聊天页全屏：隐藏外层「叙事副本 / 用户名」头部 */
            #instanceOverlay.inst-chatting #instanceHeader { display:none !important; }
            /* 顶排：← 返回首页 + 副本名称（对应住宅的房间名位置） */
            .inst-top { display:flex; align-items:center; gap:8px; padding:8px 10px 6px; background:#0d1a2e; flex-shrink:0; }
            .inst-top .inst-back { color:#7fd0ff; font-size:13px; cursor:pointer; flex-shrink:0; padding:4px 8px; border-radius:8px; background:rgba(80,180,255,.12); border:1px solid rgba(80,180,255,.25); white-space:nowrap; }
            .inst-top .inst-back:hover { background:rgba(80,180,255,.26); }
            .inst-top .inst-title { font-size:15px; font-weight:600; color:#e6f1ff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; }
            .inst-top .inst-sub { font-size:11px; color:#6d8bb0; white-space:nowrap; flex-shrink:0; margin-left:auto; }
            /* 第二排：功能键，一行放得下、不溢出画框 */
            .inst-bar { display:flex; gap:5px; padding:0 8px 7px; background:#0d1a2e; border-bottom:1px solid rgba(80,180,255,.15); flex-shrink:0; }
            .inst-bar .inst-hbtn { flex:1 1 0; min-width:0; text-align:center; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
            .inst-hbtn { background:rgba(80,180,255,.15); border:1px solid rgba(80,180,255,.3); color:#9fd8ff; padding:6px 4px; border-radius:8px; font-size:11.5px; cursor:pointer; }
            .inst-hbtn:hover { background:rgba(80,180,255,.28); }
            .inst-hbtn.warn { color:#ffd166; border-color:rgba(255,209,102,.35); background:rgba(255,209,102,.12); }
            .inst-hbtn.danger { color:#ff9d9d; border-color:rgba(255,107,107,.35); background:rgba(255,107,107,.12); }
            .inst-hbtn.tts-on { background:rgba(14,127,212,.4); color:#fff; border-color:#0e7fd4; }
            .inst-hbtn:disabled { opacity:.4; cursor:not-allowed; }
            /* 背景层不滚动（固定铺满），消息层在上方滚动 */
            .inst-chatarea { flex:1; min-height:0; position:relative; display:flex; flex-direction:column; background-color:#0f1a2e; background-size:cover; background-position:center; background-repeat:no-repeat; }
            #instanceMsgArea { flex:1; min-height:0; overflow-y:auto; padding:12px; background:transparent; }
            .inst-story { display:flex; justify-content:center; margin-bottom:16px; }
            .inst-story .body { max-width:82%; background:rgba(19,35,61,.92); border:1px solid rgba(80,180,255,.22); border-left:3px solid #7fd0ff; border-radius:12px; padding:10px 14px; }
            .inst-story .cap { font-size:12px; color:#7fd0ff; font-weight:600; margin-bottom:5px; letter-spacing:.6px; }
            .inst-story .txt { font-size:13.5px; line-height:1.75; color:#bcd6f0; white-space:pre-wrap; word-break:break-word; }
            .inst-thinking { display:flex; align-items:center; gap:7px; color:#6d8bb0; font-size:12px; padding:6px 4px 10px; }
            .inst-thinking .dot { width:6px; height:6px; border-radius:50%; background:#7fd0ff; animation:instPulse 1.1s ease-in-out infinite; flex-shrink:0; }
            @keyframes instPulse { 0%,100%{ opacity:.25; transform:scale(.8);} 50%{ opacity:1; transform:scale(1.15);} }
            .inst-err { margin:0 0 10px; padding:8px 11px; border-radius:10px; background:rgba(13,26,46,.94); border:1px solid rgba(255,107,107,.5); color:#ffb3b3; font-size:12px; line-height:1.6; }
            .inst-composer { background:#0d1a2e; border-top:1px solid rgba(80,180,255,.15); padding:7px 8px; flex-shrink:0; }
            .inst-composer .row { display:flex; align-items:center; gap:6px; }
            #instanceMsgInput { flex:1 1 auto; border:1px solid #1d3a5f; border-radius:20px; padding:9px 14px; font-size:15px; outline:none; background:#13233d; color:#e6f1ff; min-width:0; }
            #instanceMsgInput::placeholder { color:#5b7aa0; }
            #instanceSendBtn { background:#0e7fd4; color:#fff; border:none; border-radius:20px; padding:9px 18px; font-size:14px; cursor:pointer; flex-shrink:0; }
            #instanceSendBtn:disabled { background:#2a4a75; color:#7f9dc0; cursor:not-allowed; }
            /* 模型 chip：只显示提供商图标/首字母，长按或悬停看全名 */
            .inst-model-chip { width:38px; height:38px; border-radius:50%; flex-shrink:0; background:#13233d; border:1px solid rgba(80,180,255,.35); color:#9fd8ff; font-size:15px; font-weight:600; cursor:pointer; display:flex; align-items:center; justify-content:center; padding:0; }
            .inst-model-chip:hover { background:#1a2f52; }
            .inst-model-chip:disabled { opacity:.45; cursor:not-allowed; }
            .inst-model-opt { padding:10px 12px; border-radius:10px; background:#13233d; border:1px solid rgba(80,180,255,.15); color:#cfe8ff; font-size:13.5px; cursor:pointer; margin-bottom:6px; }
            .inst-model-opt:hover { background:#1a2f52; }
            .inst-model-opt.active { border-color:#0e7fd4; color:#fff; }
            .inst-modal-mask { position:fixed; inset:0; background:rgba(3,8,18,.78); z-index:400; display:flex; align-items:center; justify-content:center; padding:20px; }
            .inst-modal { background:#0d1a2e; border:1px solid rgba(80,180,255,.25); border-radius:14px; width:100%; max-width:600px; max-height:85vh; overflow-y:auto; padding:20px; box-shadow:0 12px 44px rgba(0,0,0,.6); }
            .inst-modal h2 { margin:0 0 4px; font-size:17px; color:#9fd8ff; }
            .inst-modal h3 { margin:16px 0 6px; font-size:14px; color:#7fa8cf; }
            .inst-modal .muted { color:#6d8bb0; font-size:12px; }
            .inst-modal .txt { color:#cfe8ff; line-height:1.8; white-space:pre-wrap; word-break:break-word; font-size:14px; }
            .inst-modal .mfoot { text-align:center; margin-top:18px; }
            .inst-modal .mclose { background:#0e7fd4; color:#fff; border:none; padding:8px 24px; border-radius:8px; cursor:pointer; font-size:14px; }
        `;
        document.head.appendChild(st);
    }

    // ==================================================================
    // 语音接口（P1 预留 + 与住宅朗读一致的实现）
    // 路线：浏览器 speechSynthesis（与 index.html 的 speakNewMessages 同源）
    // 不引入第二套 TTS provider，不把任何 Key 写进 instance / localStorage。
    // ==================================================================
    let autoVoiceEnabled = false;
    let lastSpokenKey = '';

    function voiceSupported() {
        return typeof window !== 'undefined' && 'speechSynthesis' in window;
    }
    window.getAutoVoiceEnabled = function() { return autoVoiceEnabled; };
    window.setAutoVoiceEnabled = function(enabled) {
        autoVoiceEnabled = !!enabled;
        updateVoiceToggleUI();
        return autoVoiceEnabled;
    };
    window.toggleAutoVoice = function() {
        if (!voiceSupported()) { toast('当前浏览器不支持语音朗读'); return false; }
        const next = !autoVoiceEnabled;
        window.setAutoVoiceEnabled(next);
        if (next) toast('🔊 已开启 AI 回复自动朗读');
        else { try { window.speechSynthesis.cancel(); } catch (e) {} toast('🔇 已关闭自动朗读'); }
        return next;
    };

    function updateVoiceToggleUI() {
        const btn = document.getElementById('instanceVoiceBtn');
        if (!btn) return;
        const ok = voiceSupported();
        btn.disabled = !ok;
        btn.classList.toggle('tts-on', ok && autoVoiceEnabled);
        btn.textContent = (ok && autoVoiceEnabled) ? '🔊 语音' : '🔇 语音';
        btn.title = ok
            ? (autoVoiceEnabled ? '自动朗读 AI 回复：开（点击关闭）' : '自动朗读 AI 回复：关（点击开启）')
            : '当前浏览器不支持语音朗读';
    }

    // 朗读单条消息（住宅手动播放 / 副本自动+手动都走这里）
    function speakText(text) {
        if (!voiceSupported() || !text) return;
        try {
            const voices = window.speechSynthesis.getVoices();
            if (voices.length === 0) {
                window.speechSynthesis.onvoiceschanged = function() {
                    window.speechSynthesis.onvoiceschanged = null;
                    setTimeout(function() { speakText(text); }, 120);
                };
                window.speechSynthesis.getVoices();
                return;
            }
            window.speechSynthesis.cancel();
            const u = new SpeechSynthesisUtterance(text);
            u.lang = 'zh-CN';
            u.rate = 0.9;
            window.speechSynthesis.speak(u);
        } catch (e) {
            console.warn('[instance] 朗读失败:', e);
        }
    }

    window.playMessageVoice = function(msgOrText) {
        if (!voiceSupported()) { toast('当前浏览器不支持语音朗读'); return; }
        if (!msgOrText) return;
        const text = (typeof msgOrText === 'string')
            ? msgOrText
            : ((msgOrText.sender ? msgOrText.sender + '说：' : '') + (msgOrText.content || ''));
        if (!text.trim()) return;
        speakText(text);
    };

    // AI 回复写入后，若开启了自动朗读则朗读最新一条
    function maybeAutoSpeak(history) {
        if (!autoVoiceEnabled || !voiceSupported()) return;
        const hist = history || [];
        for (let i = hist.length - 1; i >= 0; i--) {
            if (isAssistantMsg(hist[i])) {
                const key = hist[i].sender + '|' + hist[i].content;
                if (key === lastSpokenKey) return;
                lastSpokenKey = key;
                window.playMessageVoice(hist[i]);
                return;
            }
        }
    }

    // ==================================================================
    // 模型切换接口（P1 预留）
    // 只读取用户「设置 → 模型与服务」里已保存的 provider / model，
    // 不新建 instance_ai_keys，不把 Key 存进 instance / chat_history /
    // localStorage，也不修改 data["ai_keys"] 结构。
    // 选择结果通过每次 /message 请求的 model_override 字段传给后端；
    // 后端 call_llm 目前只读 ai_keys[owner].model，因此该字段需要
    // ext_ai.py 侧配合（本次未改后端，属于预留接口）。
    // ==================================================================
    let currentInstanceModel = '';

    function loadUserModelConfig() {
        if (!currentUser) return Promise.resolve(null);
        return api('/api/ai/key?user=' + encodeURIComponent(currentUser))
            .then(d => (d && d.has_key) ? d : null)
            .catch(() => null);
    }

    function providerLabel(p) {
        return ({ deepseek: 'DeepSeek', siliconflow: '硅基流动', glm: 'GLM' })[p] || (p || '默认');
    }
    // chip 上只显示「提供商图标/首字母」
    function providerInitial(p) {
        return ({ deepseek: 'D', siliconflow: '硅', glm: 'G' })[p] || (String(p || '?').charAt(0).toUpperCase() || '?');
    }

    let userModelCfg = null;
    let userModelCfgLoaded = false;

    function updateModelChipUI() {
        const chip = document.getElementById('instanceModelChip');
        if (!chip) return;
        if (!userModelCfg) {
            chip.textContent = '?';
            chip.disabled = true;
            chip.title = '未配置模型：请到「设置 → 模型与服务」填写 API Key';
            return;
        }
        const provider = userModelCfg.provider || 'deepseek';
        chip.disabled = false;
        chip.textContent = providerInitial(provider);
        chip.title = providerLabel(provider) + (currentInstanceModel ? (' · ' + currentInstanceModel) : ' · 默认模型');
    }

    function renderModelTools() {
        // 同一会话内只查一次，避免每次进副本聊天都打一次接口
        if (userModelCfgLoaded) { updateModelChipUI(); return; }
        loadUserModelConfig().then(cfg => {
            userModelCfg = cfg;
            userModelCfgLoaded = true;
            currentInstanceModel = cfg ? (cfg.model || '') : '';
            updateModelChipUI();
        });
    }

    // 点模型 chip → 弹出选择（只用设置里已保存的配置，不新建 Key 系统）
    window.openInstanceModelPicker = function() {
        if (!userModelCfg) {
            toast('未配置模型：请到「设置 → 模型与服务」填写 API Key');
            return;
        }
        const provider = userModelCfg.provider || 'deepseek';
        const saved = userModelCfg.model || '';
        const mask = document.createElement('div');
        mask.className = 'inst-modal-mask';
        mask.onclick = function(e) { if (e.target === mask) mask.remove(); };
        const opt = (value, label, active) => (
            '<div class="inst-model-opt' + (active ? ' active' : '') + '" data-v="' + escAttr(value) + '">' +
                label + (active ? ' ✓' : '') +
            '</div>'
        );
        mask.innerHTML =
            '<div class="inst-modal" style="max-width:420px;">' +
                '<h2>🔀 选择模型</h2>' +
                '<div class="muted">使用你「设置 → 模型与服务」里已保存的 ' + esc(providerLabel(provider)) + ' 配置，不新建 Key。</div>' +
                '<h3>模型</h3>' +
                (saved ? opt(saved, '已保存：' + esc(saved), currentInstanceModel === saved) : '') +
                opt('', esc(providerLabel(provider)) + ' 默认模型', !currentInstanceModel) +
                '<div class="mfoot"><button class="mclose">关闭</button></div>' +
            '</div>';
        mask.querySelector('.mclose').onclick = function() { mask.remove(); };
        mask.querySelectorAll('.inst-model-opt').forEach(el => {
            el.onclick = function() {
                currentInstanceModel = el.dataset.v || '';
                mask.remove();
                updateModelChipUI();
                toast(currentInstanceModel ? ('已切换模型：' + currentInstanceModel) : '已切回默认模型');
            };
        });
        document.body.appendChild(mask);
    };

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
            // 退出整个副本模块 = 回到现实世界。
            // 若此时正在副本聊天页，先暂离（已暂离/已结束也算成功，不卡住）。
            if (currentInstanceId) {
                const res = await doPauseInstance(currentInstanceId);
                if (res && res.ok) toast('⏸ 已暂离副本，AI 回到现实世界');
            }
            const ov = document.getElementById('instanceOverlay');
            if (ov) {
                ov.style.display = 'none';
                ov.classList.remove('inst-chatting');
            }
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

    // ---------- 副本内容区布局模式切换 ----------
    function setContentScrollable() {
        const c = document.getElementById('instanceContent');
        if (!c) return;
        c.style.display = 'block';
        c.style.flexDirection = '';
        c.style.height = '';
        c.style.overflowY = 'auto';
        c.style.padding = '12px 16px';
        // 离开聊天页 → 恢复外层头部（AI 选择 / 副本库 / 公开副本都需要它）
        const overlay = document.getElementById('instanceOverlay');
        if (overlay) overlay.classList.remove('inst-chatting');
    }
    function setContentChatMode() {
        const c = document.getElementById('instanceContent');
        if (!c) return;
        c.style.display = 'flex';
        c.style.flexDirection = 'column';
        c.style.height = '100%';
        c.style.overflowY = 'hidden';
        // 聊天页全屏：隐藏外层「叙事副本 / 用户名」头部，去掉内边距
        c.style.padding = '0';
        const overlay = document.getElementById('instanceOverlay');
        if (overlay) overlay.classList.add('inst-chatting');
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

        function buildAiList() {
            const allUserAis =
                window.mapData && window.mapData.user_ais
                    ? window.mapData.user_ais
                    : {};

            allAis = [];

            for (const [owner, ais] of Object.entries(allUserAis)) {
                if (!Array.isArray(ais)) continue;
                ais.forEach(ai => {
                    allAis.push({
                        name: ai,
                        owner: owner,
                        isMine: (owner === currentUser)
                    });
                });
            }
        }

        function renderAfterMap() {
            buildAiList();
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

        // 已经有 AI 数据，直接用
        if (
            window.mapData &&
            window.mapData.user_ais &&
            Object.keys(window.mapData.user_ais).length > 0
        ) {
            renderAfterMap();
            return;
        }

        // 地图数据尚未准备好，主动重新取一次
        api('/api/map')
            .then(d => {
                if (d && typeof d === 'object') {
                    window.mapData = d;
                }
                renderAfterMap();
            })
            .catch(e => {
                // 兜底：即使地图接口失败，也不卡死
                buildAiList();
                api('/api/instance/public/all')
                    .then(d => {
                        publicInstancesMap = d.public_instances || {};
                        renderAiSelection();
                    })
                    .catch(() => {
                        publicInstancesMap = {};
                        renderAiSelection();
                    });
            });
    }

    // ---------- AI选择页 ----------
    function renderAiSelection() {
        setContentScrollable();
        // 回到选择页说明已离开副本聊天，清掉残留的聊天态
        currentInstanceId = null;
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
        // 回到副本库说明已离开副本聊天，清掉残留的聊天态
        currentInstanceId = null;
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
        setContentScrollable();
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
                // 暂停状态要一眼可见：固定在封面右上角，用醒目配色
                const badgeBg = isPaused ? 'rgba(243,156,18,.92)'
                    : (isActive ? 'rgba(39,174,96,.88)' : 'rgba(0,0,0,0.6)');
                const badgeStyle = `position:absolute; top:8px; right:8px; background:${badgeBg}; color:#fff; padding:4px 10px; border-radius:12px; font-size:11.5px; font-weight:600; backdrop-filter:blur(4px);`;
                html += `
                    <div onclick="openInstanceCard('${id}')" style="cursor:pointer; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.04); transition:transform .2s, box-shadow .2s; border:1px solid rgba(0,0,0,0.04);" 
                         onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(0,0,0,0.06)';" 
                         onmouseout="this.style.transform='none'; this.style.boxShadow='0 2px 8px rgba(0,0,0,0.04)';">
                        <div style="aspect-ratio: 3/4; background:${cover ? `url(${cover}) center/cover` : '#eae7e3'}; position:relative;">
                            ${statusLabel ? `<span style="${badgeStyle}">${statusLabel}</span>` : ''}
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
        setContentScrollable();
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

    // ---------- 查看公开副本（阅读器模式） ----------
    window.viewPublicSummary = function(id, owner) {
        const item = publicInstancesMap[selectedAi]?.find(i => i.id === id);
        if (!item) { toast('副本不存在'); return; }
        const chapters = item.chapters || [];
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.7); z-index:400; display:flex; align-items:center; justify-content:center; padding:20px;';
        wrapper.onclick = function(e) { if (e.target === wrapper) wrapper.remove(); };
        wrapper.innerHTML = `
            <div style="background:#f5f2ef; border-radius:16px; width:100%; max-width:600px; max-height:85vh; overflow-y:auto; padding:24px; position:relative;">
                <h2 style="margin:0 0 8px;">📖 ${esc(item.name || '未命名副本')}</h2>
                <div style="color:#888; font-size:13px; margin-bottom:16px;">作者：${esc(owner || '')}</div>
                <hr style="border:none; border-top:1px solid #ddd; margin:16px 0;">
                ${chapters.length ? chapters.map(c => `
                    <div style="margin-bottom:18px;">
                        <h3 style="margin:0 0 6px; font-size:15px; color:#555;">📚 ${esc(c.title || ('第' + (c.chapter || '?') + '章'))}</h3>
                        <div style="color:#666; line-height:1.7; white-space:pre-wrap;">${esc(c.summary || '')}</div>
                    </div>
                `).join('') : ''}
                ${item.summary ? `
                    <hr style="border:none; border-top:1px solid #ddd; margin:16px 0;">
                    <h3 style="margin:0 0 8px; font-size:15px; color:#555;">🎬 全篇剧情</h3>
                    <div style="color:#666; line-height:1.7; white-space:pre-wrap;">${esc(item.summary)}</div>
                ` : ''}
                <div style="text-align:center; margin-top:24px;">
                    <button style="background:#3498db; color:#fff; border:none; padding:8px 24px; border-radius:8px; cursor:pointer;" onclick="this.closest('div[style*=\\'position:fixed\\']').remove()">关闭</button>
                </div>
            </div>
        `;
        document.body.appendChild(wrapper);
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

                    <!-- 底部按钮 -->
                    <div style="display:flex; gap:8px; margin-top:12px; flex-wrap:wrap;">
                        <button class="btn green" data-action="save" data-id="${inst.id}" style="flex:1; background:#0e9f6e; color:#fff; border:none; padding:8px; border-radius:8px; cursor:pointer;">💾 保存</button>
                        <button class="btn" data-action="enter" data-id="${inst.id}" style="flex:1; background:#0e7fd4; color:#fff; border:none; padding:8px; border-radius:8px; cursor:pointer;">${isEnded ? '▶ 继续剧情' : (isPaused ? '▶ 继续剧情' : '▶ 进入剧情')}</button>
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

    // ---------- 进入副本（唯一入口） ----------
    window.enterInstanceDirect = function(id) {
        if (!id) { toast('❌ 缺少副本ID'); return; }
        // 1. 先关闭编辑 modal
        const modal = document.getElementById('instanceModal');
        if (modal) modal.remove();
        currentEditingInstance = null;

        // 2. 无论什么状态，都调用 enter API（后端幂等）
        //    draft / paused / ended → active；active → 保持 active
        toast('⏳ 进入副本...');
        api('/api/instance/' + id + '/enter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: currentUser })
        }).then(d => {
            currentInstanceId = id;
            if (!instances[id]) instances[id] = {};
            instances[id].chat_history = d.chat_history || [];
            // 以服务器返回状态为准，前端不自己宣布 active
            instances[id].status = d.status || 'active';
            if (d.ai_location) {
                console.log('[instance] enter 返回状态:', d.status, 'AI 位置:', d.ai_location);
            }
            // 补充 settings 里的字段到本地实例
            const s = d.settings || {};
            if (s.name) instances[id].name = s.name;
            if (s.background) instances[id].background = s.background;
            if (s.premise) instances[id].premise = s.premise;
            if (s.time_setting) instances[id].time_setting = s.time_setting;
            if (s.participants) instances[id].participants = s.participants;
            if (s.chat_bg != null) instances[id].chat_bg = s.chat_bg;
            if (instances[id].status !== 'active') {
                toast('⚠️ 服务器返回状态为 ' + instances[id].status + '，可能未能激活');
                console.warn('[instance] enter 后状态不是 active:', instances[id].status);
            }
            // 3. 直接渲染聊天页
            renderChatRoom(d.chat_history || [], s);
        }).catch(e => {
            toast('❌ 进入失败：' + e.message);
            console.error(e);
        });
    };

    // ---------- 暂离副本（副本库编辑弹窗里的按钮） ----------
    window.pauseInstance = function(id) {
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
            // 若正在这个副本的聊天页里，一并退出
            if (currentInstanceId === id) currentInstanceId = null;
            // 刷新图鉴
            if (isReadOnly) {
                const publicList = publicInstancesMap[selectedAi] || [];
                renderPublicLibrary(publicList, selectedOwner);
            } else {
                loadInstanceLibrary(selectedAi);
            }
        }).catch(e => {
            const msg = String((e && e.message) || '');
            // 已暂离 / 已结束：状态本来就对了，不该报错卡住
            if (/不是进行中|未激活/.test(msg)) {
                toast('ℹ️ 该副本已不是进行中状态');
                if (modal) modal.remove();
                currentEditingInstance = null;
                if (isReadOnly) {
                    const publicList = publicInstancesMap[selectedAi] || [];
                    renderPublicLibrary(publicList, selectedOwner);
                } else {
                    loadInstanceLibrary(selectedAi);
                }
                return;
            }
            toast('❌ 暂离失败：' + msg);
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

    // ---------- 聊天消息渲染（复用住宅聊天 .msg/.bubble/.avatar 结构） ----------
    // 单独抽出，方便未来插入「章节 / NPC / 骰子 / 小游戏」等卡片而不动主渲染。
    function buildInstanceMsgEl(m) {
        const isMe = (m.sender === currentUser);
        const av = (window.avatars && window.avatars[m.sender]) || '';
        const avHtml = av ? '<img src="' + escAttr(av) + '">' : esc((m.sender || '?').charAt(0));
        const p = (typeof window.pairOf === 'function') ? window.pairOf(m.sender) : null;
        const isOwner = p && m.sender === p.owner;
        const bg = p ? (isOwner ? p.dark : p.light) : (isMe ? '#0e7fd4' : '#1c2f4d');
        const nameColor = p ? (isOwner ? p.dark : p.light) : '#7fd0ff';
        const textColor = p ? (isOwner ? '#ffffff' : '#16263c') : (isMe ? '#ffffff' : '#e6f1ff');
        const border = (!p && !isMe) ? 'border:1px solid rgba(255,255,255,.1);' : '';
        const d = document.createElement('div');
        d.className = 'msg ' + (isMe ? 'me' : 'other');
        d.innerHTML =
            '<div class="avatar">' + avHtml + '</div>' +
            '<div class="body">' +
                '<div class="meta">' +
                    (isMe ? '' : '<span style="color:' + nameColor + ';font-weight:bold">' + esc(m.sender) + '</span> ') +
                    '<span>' + esc(m.time || '') + '</span>' +
                '</div>' +
                '<div class="bubble" style="background:' + bg + ';color:' + textColor + ';' + border + '">' + esc(m.content) + '</div>' +
                '<div class="inst-msg-ops" style="margin-top:4px;text-align:right;"></div>' +
            '</div>';
        // 单条 AI 消息手动播放（P1 预留）
        const ops = d.querySelector('.inst-msg-ops');
        if (ops && isAssistantMsg(m)) {
            const b = document.createElement('span');
            b.textContent = '🔊 朗读';
            b.style.cssText = 'font-size:11px;color:#7fa8cf;cursor:pointer;';
            b.onclick = function() { window.playMessageVoice(m); };
            ops.appendChild(b);
        }
        return d;
    }

    // 前情提要 → 聊天框第一条「剧情系统消息」（仅 UI 层，绝不写入 chat_history）
    function buildPremiseEl(premise) {
        const d = document.createElement('div');
        d.className = 'inst-story';
        d.innerHTML =
            '<div class="body">' +
                '<div class="cap">📖 副本开始</div>' +
                '<div class="txt">' + esc(premise) + '</div>' +
            '</div>';
        return d;
    }

    function buildThinkingEl() {
        const d = document.createElement('div');
        d.id = 'instanceAiThinking';
        d.className = 'inst-thinking';
        d.innerHTML = '<span class="dot"></span><span>💭 AI 正在思考…</span>';
        return d;
    }

    function instScrollToBottom() {
        const area = document.getElementById('instanceMsgArea');
        if (area) area.scrollTop = area.scrollHeight;
    }

    function renderChatMessages() {
        const area = document.getElementById('instanceMsgArea');
        if (!area) return;
        const inst = instances[currentInstanceId];
        if (!inst) return;
        const hist = inst.chat_history || [];
        const stick = area.scrollTop + area.clientHeight >= area.scrollHeight - 60;
        area.innerHTML = '';

        // 1) 前情提要做第一条剧情内容（不固定占顶部）
        if (inst.premise) area.appendChild(buildPremiseEl(inst.premise));

        // 2) 真实聊天记录
        if (!hist.length) {
            if (!inst.premise) {
                const tip = document.createElement('div');
                tip.className = 'sys-tip';
                tip.textContent = '✨ 空荡荡的，开始你的冒险吧…';
                area.appendChild(tip);
            }
        } else {
            hist.forEach(m => {
                if (m.sender === 'system') area.appendChild(buildSystemEl(m.content));
                else area.appendChild(buildInstanceMsgEl(m));
            });
        }

        // 3) 思考中指示器（用状态变量判断，不能依赖 DOM，因为上面刚清空过）
        if (thinkingActive) area.appendChild(buildThinkingEl());
        if (stick) instScrollToBottom();
    }

    function buildSystemEl(t) {
        const d = document.createElement('div');
        d.className = 'msg system';
        d.innerHTML = '<div class="bubble">' + esc(t) + '</div>';
        return d;
    }

    function showAiThinking(on) {
        const area = document.getElementById('instanceMsgArea');
        thinkingActive = !!on;
        if (!area) return;
        const cur = document.getElementById('instanceAiThinking');
        if (on) {
            if (cur) return;
            area.appendChild(buildThinkingEl());
            instScrollToBottom();
        } else if (cur) {
            cur.remove();
        }
    }

    // 失败时把原因显示在聊天区，不再静默超时
    function showInstanceError(msg) {
        const area = document.getElementById('instanceMsgArea');
        if (!area) { toast(msg); return; }
        const old = document.getElementById('instanceErrorBar');
        if (old) old.remove();
        const d = document.createElement('div');
        d.id = 'instanceErrorBar';
        d.className = 'inst-err';
        d.textContent = '⚠️ ' + msg;
        area.appendChild(d);
        instScrollToBottom();
    }

    // ---------- 背景 / 剧情 阅读面板（不再长期占据聊天空间） ----------
    function openInstanceInfoModal(title, sections) {
        const mask = document.createElement('div');
        mask.className = 'inst-modal-mask';
        mask.onclick = function(e) { if (e.target === mask) mask.remove(); };
        const body = (sections || []).map(s => (
            '<h3>' + esc(s.title) + '</h3>' +
            (s.text ? '<div class="txt">' + esc(s.text) + '</div>' : '<div class="muted">（未填写）</div>')
        )).join('');
        mask.innerHTML =
            '<div class="inst-modal">' +
                '<h2>' + esc(title) + '</h2>' +
                body +
                '<div class="mfoot"><button class="mclose">关闭</button></div>' +
            '</div>';
        mask.querySelector('.mclose').onclick = function() { mask.remove(); };
        document.body.appendChild(mask);
    }

    window.openInstanceBackground = function() {
        const inst = instances[currentInstanceId];
        if (!inst) return;
        const parts = (inst.participants || []).map(p =>
            (p.type === 'user' ? '👤 ' : (p.type === 'ai' ? '🤖 ' : '🧑 ')) +
            p.name + (p.type === 'npc' ? '（NPC）' : '') +
            (p.profile ? '：' + p.profile : '')
        ).join('\n');
        const sections = [
            { title: '🌍 副本背景', text: inst.background },
            { title: '🕰️ 剧情时间', text: inst.time_setting },
            { title: '📖 前情提要', text: inst.premise },
            { title: '👥 参与者', text: parts }
        ];
        // 已完成的章节也放进这个面板（不再占用聊天空间）
        const chapters = inst.chapters || [];
        chapters.forEach(c => {
            sections.push({
                title: '📚 ' + (c.title || ('第' + (c.chapter || '?') + '章')) +
                       '（第' + (c.round_start || '?') + '-' + (c.round_end || '?') + '轮）',
                text: c.summary || ''
            });
        });
        openInstanceInfoModal('📖 ' + (inst.name || '副本'), sections);
    };

    // 保留：供未来单独的「📚 剧情」入口调用（本次按需求收进「📖 副本背景」面板）
    window.openInstanceChapters = function() {
        const inst = instances[currentInstanceId];
        if (!inst) return;
        const chapters = inst.chapters || [];
        if (!chapters.length) {
            toast('📚 还没有已完成的章节（每 30 轮生成一章）');
            return;
        }
        openInstanceInfoModal('📚 ' + (inst.name || '副本') + ' · 剧情章节',
            chapters.map(c => ({
                title: (c.title || ('第' + (c.chapter || '?') + '章')) + '（第' + (c.round_start || '?') + '-' + (c.round_end || '?') + '轮）',
                text: c.summary || ''
            }))
        );
    };

    // ---------- 聊天界面（InstanceChatShell：Header / StoryHeader / MessageList / Composer） ----------
    function renderChatRoom(history, settings) {
        injectInstanceChatStyles();
        setContentChatMode();
        thinkingActive = false;   // 进入/重绘聊天页时重置思考态
        let inst = instances[currentInstanceId];
        if (!inst) {
            if (settings && settings.name) {
                inst = {
                    id: currentInstanceId,
                    name: settings.name || '未命名',
                    time_setting: settings.time_setting || '',
                    background: settings.background || '',
                    premise: settings.premise || '',
                    participants: settings.participants || [],
                    chapters: settings.chapters || [],
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
        // settings 里可能带来更完整的副本信息（enter 接口返回）
        if (settings) {
            if (settings.name) inst.name = settings.name;
            if (settings.background != null) inst.background = settings.background;
            if (settings.premise != null) inst.premise = settings.premise;
            if (settings.time_setting != null) inst.time_setting = settings.time_setting;
            if (settings.participants) inst.participants = settings.participants;
            if (settings.chapters) inst.chapters = settings.chapters;
        }

        const content = document.getElementById('instanceContent');
        content.innerHTML = `
            <div class="inst-shell">
                <div class="inst-top">
                    <span class="inst-back" onclick="pauseAndLeaveInstance()" title="← 返回副本首页（= 暂离副本，AI 回到现实世界）">← 返回首页</span>
                    <span class="inst-title">🎬 ${esc(inst.name || '未命名')}</span>
                    ${inst.time_setting ? `<span class="inst-sub">${esc(inst.time_setting)}</span>` : ''}
                </div>
                <div class="inst-bar">
                    <button class="inst-hbtn" onclick="changeInstanceChatBg()" title="上传一张图片作为聊天背景（保存在服务器）">🖼 换背景图</button>
                    <button class="inst-hbtn" onclick="openInstanceBackground()" title="查看副本背景 / 前情提要 / 参与者">📖 副本背景</button>
                    <button class="inst-hbtn" onclick="pauseAndLeaveInstance()" title="返回副本首页（= 暂离副本）">🏠 返回首页</button>
                    <button class="inst-hbtn danger" onclick="endInstance('${escAttr(currentInstanceId)}')" title="结束副本并生成剧情总结">🏁 结束副本</button>
                    <button class="inst-hbtn" id="instanceVoiceBtn" onclick="toggleAutoVoice()" title="自动朗读">🔇 语音</button>
                </div>
                <div id="instanceChatArea" class="inst-chatarea">
                    <div id="instanceMsgArea"></div>
                </div>
                <div class="inst-composer">
                    <div class="row">
                        <button id="instanceModelChip" class="inst-model-chip" onclick="openInstanceModelPicker()" title="切换模型">…</button>
                        <input id="instanceMsgInput" placeholder="说点什么…" autocomplete="off"
                               onkeydown="if(event.key==='Enter') sendInstanceMsg()">
                        <button id="instanceSendBtn" onclick="sendInstanceMsg()">发送</button>
                    </div>
                </div>
            </div>
        `;
        renderChatMessages();
        renderModelTools();
        updateVoiceToggleUI();
        // 恢复本副本已保存的聊天背景（无则保持默认色）
        applyChatBg(inst.chat_bg || '');
        loadChatBg(currentInstanceId);
    }

    // ---------- 聊天相关辅助函数 ----------
    // 语义（按产品定义）：
    //   返回首页 = 暂离副本（AI 回现实世界住宅），副本保留 chat_history
    //   结束副本 = 生成总结并真正结束
    //   关闭整个副本模块 = 回到现实世界
    function goBackToLibrary() {
        currentInstanceId = null;
        if (isReadOnly) {
            const publicList = publicInstancesMap[selectedAi] || [];
            renderPublicLibrary(publicList, selectedOwner);
        } else if (selectedAi) {
            loadInstanceLibrary(selectedAi);
        } else {
            renderAiSelection();
        }
    }

    // 暂离：返回后端确认过的 payload（含 status / ai / ai_location / hall），失败返回 null
    function doPauseInstance(iid, owner) {
        const u = owner || currentUser;
        if (!iid || !u) return Promise.resolve(null);
        return api('/api/instance/' + iid + '/pause', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: u })
        }).catch(e => {
            console.warn('[instance] pause 失败:', e.message);
            return null;
        });
    }

    // 顶栏「← 返回首页」/「🏠 返回首页」
    // 不盲返回：先确认后端真的把副本暂停、AI 回到现实世界，再回副本库。
    window.pauseAndLeaveInstance = function() {
        const iid = currentInstanceId;
        if (!iid) { goBackToLibrary(); return; }
        toast('⏸ 正在暂离副本…');
        doPauseInstance(iid).then(res => {
            if (!res || !res.ok) {
                toast('⚠️ 暂离状态未确认，正在刷新副本状态…');
            } else {
                const loc = res.ai_location || res.hall || '住宅';
                toast('✅ 已暂离副本，' + (res.ai ? res.ai + ' 回到 ' + loc : 'AI 回到现实世界'));
                console.log('[instance] pause 确认:', {
                    iid: iid, status: res.status, ai: res.ai,
                    ai_location: res.ai_location, hall: res.hall
                });
            }
            // 后端已确认（或未确认）都回库；goBackToLibrary 会重新 /api/instances 拉最新状态
            goBackToLibrary();
        });
    };

    window.backToLibraryFromChat = function() { window.pauseAndLeaveInstance(); };

    // 更换聊天背景图：直接上传图片 → 存服务器文件，data.json 里只存路径
    function applyChatBg(url) {
        const area = document.getElementById('instanceChatArea');
        if (!area) return;
        if (url) {
            area.style.backgroundImage = 'url(' + url + ')';
            area.style.backgroundSize = 'cover';
            area.style.backgroundPosition = 'center';
        } else {
            area.style.backgroundImage = 'none';
        }
    }

    // 进入聊天页时恢复本副本已保存的背景
    function loadChatBg(iid) {
        if (!iid) return;
        api('/api/instance/' + iid + '/chat_bg?user=' + encodeURIComponent(currentUser))
            .then(d => {
                const bg = (d && d.bg) || '';
                const inst = instances[iid];
                if (inst) inst.chat_bg = bg;
                applyChatBg(bg);
            })
            .catch(() => {});
    }

    window.changeInstanceChatBg = function() {
        const inst = instances[currentInstanceId];
        if (!inst) return;
        // 已有自定义背景时，先把「恢复默认」这个出口给出来，
        // 免得用户找不到路回去（不额外占用功能键位置）
        if (inst.chat_bg) {
            if (confirm('当前已设置自定义背景。\n【确定】= 换一张新图\n【取消】= 恢复默认背景')) { /* 继续走选图 */ }
            else { window.clearInstanceChatBg(); return; }
        }
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = function(e) {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(ev) {
                const dataUrl = ev.target.result;
                toast('⏳ 正在上传背景…');
                api('/api/instance/' + currentInstanceId + '/chat_bg', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user: currentUser, bg: dataUrl })
                }).then(d => {
                    // 后端返回的是文件路径，不是 base64
                    inst.chat_bg = (d && d.bg) || '';
                    applyChatBg(inst.chat_bg);
                    toast('✅ 背景已保存到服务器');
                }).catch(err => toast('❌ 上传失败：' + err.message));
            };
            reader.readAsDataURL(file);
        };
        input.click();
    };

    window.clearInstanceChatBg = function() {
        const inst = instances[currentInstanceId];
        if (!inst) return;
        api('/api/instance/' + currentInstanceId + '/chat_bg', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: currentUser, bg: '' })
        }).then(() => {
            inst.chat_bg = '';
            applyChatBg('');
            toast('已恢复默认背景');
        }).catch(err => toast('❌ ' + err.message));
    };

    // 重新激活副本（幂等）：用于「副本未激活」时自动纠正前端/后端状态不一致
    function reenterInstance(iid) {
        return api('/api/instance/' + iid + '/enter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: currentUser })
        }).then(d => {
            // 只更新状态与历史，不重绘（重绘会清空输入态）
            if (!instances[iid]) instances[iid] = {};
            if (d && d.chat_history) instances[iid].chat_history = d.chat_history;
            // 以服务器返回状态为准，前端不自己宣布 active
            instances[iid].status = (d && d.status) || 'active';
            const s = (d && d.settings) || {};
            if (s.name) instances[iid].name = s.name;
            if (s.background != null) instances[iid].background = s.background;
            if (s.premise != null) instances[iid].premise = s.premise;
            if (s.time_setting != null) instances[iid].time_setting = s.time_setting;
            if (s.participants) instances[iid].participants = s.participants;
            if (s.chat_bg != null) instances[iid].chat_bg = s.chat_bg;
            console.log('[instance] reenter success:', iid,
                'status=', instances[iid].status,
                'ai_location=', (d && d.ai_location) || null);
            return instances[iid].status === 'active';
        }).catch(e => {
            console.warn('[instance] 重新进入失败:', e.message);
            return false;
        });
    }

    window.sendInstanceMsg = function() {
        const input = document.getElementById('instanceMsgInput');
        const btn = document.getElementById('instanceSendBtn');
        if (!input || !currentInstanceId) return;
        const content = input.value.trim();
        if (!content) return;
        input.value = '';
        if (btn) btn.disabled = true;

        const iid = currentInstanceId;
        const inst = instances[iid];
        const prevHist = inst ? (inst.chat_history || []).slice() : [];
        const errBar = document.getElementById('instanceErrorBar');
        if (errBar) errBar.remove();

        // 1. 乐观显示用户消息（失败时回滚）
        if (inst) {
            inst.chat_history = prevHist.concat([{
                sender: currentUser, content: content, time: new Date().toLocaleString(), role: 'user'
            }]);
            renderChatMessages();
        }
        showAiThinking(true);

        // 2. 发送请求（带上模型覆盖；后端未支持时该字段被忽略）
        const body = { user: currentUser, content: content };
        if (currentInstanceModel) body.model_override = currentInstanceModel;

        const doPost = () => api('/api/instance/' + iid + '/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        // 3. 成功后才开始轮询 AI 回复。
        //    baseline：本轮发送前的 assistant 条数（进聊天页时取一次；若中间重新激活过，
        //    服务端历史可能变化，必须用刷新后的最新值，否则会误判 AI 是否已回复）。
        const afterPost = (baseline) => {
            const before = (typeof baseline === 'number')
                ? baseline
                : countAssistantMsgs(instances[iid] ? instances[iid].chat_history : []);
            let tries = 0;
            const MAX_TRIES = 15;   // 约 22 秒
            const finish = () => { showAiThinking(false); if (btn) btn.disabled = false; };

            const tick = () => {
                tries++;
                refreshInstanceChat(before).then(done => {
                    if (done) { finish(); maybeAutoSpeak((instances[iid] || {}).chat_history); return; }
                    if (tries >= MAX_TRIES) {
                        finish();
                        showInstanceError('AI 没有回复。你的消息已保存。请检查「设置 → AI 集成总开关」是否开启、以及「模型与服务」里的 API Key / 模型是否可用。');
                        const area = document.getElementById('instanceMsgArea');
                        if (area) {
                            const wrap = document.createElement('div');
                            wrap.style.cssText = 'text-align:center;margin-bottom:10px;';
                            const b = document.createElement('button');
                            b.className = 'inst-hbtn';
                            b.textContent = '🔄 刷新（只看 AI 是否稍后回复）';
                            // 只重新拉取，绝不重发消息：重发会在 chat_history 里重复用户消息，
                            // 污染 round_count 与每 30 轮的章节切片。
                            b.onclick = function() {
                                b.disabled = true;
                                b.textContent = '🔄 检查中…';
                                refreshInstanceChat(before).then(done2 => {
                                    if (done2) { maybeAutoSpeak((instances[iid] || {}).chat_history); return; }
                                    // 未回复 → 重新渲染会清空本按钮，再给一条明确提示
                                    showInstanceError('AI 仍未回复。多半是「AI 集成总开关」未开启，或 API Key / 模型不可用。');
                                });
                            };
                            wrap.appendChild(b);
                            area.appendChild(wrap);
                            instScrollToBottom();
                        }
                        return;
                    }
                    setTimeout(tick, Math.min(2000, 600 + tries * 200));
                });
            };
            setTimeout(tick, 700);
        };

        doPost().then(() => afterPost(countAssistantMsgs(prevHist))).catch(e => {
            const msg = String((e && e.message) || '');
            // 「副本未激活」：本地以为是 active，后端已 paused/ended。
            // 自动重新进入一次再重发，用户无感；只重试一次，绝不第三次。
            if (/未激活/.test(msg)) {
                console.warn('[instance] 副本未激活，自动重新进入后重发…');
                reenterInstance(iid).then(ok => {
                    const fresh = instances[iid] || {};
                    if (!ok || fresh.status !== 'active') {
                        // 服务器状态没回到 active：不再继续 enter/message 循环
                        showAiThinking(false);
                        if (btn) btn.disabled = false;
                        console.error('[instance] 重新激活未成功', {
                            iid: iid,
                            reenterOk: ok,
                            localStatus: fresh.status
                        });
                        showInstanceError('副本重新激活失败：服务器状态仍不是 active。请返回副本首页后重新进入。');
                        return;
                    }
                    // 重新进入会带回最新 chat_history，baseline 必须基于新历史重算
                    const freshBaseline = countAssistantMsgs(fresh.chat_history || []);
                    doPost().then(() => afterPost(freshBaseline)).catch(e2 => {
                        showAiThinking(false);
                        if (btn) btn.disabled = false;
                        // P0-K：第二次仍失败 → 说明不是普通前端状态问题，把真实状态打出来，
                        // 不再自动重试第三次。
                        console.error('[instance] reactivated message still failed', {
                            iid: iid,
                            localStatus: instances[iid] && instances[iid].status,
                            error: e2.message
                        });
                        showInstanceError('重新激活后仍发送失败。请返回副本首页后重新进入。');
                    });
                });
                return;
            }
            showAiThinking(false);
            if (btn) btn.disabled = false;
            // POST 失败 → 回滚乐观消息，不留假消息
            if (inst) { inst.chat_history = prevHist; renderChatMessages(); }
            showInstanceError('发送失败：' + msg + '（消息未保存，请重试）');
            console.error(e);
        });
    };

    // 拉取最新副本数据并重绘；返回「是否已经出现新的 AI 回复」
    function refreshInstanceChat(beforeAssistantCount) {
        if (!currentInstanceId) return Promise.resolve(false);
        const iid = currentInstanceId;
        return api('/api/instances?user=' + encodeURIComponent(currentUser))
            .then(d => {
                const inst = (d.instances || {})[iid];
                if (!inst) return false;
                const oldCount = (typeof beforeAssistantCount === 'number')
                    ? beforeAssistantCount
                    : countAssistantMsgs((instances[iid] || {}).chat_history);
                instances[iid] = inst;
                renderChatMessages();
                // 只要最后一条不是用户自己发的，就认为 AI 已回
                const hist = inst.chat_history || [];
                const last = hist[hist.length - 1];
                const replied = countAssistantMsgs(hist) > oldCount
                    || (!!last && last.sender !== currentUser && last.role !== 'user');
                return replied;
            }).catch(() => false);
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
        injectInstanceChatStyles();   // 让 .inst-* 样式一开始就可用
        modifyMapBar();
        createOverlay();
        console.log('[ext] 副本插件 v13 加载完成（暂离事务确认 / 状态以服务器为准 / 暂停角标 / 聊天背景存文件）');
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();