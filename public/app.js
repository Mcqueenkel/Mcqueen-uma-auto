(() => {
const state = {
    needs2fa: false,
    isLoading: false,
    account: null,
    isDeletingCareer: false,
    isFetchingFriends: false,
    isStartingCareer: false,
    presets: [],
    selectedPreset: "",
    runnerTimer: 0,
    isSavingPreset: false,
    raceData: [],
    selectedRaces: [],
    racesDirty: false,
    scenarioType: "Mant",
    burnClocks: false,
    displayedClocksUsed: 0,
    devEnabled: false,
    runCount: 1,
    consecutiveRunnerFails: 0
};
const els = {
    loadingScreen: document.getElementById('loading-screen'),
    navbar: document.querySelector('.navbar'),
    themeToggle: document.getElementById('theme-toggle'),
    brandMark: document.querySelector('.title span'),
    loginBtn: document.getElementById('login-btn'),
    recaptureBtn: document.getElementById('recapture-btn'),
    recaptureStatus: document.getElementById('recapture-status'),
    logoutBtn: document.getElementById('logout-btn'),
    refreshBtn: document.getElementById('refresh-btn'),
    turnDelayMin: document.getElementById('turn-delay-min'),
    turnDelayMax: document.getElementById('turn-delay-max'),
    temptFateBtn: document.getElementById('tempt-fate-btn'),
    burnClocksBtn: document.getElementById('burn-clocks-btn'),
    devBtn: document.getElementById('dev-career-btn'),
    runCountInput: document.getElementById('run-count-input'),
    runCountHint: document.getElementById('run-count-hint'),
    loginView: document.getElementById('login-view'),
    dashboardView: document.getElementById('dashboard-view'),
    errorMsg: document.getElementById('error-msg'),
    standardFields: document.getElementById('standard-fields'),
    faFields: document.getElementById('2fa-fields'),
    umaGrid: document.getElementById('uma-grid'),
    cardGrid: document.getElementById('card-grid'),
    cardGridWrapper: document.getElementById('card-grid-wrapper'),
    cardsToggle: document.getElementById('cards-toggle'),
    cardsChevron: document.getElementById('cards-chevron'),
    parentGrid: document.getElementById('parent-grid'),
    friendGrid: document.getElementById('friend-grid'),
    deckList: document.getElementById('deck-list'),
    umaCount: document.getElementById('uma-count'),
    cardCount: document.getElementById('card-count'),
    parentCount: document.getElementById('parent-count'),
    friendCount: document.getElementById('friend-count'),
    friendStatus: document.getElementById('friend-status'),
    friendRefreshBtn: document.getElementById('friend-refresh-btn'),
    presetSelect: document.getElementById('preset-select'),
    startCareerBtn: document.getElementById('start-career-btn'),
    navRunBtn: document.getElementById('nav-run-btn'),
    navPauseBtn: document.getElementById('nav-pause-btn'),
    startStatus: document.getElementById('start-status'),
    accountStrip: document.getElementById('account-strip'),
    careerModal: document.getElementById('career-modal'),
    careerModalCopy: document.getElementById('career-modal-copy'),
    careerCancelBtn: document.getElementById('career-cancel-btn'),
    careerDeleteBtn: document.getElementById('career-delete-btn'),
    runConfirmModal: document.getElementById('run-confirm-modal'),
    runConfirmCopy: document.getElementById('run-confirm-copy'),
    runConfirmOk: document.getElementById('run-confirm-ok'),
    runConfirmCancel: document.getElementById('run-confirm-cancel'),
    raceToggle: document.getElementById('race-toggle'),
    raceChevron: document.getElementById('race-chevron'),
    raceBody: document.getElementById('race-body'),
    saveRacesBtn: document.getElementById('save-races-btn'),
    raceSaveStatus: document.getElementById('race-save-status'),
    raceOptionsContent: document.getElementById('race-options-content'),
    racePopupOverlay: document.getElementById('race-slot-popup-overlay'),
    racePopupTitle: document.getElementById('race-slot-popup-title'),
    racePopupBody: document.getElementById('race-slot-popup-body'),
    racePopupClose: document.getElementById('race-slot-popup-close'),
    masterDataPath: document.getElementById('master-data-path'),
    masterDataSaveBtn: document.getElementById('master-data-save-btn'),
    masterDataStatus: document.getElementById('master-data-status'),
    discordWebhookUrl: document.getElementById('discord-webhook-url'),
    discordWebhookSaveBtn: document.getElementById('discord-webhook-save-btn'),
    discordWebhookTestBtn: document.getElementById('discord-webhook-test-btn'),
    discordWebhookStatus: document.getElementById('discord-webhook-status'),
    discordNotifyForecast: document.getElementById('discord-notify-forecast'),
    presetSection: document.getElementById('preset-section'),
    presetAddBtn: document.getElementById('preset-add-btn'),
    presetDelBtn: document.getElementById('preset-del-btn'),
    presetRunningStyle: document.getElementById('preset-running-style'),
    presetSkillThreshold: document.getElementById('preset-skill-threshold'),
    presetEditSkillsBtn: document.getElementById('preset-edit-skills-btn'),
    skillModal: document.getElementById('skill-modal'),
    skillSearch: document.getElementById('skill-search'),
    skillList: document.getElementById('skill-list'),
    skillTiersContainer: document.getElementById('skill-tiers-container'),
    skillBlacklistContainer: document.getElementById('skill-blacklist-container'),
    skillAddTierBtn: document.getElementById('skill-add-tier-btn'),
    skillModalClose: document.getElementById('skill-modal-close')
};
        const delaySettingsStorageKey = 'uma_turn_delay_settings';
        const burnClocksStorageKey = 'uma_burn_clocks';
        const devStorageKey = 'uma_dev_career';
        function syncDevControls() {
            if (!els.devBtn) return;
            els.devBtn.classList.toggle('is-active', state.devEnabled);
            els.devBtn.innerText = `DEV: ${state.devEnabled ? 'ON' : 'OFF'}`;
        }
        function setDevEnabled(value, options = {}) {
            state.devEnabled = Boolean(value);
            syncDevControls();
            if (options.persist) {
                localStorage.setItem(devStorageKey, String(state.devEnabled));
            }
        }

        window.addEventListener('storage', event => {
            if (event.key === devStorageKey && event.newValue !== null) {
                setDevEnabled(event.newValue === 'true', { persist: false });
            }
        });
        const storedDev = localStorage.getItem(devStorageKey);
        if (storedDev !== null) setDevEnabled(storedDev === 'true', { persist: false });

        const runCountStorageKey = 'uma_run_count';
        function readRunCount() {
            const v = parseInt(els.runCountInput && els.runCountInput.value, 10);
            return (Number.isInteger(v) && v >= 0) ? v : 1;
        }
        function updateRunCountHint() {
            if (!els.runCountHint) return;
            const n = state.runCount;
            els.runCountHint.textContent = n === 0 ? '∞ infinite' : (n === 1 ? '1 career (once)' : `${n} careers`);
            els.runCountHint.classList.toggle('infinite', n === 0);
        }
        const storedRunCount = localStorage.getItem(runCountStorageKey);
        if (storedRunCount !== null && els.runCountInput) els.runCountInput.value = storedRunCount;
        state.runCount = readRunCount();
        updateRunCountHint();
        if (els.runCountInput) {
            els.runCountInput.addEventListener('input', () => {
                state.runCount = readRunCount();
                localStorage.setItem(runCountStorageKey, String(state.runCount));
                updateRunCountHint();
            });
        }

        function setLoadingScreen(visible) {
            if (!els.loadingScreen) return;
            els.loadingScreen.classList.toggle('hidden', !visible);
        }
        function hideNavbar() {
            document.body.classList.add('pre-login');
            if (els.brandMark) els.brandMark.classList.remove('is-entrance');
        }
        function showNavbar() {
            document.body.classList.remove('pre-login');
        }
        function playBrandIntro() {
            if (!els.brandMark) return;
            els.brandMark.classList.remove('is-entrance');
            void els.brandMark.offsetWidth;
            els.brandMark.classList.add('is-entrance');
            window.setTimeout(() => els.brandMark.classList.remove('is-entrance'), 950);
        }
        hideNavbar();
        function syncDashboardHeight() {
            const navbar = document.querySelector('.navbar');
            const navbarHeight = navbar ? navbar.getBoundingClientRect().height : 0;
            const availableHeight = Math.max(360, Math.floor(window.innerHeight - navbarHeight));
            document.documentElement.style.setProperty('--dashboard-height', `${availableHeight}px`);
            syncDashboardCollapseState(false);
        }
        window.addEventListener('resize', syncDashboardHeight);
        window.addEventListener('orientationchange', syncDashboardHeight);
        syncDashboardHeight();
        const panelToggleSyncers = [];
        const dashboardMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
        let dashboardLayoutAnimation = 0;
        const dashboardAnimationMs = 420;
        function isCompactDashboard() {
            return window.matchMedia('(max-width: 850px)').matches;
        }
        function getPanelLayoutTarget(setupCollapsed, contentCollapsed) {
            const compact = isCompactDashboard();
            const gutter = document.querySelector('.split-gutter-controls');
            const dashboardRect = els.dashboardView.getBoundingClientRect();
            const gutterRect = gutter.getBoundingClientRect();
            const gutterSize = compact ? gutterRect.height : gutterRect.width;
            const available = Math.max(0, (compact ? dashboardRect.height : dashboardRect.width) - gutterSize);
            if (compact) {
                const setupSize = setupCollapsed ? 0 : contentCollapsed ? available : available * 0.34;
                const contentSize = contentCollapsed ? 0 : setupCollapsed ? available : Math.max(340, available - setupSize);
                return { compact, gutterSize, setupSize, contentSize };
            }
            const setupSize = setupCollapsed ? 0 : contentCollapsed ? available : Math.min(available * 0.62, available - 340);
            const contentSize = contentCollapsed ? 0 : setupCollapsed ? available : Math.max(340, available - setupSize);
            return { compact, gutterSize, setupSize, contentSize };
        }
        function setDashboardTemplate(layout, setupSize, contentSize) {
            const safeSetup = Math.max(0, setupSize);
            const safeContent = Math.max(0, contentSize);
            if (layout.compact) {
                els.dashboardView.style.gridTemplateColumns = '';
                els.dashboardView.style.gridTemplateRows = `${safeSetup}px ${layout.gutterSize}px ${safeContent}px`;
            } else {
                els.dashboardView.style.gridTemplateRows = '';
                els.dashboardView.style.gridTemplateColumns = `${safeSetup}px ${layout.gutterSize}px ${safeContent}px`;
            }
        }
        function easeDashboardLayout(t) {
            return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        }
        function syncDashboardCollapseState(animate = false) {
            const setupPanel = document.getElementById('setup-panel');
            const contentPanel = document.getElementById('content-panel');
            if (!setupPanel || !contentPanel || !els.dashboardView) return;
            if (setupPanel.classList.contains('collapsed') && contentPanel.classList.contains('collapsed')) {
                contentPanel.classList.remove('collapsed');
            }
            const setupCollapsed = setupPanel.classList.contains('collapsed');
            const contentCollapsed = contentPanel.classList.contains('collapsed');
            els.dashboardView.classList.toggle('setup-collapsed', setupCollapsed);
            els.dashboardView.classList.toggle('content-collapsed', contentCollapsed);
            if (!els.dashboardView.classList.contains('active')) return;
            const layout = getPanelLayoutTarget(setupCollapsed, contentCollapsed);
            if (dashboardLayoutAnimation) {
                cancelAnimationFrame(dashboardLayoutAnimation);
                dashboardLayoutAnimation = 0;
            }
            els.dashboardView.style.transition = 'none';
            if (!animate || dashboardMotion.matches) {
                setDashboardTemplate(layout, layout.setupSize, layout.contentSize);
                return;
            }
            const compact = layout.compact;
            const setupRect = setupPanel.getBoundingClientRect();
            const contentRect = contentPanel.getBoundingClientRect();
            const startSetup = compact ? setupRect.height : setupRect.width;
            const startContent = compact ? contentRect.height : contentRect.width;
            const targetSetup = layout.setupSize;
            const targetContent = layout.contentSize;
            if (Math.abs(startSetup - targetSetup) < 0.5 && Math.abs(startContent - targetContent) < 0.5) {
                setDashboardTemplate(layout, targetSetup, targetContent);
                return;
            }
            const startedAt = performance.now();
            const step = now => {
                const t = Math.min(1, (now - startedAt) / dashboardAnimationMs);
                const eased = easeDashboardLayout(t);
                setDashboardTemplate(
                    layout,
                    startSetup + (targetSetup - startSetup) * eased,
                    startContent + (targetContent - startContent) * eased
                );
                if (t < 1) {
                    dashboardLayoutAnimation = requestAnimationFrame(step);
                } else {
                    setDashboardTemplate(layout, targetSetup, targetContent);
                    dashboardLayoutAnimation = 0;
                }
            };
            setDashboardTemplate(layout, startSetup, startContent);
            dashboardLayoutAnimation = requestAnimationFrame(step);
        }
        function syncPanelToggleButtons() {
            panelToggleSyncers.forEach(sync => sync());
        }
        function makePanelToggle(panelId, btnId, collapseIcon, expandIcon) {
            const panel = document.getElementById(panelId);
            const btn = document.getElementById(btnId);
            const label = (btn.dataset.panelLabel || 'panel').toLowerCase();
            const renderChevrons = icon => `
                <span class="panel-collapse-btn-chevron-stack" aria-hidden="true">
                    <span>${icon}</span>
                    <span>${icon}</span>
                    <span>${icon}</span>
                </span>
            `;
            const syncButton = () => {
                const isCollapsed = panel.classList.contains('collapsed');
                const icon = isCollapsed ? expandIcon : collapseIcon;
                btn.classList.toggle('is-collapsed', isCollapsed);
                btn.innerHTML = renderChevrons(icon);
                btn.setAttribute('title', `${isCollapsed ? 'Expand' : 'Collapse'} ${label}`);
                btn.setAttribute('aria-label', `${isCollapsed ? 'Expand' : 'Collapse'} ${label}`);
                btn.setAttribute('aria-expanded', String(!isCollapsed));
            };
            panelToggleSyncers.push(syncButton);
            btn.addEventListener('click', () => {
                panel.classList.toggle('collapsed');
                syncDashboardCollapseState(true);
                syncPanelToggleButtons();
            });
            syncDashboardCollapseState(false);
            syncButton();
        }
        makePanelToggle('setup-panel',   'setup-collapse-btn',   '&lt;', '&gt;');
        makePanelToggle('content-panel', 'content-collapse-btn', '&gt;', '&lt;');
        function makeSectionToggle(toggleId, chevronId, bodyId, startExpanded) {
            const toggle  = document.getElementById(toggleId);
            const chevron = document.getElementById(chevronId);
            const body    = document.getElementById(bodyId);
            if (!toggle || !body) return;
            const setInitial = () => {
                const expanded = body.classList.contains('expanded');
                body.style.height = expanded ? 'auto' : '0px';
                chevron.classList.toggle('expanded', expanded);
            };
            const expand = () => {
                body.classList.add('expanded');
                chevron.classList.add('expanded');
                body.style.height = '0px';
                body.offsetHeight;
                body.style.height = `${body.scrollHeight}px`;
            };
            const collapse = () => {
                body.style.height = `${body.scrollHeight}px`;
                body.offsetHeight;
                body.classList.remove('expanded');
                chevron.classList.remove('expanded');
                body.style.height = '0px';
            };
            body.addEventListener('transitionend', event => {
                if (event.propertyName === 'height' && body.classList.contains('expanded')) body.style.height = 'auto';
            });
            toggle.addEventListener('click', () => {
                if (body.classList.contains('expanded')) collapse();
                else expand();
            });
            setInitial();
        }
        makeSectionToggle('decks-toggle',    'decks-chevron',    'decks-body',    true);
        makeSectionToggle('friends-toggle',  'friends-chevron',  'friends-body',  true);
        makeSectionToggle('trainees-toggle', 'trainees-chevron', 'trainees-body', true);
        makeSectionToggle('parents-toggle',  'parents-chevron',  'parents-body',  true);
        makeSectionToggle('cards-toggle',    'cards-chevron',    'card-grid-wrapper', false);
        makeSectionToggle('events-toggle',   'events-chevron',   'events-body',       false);

        async function loadEvents() {
            const list = document.getElementById('events-list');
            const countEl = document.getElementById('events-count');
            if (!list) return;
            // Active deck's support cards -> pre-populate their events from master.mdb.
            let deckCards = [];
            try { if (selection && selection.deck && selection.deck.cards) deckCards = selection.deck.cards; } catch (e) {}
            const cardNames = {};
            deckCards.forEach(c => { if (c && c.id != null) cardNames[String(c.id)] = c.name || ('Support ' + c.id); });
            const ids = deckCards.map(c => c && c.id).filter(v => v != null);
            const q = ids.length ? ('?cards=' + encodeURIComponent(ids.join(','))) : '';
            try {
                const data = await apiJson('/api/events' + q);
                const events = (data && data.events) || [];
                if (countEl) countEl.textContent = events.length ? `(${events.length})` : '';
                if (!events.length) {
                    list.innerHTML = '<div class="events-empty">No events yet. Select your deck, then hit REFRESH — its support-card events show up here.</div>';
                    return;
                }
                let html = '';
                let lastCard;
                events.forEach(ev => {
                    const cardId = ev.support_card_id || 0;
                    if (cardId !== lastCard) {
                        lastCard = cardId;
                        const label = cardId ? (cardNames[String(cardId)] || ('Support ' + cardId)) : 'Other / scenario events';
                        html += `<div class="event-group-head">${escapeHtml(label)}</div>`;
                    }
                    const n = (ev.num_choices && ev.num_choices > 0) ? ev.num_choices : 3;
                    const name = ev.event_name || `Event ${ev.story_id}`;
                    const autoTxt = (ev.auto_pick == null) ? 'auto'
                        : `auto: #${ev.auto_pick + 1}${ev.auto_source ? ' (' + ev.auto_source + ')' : ''}`;
                    const seenTxt = ev.count ? `seen ${ev.count}×` : 'not seen yet';
                    let opts = `<option value="-1"${ev.override == null ? ' selected' : ''}>Auto</option>`;
                    for (let i = 0; i < n; i++) opts += `<option value="${i}"${ev.override === i ? ' selected' : ''}>Choice ${i + 1}</option>`;
                    html += `
                        <div class="event-row${ev.override != null ? ' has-override' : ''}">
                            <div class="event-row-main">
                                <span class="event-name">${escapeHtml(name)}</span>
                                <span class="event-meta">${seenTxt} &middot; ${autoTxt}</span>
                            </div>
                            <select class="event-override" data-sid="${escapeAttr(ev.story_id)}">${opts}</select>
                        </div>`;
                });
                list.innerHTML = html;
                list.querySelectorAll('.event-override').forEach(sel => {
                    sel.addEventListener('change', async () => {
                        const sid = sel.getAttribute('data-sid');
                        const choice = parseInt(sel.value, 10);
                        try {
                            await apiJson('/api/events/override', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ story_id: sid, choice })
                            });
                            const row = sel.closest('.event-row');
                            if (row) row.classList.toggle('has-override', choice >= 0);
                        } catch (e) {}
                    });
                });
            } catch (e) {
                list.innerHTML = '<div class="events-empty">Could not load events.</div>';
            }
        }
        const eventsRefreshBtn = document.getElementById('events-refresh-btn');
        if (eventsRefreshBtn) eventsRefreshBtn.addEventListener('click', (e) => { e.stopPropagation(); loadEvents(); });
        // Load when the section is opened (selection/deck is defined by then; avoids
        // touching `selection` during initial setup).
        const eventsToggleEl = document.getElementById('events-toggle');
        if (eventsToggleEl) eventsToggleEl.addEventListener('click', () => {
            const body = document.getElementById('events-body');
            if (body && body.classList.contains('expanded')) loadEvents();
        });
        const applyTheme = theme => {
            const nextTheme = theme === 'blue' ? 'blue' : 'pink';
            document.documentElement.dataset.theme = nextTheme;
            document.documentElement.classList.toggle('theme-blue', nextTheme === 'blue');
            document.body.classList.toggle('theme-blue', nextTheme === 'blue');
            return nextTheme;
        };
        applyTheme(localStorage.getItem('theme'));
        const savedUsername = localStorage.getItem('saved_username');
        const savedPassword = localStorage.getItem('saved_password');
        if (savedUsername) document.getElementById('username').value = savedUsername;
        if (savedPassword) document.getElementById('password').value = savedPassword;
        let themeToggleClicks = 0;
        els.themeToggle.addEventListener('click', () => {
            const nextTheme = document.body.classList.contains('theme-blue') ? 'pink' : 'blue';
            applyTheme(nextTheme);
            localStorage.setItem('theme', nextTheme);
        });
        const sleep = ms => new Promise(resolve => window.setTimeout(resolve, ms));
        const nextFrame = () => new Promise(resolve => requestAnimationFrame(resolve));
        async function waitForDomPaint(frames = 2) {
            for (let i = 0; i < frames; i++) await nextFrame();
        }
        async function apiJson(url, options = {}) {
            const res = await fetch(url, options);
            return res.json();
        }
        function setMasterDataStatus(message, stateName = '') {
            if (!els.masterDataStatus) return;
            els.masterDataStatus.textContent = message || '';
            els.masterDataStatus.className = `master-data-status ${stateName}`.trim();
        }
        function applyMasterDataStatus(data) {
            if (!data) return;
            if (els.masterDataPath && data.master_mdb_path) {
                els.masterDataPath.value = data.master_mdb_path;
            }
            if (els.masterDataPath) {
                els.masterDataPath.classList.toggle('needs-action', !data.exists);
            }
            if (data.exists) {
                if (data.generation_error) {
                    setMasterDataStatus(data.generation_error, 'needs-action');
                } else if (data.generated) {
                    setMasterDataStatus('master.mdb found; data generated', 'ok');
                } else {
                    setMasterDataStatus('master.mdb found', 'ok');
                }
            } else {
                setMasterDataStatus(data.access_error || 'master.mdb not found; update the path', 'needs-action');
            }
        }
        async function loadMasterDataStatus() {
            if (!els.masterDataPath) return;
            try {
                applyMasterDataStatus(await apiJson('/api/master-data/status'));
            } catch (e) {
                setMasterDataStatus('Unable to read master data status', 'needs-action');
            }
        }
        async function saveMasterDataPath() {
            if (!els.masterDataPath) return null;
            const master_mdb_path = els.masterDataPath.value.trim();
            if (!master_mdb_path) {
                setMasterDataStatus('Enter the full path to master.mdb', 'needs-action');
                els.masterDataPath.classList.add('needs-action');
                return null;
            }
            if (els.masterDataSaveBtn) els.masterDataSaveBtn.disabled = true;
            setMasterDataStatus('Saving path and generating data...', 'working');
            const data = await apiJson('/api/master-data/path', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ master_mdb_path })
            });
            applyMasterDataStatus(data);
            if (data.exists && !data.generation_error) {
                await loadRaceData();
            }
            if (els.masterDataSaveBtn) els.masterDataSaveBtn.disabled = false;
            return data;
        }
        function bindMasterDataControls() {
            if (!els.masterDataPath) return;
            if (els.masterDataSaveBtn) {
                els.masterDataSaveBtn.addEventListener('click', async () => {
                    try {
                        await saveMasterDataPath();
                    } catch (e) {
                        setMasterDataStatus(e.message || 'Unable to save master.mdb path', 'needs-action');
                        if (els.masterDataPath) els.masterDataPath.classList.add('needs-action');
                    } finally {
                        if (els.masterDataSaveBtn) els.masterDataSaveBtn.disabled = false;
                    }
                });
            }
            els.masterDataPath.addEventListener('input', () => {
                els.masterDataPath.classList.remove('needs-action');
            });
            loadMasterDataStatus();
        }
        function setDiscordStatus(message, stateName = '') {
            if (!els.discordWebhookStatus) return;
            els.discordWebhookStatus.textContent = message || '';
            els.discordWebhookStatus.className = `master-data-status ${stateName}`.trim();
        }
        async function loadDiscordWebhook() {
            if (!els.discordWebhookUrl) return;
            try {
                const data = await apiJson('/api/settings/discord-webhook');
                if (data.webhook_url) els.discordWebhookUrl.value = data.webhook_url;
                if (els.discordNotifyForecast) els.discordNotifyForecast.checked = data.notify_forecast !== false;
                setDiscordStatus(data.configured ? 'Webhook saved' : 'Not configured', data.configured ? 'ok' : '');
            } catch (e) {
                setDiscordStatus('Could not read webhook status', 'needs-action');
            }
        }
        async function saveDiscordWebhook() {
            if (!els.discordWebhookUrl) return;
            const webhook_url = els.discordWebhookUrl.value.trim();
            const notify_forecast = els.discordNotifyForecast ? els.discordNotifyForecast.checked : true;
            if (els.discordWebhookSaveBtn) els.discordWebhookSaveBtn.disabled = true;
            setDiscordStatus('Saving...', 'working');
            try {
                const data = await apiJson('/api/settings/discord-webhook', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ webhook_url, notify_forecast })
                });
                setDiscordStatus(data.configured ? 'Webhook saved' : 'Webhook cleared', data.configured ? 'ok' : '');
            } catch (e) {
                setDiscordStatus(e.message || 'Failed to save webhook', 'needs-action');
            } finally {
                if (els.discordWebhookSaveBtn) els.discordWebhookSaveBtn.disabled = false;
            }
        }
        async function testDiscordWebhook() {
            if (els.discordWebhookTestBtn) els.discordWebhookTestBtn.disabled = true;
            setDiscordStatus('Sending test message...', 'working');
            try {
                const data = await apiJson('/api/settings/discord-webhook/test', { method: 'POST' });
                setDiscordStatus(
                    data.success ? 'Test message sent — check your Discord channel' : (data.detail || 'Failed to send test'),
                    data.success ? 'ok' : 'needs-action'
                );
            } catch (e) {
                setDiscordStatus(e.message || 'Failed to send test', 'needs-action');
            } finally {
                if (els.discordWebhookTestBtn) els.discordWebhookTestBtn.disabled = false;
            }
        }
        function bindDiscordWebhookControls() {
            if (!els.discordWebhookUrl) return;
            if (els.discordWebhookSaveBtn) els.discordWebhookSaveBtn.addEventListener('click', saveDiscordWebhook);
            if (els.discordWebhookTestBtn) els.discordWebhookTestBtn.addEventListener('click', testDiscordWebhook);
            els.discordWebhookUrl.addEventListener('input', () => setDiscordStatus(''));
            loadDiscordWebhook();
        }
        function writeLocalSetting(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
            } catch (e) {}
        }
        function readLocalSetting(value, fallback = null) {
            if (!value) return fallback;
            try {
                return JSON.parse(value);
            } catch (e) {
                return fallback;
            }
        }
        function escapeHtml(value) {
            return String(value ?? '').replace(/[&<>"']/g, char => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            }[char]));
        }
        function escapeAttr(value) {
            return escapeHtml(value);
        }
        function normalizeDelayBounds(min, max, disabled = false, restoreMin = null, restoreMax = null) {
            const fallbackMin = Number.isFinite(Number(restoreMin)) ? Number(restoreMin) : 1.6;
            const fallbackMax = Number.isFinite(Number(restoreMax)) ? Number(restoreMax) : 3.7;
            if (disabled) return { min: 0, max: 0, restoreMin: fallbackMin, restoreMax: fallbackMax, disabled: true };
            const left = Math.max(0, Number.isFinite(Number(min)) ? Number(min) : fallbackMin);
            let right = Math.max(0, Number.isFinite(Number(max)) ? Number(max) : fallbackMax);
            if (left > right) right = left;
            return { min: left, max: right, restoreMin: left, restoreMax: right, disabled: false };
        }
        function setDelayControls(settings) {
            if (!els.turnDelayMin || !els.turnDelayMax || !els.temptFateBtn) return;
            const disabled = Boolean(settings.disabled);
            const restoreMin = Number.isFinite(Number(settings.restoreMin)) ? Number(settings.restoreMin) : Number(settings.restore_min);
            const restoreMax = Number.isFinite(Number(settings.restoreMax)) ? Number(settings.restoreMax) : Number(settings.restore_max);
            els.turnDelayMin.value = String(settings.min);
            els.turnDelayMax.value = String(settings.max);
            els.turnDelayMin.dataset.restoreValue = String(Number.isFinite(restoreMin) ? restoreMin : settings.min);
            els.turnDelayMax.dataset.restoreValue = String(Number.isFinite(restoreMax) ? restoreMax : settings.max);
            els.turnDelayMin.disabled = disabled;
            els.turnDelayMax.disabled = disabled;
            els.temptFateBtn.classList.toggle('is-active', disabled);
            els.temptFateBtn.innerText = disabled ? 'NO CD ✓' : 'NO CD';
        }
        async function saveDelaySettings(settings) {
            setDelayControls(settings);
            const data = await apiJson('/api/settings/turn-delay', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });
            const normalized = normalizeDelayBounds(data.min, data.max, data.disabled, data.restore_min, data.restore_max);
            setDelayControls(normalized);
            writeLocalSetting(delaySettingsStorageKey, normalized);
        }
        async function loadDelaySettings() {
            if (!els.turnDelayMin || !els.turnDelayMax || !els.temptFateBtn) return;
            try {
                const data = await apiJson('/api/settings/turn-delay');
                setDelayControls(normalizeDelayBounds(data.min, data.max, data.disabled, data.restore_min, data.restore_max));
            } catch (e) {
                setDelayControls({ min: 1.6, max: 3.7, restoreMin: 1.6, restoreMax: 3.7, disabled: false });
            }
        }
        function bindDelayControls() {
            if (!els.turnDelayMin || !els.turnDelayMax || !els.temptFateBtn) return;
            const sync = () => {
                saveDelaySettings(normalizeDelayBounds(els.turnDelayMin.value, els.turnDelayMax.value, false));
            };
            els.turnDelayMin.addEventListener('input', sync);
            els.turnDelayMax.addEventListener('input', sync);
            els.temptFateBtn.addEventListener('click', () => {
                const active = els.temptFateBtn.classList.contains('is-active');
                const restoreMin = Number(els.turnDelayMin.dataset.restoreValue || 1.6);
                const restoreMax = Number(els.turnDelayMax.dataset.restoreValue || 3.7);
                saveDelaySettings(active
                    ? normalizeDelayBounds(restoreMin, restoreMax, false)
                    : normalizeDelayBounds(0, 0, true, restoreMin, restoreMax)
                );
            });
            loadDelaySettings();
        }
        window.addEventListener('storage', event => {
            if (event.key !== delaySettingsStorageKey || !event.newValue) return;
            const settings = readLocalSetting(event.newValue);
            if (settings) setDelayControls(normalizeDelayBounds(settings.min, settings.max, settings.disabled, settings.restoreMin, settings.restoreMax));
        });
        window.addEventListener('storage', event => {
            if (event.key !== burnClocksStorageKey || !event.newValue) return;
            setBurnClocks(readLocalSetting(event.newValue, false));
        });
        function resetLoginState() {
            state.isLoading = false;
            els.loginBtn.innerText = state.needs2fa ? 'VALIDATE' : 'LOGIN';
        }
        function showLoginError(message) {
            setLoadingScreen(false);
            els.errorMsg.innerText = String(message || 'FAIL').toUpperCase();
            els.errorMsg.style.display = 'block';
            resetLoginState();
        }
        function showTwoFactorPrompt() {
            setLoadingScreen(false);
            state.needs2fa = true;
            state.isLoading = false;
            els.standardFields.style.display = 'none';
            els.faFields.style.display = 'block';
            els.loginBtn.innerText = 'VALIDATE';
            els.errorMsg.innerText = '2FA REQUIRED';
            els.errorMsg.style.display = 'block';
        }
        function readLoginPayload() {
            return {
                username: document.getElementById('username').value,
                password: document.getElementById('password').value,
                code: document.getElementById('code').value
            };
        }
        function resetSelection() {
            selection.deck = null;
            selection.friend = null;
            selection.trainee = null;
            selection.veterans = [];
        }
        function hideBrokenImage(img) {
            img.onerror = null;
            img.style.display = 'none';
        }
        function setRecaptureStatus(msg, cls) {
            if (!els.recaptureStatus) return;
            els.recaptureStatus.textContent = msg || '';
            els.recaptureStatus.className = 'recapture-status' + (cls ? ' ' + cls : '');
        }
        async function pollRecapture() {
            try {
                const data = await apiJson('/api/auth/recapture/status');
                const cap = (data && data.capture) || {};
                if (cap.capturing) {
                    setRecaptureStatus(cap.message || 'Capturing…', 'working');
                    setTimeout(pollRecapture, 2000);
                } else {
                    setRecaptureStatus(cap.message || (cap.ok ? 'Done' : 'Failed'), cap.ok ? 'ok' : 'error');
                    if (els.recaptureBtn) els.recaptureBtn.disabled = false;
                }
            } catch (e) {
                setRecaptureStatus('Status check failed', 'error');
                if (els.recaptureBtn) els.recaptureBtn.disabled = false;
            }
        }
        async function doRecapture() {
            if (els.recaptureBtn) els.recaptureBtn.disabled = true;
            setRecaptureStatus('Starting capture…', 'working');
            try {
                const data = await apiJson('/api/auth/recapture', { method: 'POST' });
                if (!data || !data.success) {
                    setRecaptureStatus((data && data.detail) || 'Could not start capture', 'error');
                    if (els.recaptureBtn) els.recaptureBtn.disabled = false;
                    return;
                }
                const cap = data.capture || {};
                setRecaptureStatus(cap.message || 'Capturing…', 'working');
                setTimeout(pollRecapture, 2000);
            } catch (e) {
                setRecaptureStatus('Network error', 'error');
                if (els.recaptureBtn) els.recaptureBtn.disabled = false;
            }
        }
        if (els.recaptureBtn) els.recaptureBtn.addEventListener('click', doRecapture);
        const loginForm = document.getElementById('login-form');
        loginForm.addEventListener('submit', async event => {
            event.preventDefault();
            if (state.isLoading) return;
            state.isLoading = true;
            setLoadingScreen(true);
            els.loginBtn.innerText = 'WORKING...';
            els.errorMsg.style.display = 'none';
            const payload = readLoginPayload();
            try {
                const data = await apiJson('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (data.needs_2fa) {
                    showTwoFactorPrompt();
                } else if (data.success) {
                    if (payload.username) localStorage.setItem('saved_username', payload.username);
                    if (payload.password) localStorage.setItem('saved_password', payload.password);
                    await renderDashboard(data, { animateIntro: true, waitForIntro: true });
                    state.isLoading = false;
                } else {
                    showLoginError(data.detail || 'FAIL');
                }
            } catch (e) {
                showLoginError('NETWORK ERROR');
            }
        });

        els.logoutBtn.addEventListener('click', async () => {
            setLoadingScreen(false);
            try {
                await apiJson('/api/logout', { method: 'POST' });
            } catch (e) {}
            document.body.classList.remove('dashboard-mode');
            hideNavbar();
            els.loginView.style.display = 'flex';
            els.dashboardView.style.display = 'none';
            els.dashboardView.classList.remove('active');
            els.logoutBtn.style.display = 'none';
            if (els.refreshBtn) els.refreshBtn.style.display = 'none';
            els.standardFields.style.display = 'block';
            els.faFields.style.display = 'none';
            els.loginBtn.innerText = 'LOGIN';
            els.accountStrip.style.display = 'none';
            els.accountStrip.innerHTML = '';
            state.account = null;
            state.needs2fa = false;
            dashData = null;
            resetSelection();
            syncDashboardHeight();
            loginForm.reset();
        });

        if (els.refreshBtn) {
            els.refreshBtn.addEventListener('click', async () => {
                if (els.refreshBtn.disabled) return;
                els.refreshBtn.disabled = true;
                const original = els.refreshBtn.textContent;
                els.refreshBtn.textContent = '...';
                try {
                    // Pull fresh state from the game (detects careers/changes made in-game),
                    // then reload so the dashboard re-renders cleanly with the new state.
                    await apiJson('/api/session/refresh', { method: 'POST' });
                } catch (e) {}
                window.location.reload();
            });
        }

        const formatNumber = value => Number(value || 0).toLocaleString();
        function closeCareerModal() {
            els.careerModal.style.display = 'none';
            els.careerModalCopy.innerText = 'This will force-delete the ongoing career.';
            els.careerDeleteBtn.innerText = 'DELETE';
            state.isDeletingCareer = false;
        }
        function openCareerModal() {
            const career = state.account && state.account.career;
            if (!career || !career.active) return;
            els.careerModalCopy.innerText = 'This will force-delete the ongoing career.';
            els.careerModal.style.display = 'flex';
        }
        async function deleteCareer() {
            const career = state.account && state.account.career;
            if (!career || !career.active || state.isDeletingCareer) return;
            state.isDeletingCareer = true;
            els.careerDeleteBtn.innerText = 'DELETING';
            els.careerModalCopy.innerText = 'Deleting ongoing career...';
            try {
                const data = await apiJson('/api/career/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ current_turn: career.turn || 0 })
                });
                if (!data.success) throw new Error(data.detail || 'Delete failed');
                renderAccountStrip(data.account);
                closeCareerModal();
            } catch (e) {
                els.careerModalCopy.innerText = e.message || 'Delete failed';
                els.careerDeleteBtn.innerText = 'RETRY';
                state.isDeletingCareer = false;
            }
        }
        els.careerCancelBtn.addEventListener('click', closeCareerModal);
        els.careerDeleteBtn.addEventListener('click', deleteCareer);
        els.careerModal.addEventListener('click', event => {
            if (event.target === els.careerModal) closeCareerModal();
        });
        function syncBurnClocksControls() {
            if (!els.burnClocksBtn) return;
            const clocks = state.account ? Number(state.account.clocks || 0) : 0;
            const disabled = clocks <= 11;

            if (disabled) {
                state.burnClocks = false;
                els.burnClocksBtn.disabled = true;
                els.burnClocksBtn.classList.remove('is-active');
                els.burnClocksBtn.innerText = `BURN CLOCKS: LOW (${clocks})`;
            } else {
                els.burnClocksBtn.disabled = false;
                els.burnClocksBtn.classList.toggle('is-active', state.burnClocks);
                els.burnClocksBtn.innerText = `BURN CLOCKS: ${state.burnClocks ? 'ON' : 'OFF'}`;
            }
        }
        function setBurnClocks(value, options = {}) {
            state.burnClocks = Boolean(value);
            syncBurnClocksControls();
            if (options.persist) writeLocalSetting(burnClocksStorageKey, state.burnClocks);
        }
        function loadStoredBurnClocks() {
            if (state.runner && state.runner.running) return;
            const stored = readLocalSetting(localStorage.getItem(burnClocksStorageKey));
            if (stored !== null) setBurnClocks(stored);
        }

        function renderAccountStrip(account) {
            state.account = account || null;
            if (!account) {
                els.accountStrip.style.display = 'none';
                els.accountStrip.innerHTML = '';
                return;
            }
            const tp = account.tp || {};
            const career = account.career;
            const careerHtml = career && career.active ? `
                <div id="career-pill" class="account-pill pill-career account-pill-clickable">
                    <span class="label">CAREER</span>
                    <strong>ONGOING</strong>
                </div>
            ` : `<div class="account-pill" style="opacity: 0.25;">
                    <span class="label">CAREER</span>
                    <strong>NONE</strong>
                </div>`;
            const carrots = account.carrots || {};
            els.accountStrip.innerHTML = `
                <div class="account-pill pill-tp">
                    <span class="label">TP</span>
                    <strong>${tp.current || 0}/${tp.max || 0}</strong>
                </div>
                <div class="account-pill pill-carrots">
                    <span class="label">CARROTS</span>
                    <strong>${formatNumber(carrots.total)}</strong>
                </div>
                <div class="account-pill pill-gold">
                    <span class="label">GOLD</span>
                    <strong>${formatNumber(account.gold)}</strong>
                </div>
                <div class="account-pill pill-clk">
                    <span class="label">CLOCKS</span>
                    <strong>${formatNumber(account.clocks)}</strong>
                </div>
                ${careerHtml}
            `;
            els.accountStrip.style.display = 'flex';
            const careerPill = document.getElementById('career-pill');
            if (careerPill) careerPill.addEventListener('click', openCareerModal);
            loadStoredBurnClocks();
            syncBurnClocksControls();
        }

        els.burnClocksBtn.addEventListener('click', async () => {
            setBurnClocks(!state.burnClocks, { persist: true });
            if (state.runner && state.runner.running) {
                try {
                    const data = await apiJson('/api/career/runner/burn_clocks', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ burn_clocks: state.burnClocks })
                    });
                    if (!data.success) throw new Error(data.detail || 'Failed to update burn_clocks');
                    if (data.runner) applyRunnerSnapshot(data.runner);
                } catch (e) {
                    console.error("Failed to update burn_clocks mid-run", e);
                    if (state.runner && state.runner.burn_clocks !== undefined) {
                        setBurnClocks(state.runner.burn_clocks, { persist: true });
                    }
                }
            }
        });

        const rankMap = {
            1: 'G', 2: 'G+', 3: 'F', 4: 'F+', 5: 'E', 6: 'E+',
            7: 'D', 8: 'D+', 9: 'C', 10: 'C+', 11: 'B', 12: 'B+',
            13: 'A', 14: 'A+', 15: 'S', 16: 'S+', 17: 'SS', 18: 'SS+',
            19: 'UG', 20: 'UF', 21: 'UE', 22: 'UD'
        };
        let dashData = null;
        const selection = { deck: null, friend: null, trainee: null, veterans: [] };

        async function syncSelectionToServer() {
            try {
                const payload = {
                    deck: selection.deck,
                    friend: selection.friend,
                    trainee: selection.trainee,
                    veterans: selection.veterans
                };
                await apiJson('/api/selection', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ selection: payload })
                });
            } catch (e) {}
        }

        function deselect(action, idx) {
            if (action === 'deck') {
                document.querySelectorAll('.deck-container.selected').forEach(el => el.classList.remove('selected'));
                selection.deck = null;
            } else if (action === 'friend') {
                document.querySelectorAll('#friend-grid .grid-card.selected').forEach(el => el.classList.remove('selected'));
                selection.friend = null;
            } else if (action === 'trainee') {
                document.querySelectorAll('#uma-grid .grid-card.selected').forEach(el => el.classList.remove('selected'));
                selection.trainee = null;
            } else if (action === 'vet') {
                const vet = selection.veterans[idx];
                if (vet != null) {
                    const card = document.querySelectorAll('#parent-grid .grid-card')[vet._gridIdx];
                    if (card) card.classList.remove('selected');
                }
                selection.veterans.splice(idx, 1);
                updateVetSelectability();
            }
            renderTeamPanel();
            syncSelectionToServer();
        }
        function getStartMissingReason() {
            const activeCareer = state.account && state.account.career && state.account.career.active;
            if (!state.selectedPreset) return 'Select a preset';
            if (activeCareer) return '';
            if (!selection.deck) return 'Select a deck';
            if (!selection.friend) return 'Select a friend support';
            if (!selection.trainee) return 'Select a trainee';
            if (selection.veterans.length < 2) return 'Select two parents';
            const parentError = getParentSelectionError();
            if (parentError) return parentError;
            const tp = state.account && state.account.tp ? Number(state.account.tp.current || 0) : 0;
            if (state.account && tp < 30 && state.runCount === 1) return `Not enough TP: ${tp}/30`;
            return '';
        }
        function getParentLineageCards(parent) {
            if (!parent || !parent.tree) return [];
            return ['self', 'p1', 'p2', 'gp1', 'gp2', 'gp3', 'gp4']
                .map(key => Number(parent.tree[key] && parent.tree[key].card_id))
                .filter(Boolean);
        }
        function getParentSelectionError() {
            if (!selection.trainee) return '';
            const traineeId = Number(selection.trainee.id);
            const lineages = selection.veterans.map(getParentLineageCards);
            if (lineages.length < 2) return '';
            if (lineages.some(cards => cards[0] === traineeId)) return 'Direct parent is trainee';
            return '';
        }
        function syncStartButton() {
            const reason = getStartMissingReason();
            els.startCareerBtn.disabled = Boolean(reason) || state.isStartingCareer;
            if (state.isStartingCareer) {
                els.startCareerBtn.innerText = 'RUNNING...';
                els.startStatus.innerText = 'Starting runner...';
                els.startStatus.classList.remove('error');
            } else {
                const activeCareer = state.account && state.account.career && state.account.career.active;
                els.startCareerBtn.innerText = activeCareer ? 'RESUME CAREER' : 'RUN CAREER';
                els.startStatus.innerText = reason;
                els.startStatus.classList.toggle('error', false);
            }
            if (els.navRunBtn) {
                els.navRunBtn.disabled = els.startCareerBtn.disabled;
                const activeCareer = state.account && state.account.career && state.account.career.active;
                els.navRunBtn.innerText = state.isStartingCareer ? 'RUNNING' : (activeCareer ? 'RESUME' : 'RUN');
                els.navRunBtn.title = (!state.isStartingCareer && reason) ? reason : '';
            }
        }
        function renderTeamPanel() {
            document.getElementById('dashboard-view').classList.add('active');
            function setSlot(id, role, content, action, idx, emptyText = 'select') {
                const el = document.getElementById(id);
                el.className = content ? 'team-item filled' : 'team-item';
                el.onclick = content ? () => deselect(action, idx) : null;
                const clear = content ? '<span class="team-item-clear">clear</span>' : '';
                const empty = `<div class="team-item-empty">${emptyText}</div>`;
                el.innerHTML = `
                    <div class="team-item-head">
                        <span class="team-item-role">${role}</span>
                        ${clear}
                    </div>
                    ${content || empty}
                `;
            }
            if (selection.deck) {
                const thumbs = selection.deck.cards.map(c =>
                    `<img class="team-item-thumb" src="/api/images/${c.id || '10001'}.png" onerror="hideBrokenImage(this)">`
                ).join('');
                setSlot('team-slot-deck', 'Deck', `
                    <div class="team-item-body">
                        <div class="team-item-thumbs">${thumbs}</div>
                        <div class="team-item-text">
                            <span class="team-item-name">${selection.deck.name}</span>
                            <span class="team-item-sub">Slot ${selection.deck.id}</span>
                        </div>
                    </div>
                `, 'deck', null, 'select deck');
            } else {
                setSlot('team-slot-deck', 'Deck', null, 'deck', null, 'select deck');
            }
            if (selection.friend) {
                setSlot('team-slot-friend', 'Friend', `
                    <div class="team-item-body">
                        <img class="team-item-portrait" src="/api/images/${selection.friend.support_card_id || '10001'}.png" onerror="hideBrokenImage(this)">
                        <div class="team-item-text">
                            <span class="team-item-name">${selection.friend.support_name || 'Unknown'}</span>
                            <span class="team-item-sub">${selection.friend.type || '?'} | LB${selection.friend.limit_break_count ?? '?'}</span>
                        </div>
                    </div>
                `, 'friend', null, 'select friend');
            } else {
                setSlot('team-slot-friend', 'Friend', null, 'friend', null, 'select friend');
            }
            if (selection.trainee) {
                setSlot('team-slot-trainee', 'Trainee', `
                    <div class="team-item-body">
                        <img class="team-item-portrait" src="/api/images/${selection.trainee.id || '100101'}.png" onerror="hideBrokenImage(this)">
                        <div class="team-item-text">
                            <span class="team-item-name">${selection.trainee.name || 'Unknown'}</span>
                        </div>
                    </div>
                `, 'trainee', null, 'select trainee');
            } else {
                setSlot('team-slot-trainee', 'Trainee', null, 'trainee', null, 'select trainee');
            }
            ['team-slot-vet1', 'team-slot-vet2'].forEach((id, i) => {
                const vet = selection.veterans[i];
                if (vet) {
                    setSlot(id, `Parent ${i + 1}`, `
                        <div class="team-item-body">
                            <img class="team-item-portrait" src="/api/images/${vet.card_id || '100101'}.png" onerror="hideBrokenImage(this)">
                            <div class="team-item-text">
                                <span class="team-item-name">${vet.name || 'Unknown'}</span>
                                <span class="team-item-sub">${rankMap[vet.rank] || '??'}</span>
                            </div>
                        </div>
                    `, 'vet', i, 'select parent');
                } else {
                    setSlot(id, `Parent ${i + 1}`, null, 'vet', i, 'select parent');
                }
            });
            syncStartButton();
        }
                function updateVetSelectability() {
            const full = selection.veterans.length >= 2;
            document.querySelectorAll('#parent-grid .grid-card').forEach(card => {
                if (card.classList.contains('selected')) {
                    card.classList.remove('vet-full');
                } else {
                    card.classList.toggle('vet-full', full);
                }
            });
            syncStartButton();
        }
        function clampValue(value, min, max) {
            return Math.min(Math.max(value, min), max);
        }
        let activeSparkCard = null;
        let activeSparkTooltip = null;
        function positionSparkTooltip(card, tooltip = card.querySelector('.sparks-tooltip')) {
            if (!card || !tooltip) return;
            const rect = card.getBoundingClientRect();
            const tooltipRect = tooltip.getBoundingClientRect();
            const tooltipWidth = Math.min(tooltipRect.width || 620, window.innerWidth - 16);
            const tooltipHeight = tooltipRect.height || 320;
            const x = clampValue(rect.left + rect.width / 2, tooltipWidth / 2 + 8, window.innerWidth - tooltipWidth / 2 - 8);
            const y = Math.max(8, rect.top - tooltipHeight - 10);
            tooltip.style.setProperty('--tooltip-left', `${x}px`);
            tooltip.style.setProperty('--tooltip-top', `${y}px`);
        }
        function bindSparkTooltips() {
            document.querySelectorAll('body > .sparks-tooltip').forEach(tooltip => tooltip.remove());
            document.querySelectorAll('#parent-grid .grid-card').forEach(card => {
                const tooltip = card.querySelector('.sparks-tooltip');
                if (!tooltip) return;
                card.classList.add('has-sparks');
                const show = () => {
                    if (tooltip.parentElement !== document.body) document.body.appendChild(tooltip);
                    activeSparkCard = card;
                    activeSparkTooltip = tooltip;
                    positionSparkTooltip(card, tooltip);
                    tooltip.classList.add('is-visible');
                };
                const hide = () => {
                    if (activeSparkCard === card) {
                        activeSparkCard = null;
                        activeSparkTooltip = null;
                    }
                    tooltip.classList.remove('is-visible');
                };
                tooltip.addEventListener('click', event => event.stopPropagation());
                tooltip.addEventListener('mousedown', event => event.stopPropagation());
                card.addEventListener('mouseenter', show);
                card.addEventListener('mouseleave', hide);
                card.addEventListener('focusin', show);
                card.addEventListener('focusout', hide);
            });
        }
        document.addEventListener('scroll', () => {
            if (activeSparkCard && activeSparkTooltip) positionSparkTooltip(activeSparkCard, activeSparkTooltip);
        }, true);
        window.addEventListener('resize', () => {
            if (activeSparkCard && activeSparkTooltip) positionSparkTooltip(activeSparkCard, activeSparkTooltip);
        });
        function friendKey(friend) {
            return `${friend.viewer_id}:${friend.support_card_id}`;
        }
        function normalizedCardName(value) {
            return String(value || '').toLowerCase().replace(/\([^)]*\)/g, '').replace(/[^a-z0-9]+/g, '');
        }
        function friendAllowed(friend) {
            if (!friend) return false;
            const friendId = String(friend.support_card_id || '');
            const friendName = normalizedCardName(friend.support_name);
            if (selection.deck) {
                const deckIds = new Set(selection.deck.cards.map(card => String(card.id || '')));
                if (deckIds.has(friendId)) return false;
                const deckNames = new Set(selection.deck.cards.map(card => normalizedCardName(card.name)));
                if (friendName && deckNames.has(friendName)) return false;
            }
            if (selection.trainee && friendName && normalizedCardName(selection.trainee.name) === friendName) return false;
            return true;
        }
        function getVisibleFriends() {
            const friends = (dashData && dashData.friends) || [];
            return friends.filter(friendAllowed);
        }
        function clearInvalidFriendSelection() {
            if (selection.friend && !friendAllowed(selection.friend)) {
                selection.friend = null;
            }
        }
        function syncFriendSelection() {
            const visibleFriends = (dashData && dashData.visibleFriends) || [];
            document.querySelectorAll('#friend-grid .grid-card').forEach((el, i) => {
                const friend = visibleFriends[i];
                el.classList.toggle('selected', Boolean(selection.friend && friend && friendKey(selection.friend) === friendKey(friend)));
            });
        }
        function findDeckIndexForCareer(activeCareer) {
            const decks = (dashData && dashData.validDecks) || [];
            if (!activeCareer || !decks.length) return -1;
            if (activeCareer.deck_id) {
                const deckIdx = decks.findIndex(d => Number(d.id) === Number(activeCareer.deck_id));
                if (deckIdx >= 0) return deckIdx;
            }
            const supportIds = (activeCareer.support_card_ids || []).map(id => String(id)).filter(Boolean);
            if (!supportIds.length) return -1;
            const careerSet = new Set(supportIds);
            return decks.findIndex(deck => {
                const deckIds = (deck.cards || []).map(card => String(card.id || '')).filter(Boolean);
                return deckIds.length === careerSet.size && deckIds.every(id => careerSet.has(id));
            });
        }
        function selectCareerDeck(activeCareer) {
            const deckIdx = findDeckIndexForCareer(activeCareer);
            if (deckIdx >= 0) {
                selection.deck = dashData.validDecks[deckIdx];
                const deckEls = document.querySelectorAll('.deck-container');
                if (deckEls[deckIdx]) deckEls[deckIdx].classList.add('selected');
                return;
            }
            const supportCards = (activeCareer && activeCareer.support_cards) || [];
            if (supportCards.length) {
                selection.deck = {
                    id: activeCareer.deck_id || 'active',
                    name: activeCareer.deck_id ? `Deck ${activeCareer.deck_id}` : 'Active career deck',
                    cards: supportCards
                };
            }
        }
        function selectCareerFriend(activeCareer) {
            if (!activeCareer || !activeCareer.friend_viewer_id || !activeCareer.friend_card_id) return;
            state.pendingFriendSelection = {
                viewer_id: String(activeCareer.friend_viewer_id),
                support_card_id: String(activeCareer.friend_card_id)
            };
            if (activeCareer.friend) {
                selection.friend = {
                    ...activeCareer.friend,
                    viewer_id: String(activeCareer.friend_viewer_id),
                    support_card_id: String(activeCareer.friend_card_id)
                };
            }
        }
        async function loadRaceData() {
            try {
                const raceRes = await fetch('/assets/data/uma_race_data.json');
                const data = await raceRes.json();
                state.raceData = Array.isArray(data.races) ? data.races : [];
                syncSelectedPresetRaces();
                renderRaces();
            } catch (e) {}
        }

        function getCurrentPreset() {
            return (state.presets || []).find(p => p.name === state.selectedPreset);
        }

        function normalizePresetName(value) {
            return String(value || '').trim().replace(/[^a-zA-Z0-9._ -]+/g, '').replace(/\s+/g, ' ').trim();
        }

        function presetNameExists(name) {
            const normalized = normalizePresetName(name).toLowerCase();
            return Boolean(normalized && (state.presets || []).some(p => p.name.toLowerCase() === normalized));
        }

        function syncSelectedPresetRaces() {
            const current = getCurrentPreset();
            state.selectedRaces = (current?.extra_race_list || [])
                .map(id => parseInt(id, 10))
                .filter(id => Number.isFinite(id));
            state.racesDirty = false;
            updateRaceSaveStatus();
        }

        function getYearSlots(yearIdx) {
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const periods = ['Early', 'Late'];
            const yearLabels = ['Junior Year', 'Classic Year', 'Senior Year'];
            const slots = [];
            for (const month of months) {
                for (const period of periods) {
                    const label = period + ' ' + month;
                    const datePrefix = yearLabels[yearIdx] + ' ' + label;
                    const races = state.raceData.filter(r => r.date.includes(datePrefix));
                    slots.push({ period: label, races: races, yearIdx: yearIdx });
                }
            }
            return slots;
        }

        function raceKeys(race) {
            const keys = [race.id, ...(race.legacy_ids || [])];
            return keys.map(id => parseInt(id)).filter(id => Number.isFinite(id));
        }

        function raceSelected(race) {
            return raceKeys(race).some(id => state.selectedRaces.includes(id));
        }

        function renderRaces() {
            if (!els.raceOptionsContent) return;
            els.raceOptionsContent.innerHTML = '';

            const yearLabels = ['Junior Year', 'Classic Year', 'Senior Year'];
            yearLabels.forEach((label, yi) => {
                const block = document.createElement('div');
                block.className = 'race-year-block';
                block.innerHTML = `<div class="race-year-title">${label}</div>`;

                const grid = document.createElement('div');
                grid.className = 'race-time-grid';

                const slots = getYearSlots(yi);
                slots.forEach((slot, si) => {
                    const cell = document.createElement('div');
                    cell.className = 'race-time-cell';

                    const slotIds = slot.races.flatMap(r => raceKeys(r));
                    const selectedInSlot = state.selectedRaces.filter(id => slotIds.includes(id));
                    const mainRaceId = selectedInSlot[0];
                    const selected = slot.races.find(r => raceKeys(r).includes(mainRaceId));

                    let html = `<div class="race-time-label">${slot.period}</div>`;
                    if (selected) {
                        html += `
                            <div class="race-cell-selected-img">
                                <img src="/races/${encodeURIComponent(selected.name)}.png" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'">
                                <div class="race-image-fallback" style="display:none">${selected.type}</div>
                                <span class="race-cell-selected-grade badge-${selected.type.toLowerCase().replace('-', '')}">${selected.type}</span>
                            </div>
                            <div class="race-cell-selected-name">${escapeHtml(selected.name)}</div>
                        `;
                    } else {
                        html += `<div class="race-time-plus">+</div>`;
                    }

                    cell.innerHTML = html;
                    cell.onclick = () => openSlotPopup(slot, yi);
                    grid.appendChild(cell);
                });

                block.appendChild(grid);
                els.raceOptionsContent.appendChild(block);
            });
        }

        function openSlotPopup(slot, yearIdx) {
            const yearLabels = ['Junior Year', 'Classic Year', 'Senior Year'];
            els.racePopupTitle.textContent = `${yearLabels[yearIdx]} - ${slot.period}`;
            els.racePopupBody.innerHTML = '';

            if (slot.races.length === 0) {
                els.racePopupBody.innerHTML = '<div class="race-slot-popup-empty">No races available</div>';
            } else {
                const list = document.createElement('div');
                list.className = 'race-slot-popup-list';

                const slotIds = slot.races.flatMap(r => raceKeys(r));

                slot.races.forEach(race => {
                    const myIds = raceKeys(race);
                    const selectedInSlot = state.selectedRaces.filter(id => slotIds.includes(id));
                    const selIndex = selectedInSlot.findIndex(id => myIds.includes(id));
                    const isSelected = selIndex !== -1;

                    let badgeHtml = '<div class="race-slot-popup-check">✓</div>';
                    if (isSelected && state.scenarioType === "Mant" && selectedInSlot.length > 0) {
                        if (selIndex === 0) {
                            badgeHtml = '<div class="race-slot-popup-check main-race" style="font-size: 0.7rem; font-weight: bold; width: auto; padding: 0 8px; border-radius: 12px; background: rgba(255,255,255,0.2);">MAIN</div>';
                        } else {
                            badgeHtml = `<div class="race-slot-popup-check overwrite-race" style="font-size: 0.7rem; font-weight: bold; width: auto; padding: 0 8px; border-radius: 12px; background: rgba(255,255,255,0.1);">RIVAL OVERWRITE ${selIndex}</div>`;
                        }
                    }

                    const item = document.createElement('div');
                    item.className = `race-slot-popup-item ${isSelected ? 'on' : ''}`;
                    item.innerHTML = `
                        <div class="race-slot-popup-img">
                            <img src="/races/${encodeURIComponent(race.name)}.png" onerror="this.src='/broom.png'">
                        </div>
                        <div class="race-slot-popup-info">
                            <div class="race-slot-popup-name-row">
                                <span class="race-slot-popup-grade badge-${race.type.toLowerCase().replace('-', '')}">${race.type}</span>
                                <span class="race-slot-popup-name">${escapeHtml(race.name)}</span>
                            </div>
                            <div class="race-slot-popup-meta">
                                <span class="race-slot-popup-terrain ${race.terrain.toLowerCase()}">${race.terrain}</span>
                                <span class="race-slot-popup-distance">${race.distance}</span>
                            </div>
                        </div>
                        ${badgeHtml}
                    `;
                    item.onclick = async () => {
                        const isMant = state.scenarioType === "Mant";

                        if (isSelected) {
                            state.selectedRaces = state.selectedRaces.filter(id => !myIds.includes(id));
                        } else {
                            if (!isMant) {
                                state.selectedRaces = state.selectedRaces.filter(id => !slotIds.includes(id));
                            }
                            state.selectedRaces.push(parseInt(race.id));
                        }

                        openSlotPopup(slot, yearIdx);
                        renderRaces();
                        markRacesDirty();
                    };
                    list.appendChild(item);
                });
                els.racePopupBody.appendChild(list);
            }
            els.racePopupOverlay.style.display = 'flex';
        }

        function updateRaceSaveStatus() {
            if (!els.raceSaveStatus) return;
            els.raceSaveStatus.textContent = state.racesDirty ? '● Unsaved' : '';
            els.raceSaveStatus.className = state.racesDirty ? 'race-save-status dirty' : 'race-save-status';
        }
        function markRacesDirty() {
            state.racesDirty = true;
            updateRaceSaveStatus();
        }
        async function saveRaces() {
            if (!state.selectedPreset) {
                if (els.raceSaveStatus) { els.raceSaveStatus.textContent = 'Select a preset first'; els.raceSaveStatus.className = 'race-save-status dirty'; }
                return;
            }
            if (els.saveRacesBtn) els.saveRacesBtn.disabled = true;
            if (els.raceSaveStatus) { els.raceSaveStatus.textContent = 'Saving...'; els.raceSaveStatus.className = 'race-save-status'; }
            try {
                const current = getCurrentPreset();
                if (current) current.extra_race_list = [...state.selectedRaces];
                const data = await apiJson('/api/presets/save_races', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ preset_name: state.selectedPreset, races: state.selectedRaces })
                });
                if (data && data.success === false) throw new Error(data.detail || 'save failed');
                state.racesDirty = false;
                if (els.raceSaveStatus) { els.raceSaveStatus.textContent = `✓ Saved (${state.selectedRaces.length} races)`; els.raceSaveStatus.className = 'race-save-status saved'; }
            } catch (e) {
                if (els.raceSaveStatus) { els.raceSaveStatus.textContent = e.message || 'Failed to save'; els.raceSaveStatus.className = 'race-save-status dirty'; }
            } finally {
                if (els.saveRacesBtn) els.saveRacesBtn.disabled = false;
            }
        }

        function getTurnFromDate(dateStr) {
            const match = dateStr.match(/(\d+)年(\d+)月(前|後)半/);
            if (!match) return 0;
            const year = parseInt(match[1]);
            const month = parseInt(match[2]);
            const half = match[3] === '前' ? 0 : 1;
            return (year - 1) * 24 + (month - 1) * 2 + half + 1;
        }

        function bindRaceHandlers() {
            els.racePopupClose?.addEventListener('click', () => {
                els.racePopupOverlay.style.display = 'none';
            });
            els.racePopupOverlay?.addEventListener('click', (e) => {
                if (e.target === els.racePopupOverlay) els.racePopupOverlay.style.display = 'none';
            });
            els.saveRacesBtn?.addEventListener('click', saveRaces);

            makeSectionToggle('race-toggle', 'race-chevron', 'race-body', false);
        }

        let skillDataCache = null;
        let activeEditTier = null;
        let activeSkillFilter = null;
        let activeColorFilter = null;

        const SKILL_FILTERS = [
            { id: 101, label: 'Front' },
            { id: 102, label: 'Pace' },
            { id: 103, label: 'Late' },
            { id: 104, label: 'End' },
            { id: 201, label: 'Short' },
            { id: 202, label: 'Mile' },
            { id: 203, label: 'Medium' },
            { id: 204, label: 'Long' },
            { id: 502, label: 'Dirt' },
            { id: 'turf', label: 'Turf' }
        ];

        const COLOR_FILTERS = [
            { id: 'green', label: 'Green', color: '#4ade80', iconPrefixes: ['1001', '1002', '1003', '1004', '1005', '1006'] },
            { id: 'blue', label: 'Blue', color: '#60a5fa', iconPrefixes: ['2002'] },
            { id: 'yellow', label: 'Yellow', color: '#fbbf24', iconPrefixes: ['2001', '2004', '2005', '2006', '2009'] },
            { id: 'red', label: 'Red', color: '#f87171', iconPrefixes: ['3001', '3002', '3004', '3005', '3007'] }
        ];

        async function loadSkillData() {
            if (skillDataCache) return skillDataCache;
            try {
                const res = await apiJson('/api/skills');
                if (res.success && res.skills) {
                    const uniqueMap = new Map();
                    Object.entries(res.skills).forEach(([id, s]) => {
                        if (!uniqueMap.has(s.name)) {
                            uniqueMap.set(s.name, { id, ...s, tags: new Set(s.tags || []) });
                        } else {
                            const existing = uniqueMap.get(s.name);
                            if (s.rarity > existing.rarity) existing.rarity = s.rarity;
                            (s.tags || []).forEach(t => existing.tags.add(t));
                        }
                    });
                    skillDataCache = Array.from(uniqueMap.values()).map(s => ({ ...s, tags: Array.from(s.tags) }));
                    skillDataCache.sort((a, b) => a.name.localeCompare(b.name));
                    return skillDataCache;
                }
            } catch (e) {}
            return [];
        }

        function renderSkillFilters() {
            const container = document.getElementById('skill-filters');
            if (!container) return;
            
            let html = '<div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 4px;">';
            for (const filter of SKILL_FILTERS) {
                const isActive = activeSkillFilter === filter.id;
                const bg = isActive ? 'rgba(var(--accent-primary-rgb), 0.2)' : 'rgba(255,255,255,0.05)';
                const border = isActive ? 'var(--accent-primary)' : 'transparent';
                const color = isActive ? 'var(--text-main)' : '#a1a1aa';
                html += `<div class="skill-filter-chip affinity-filter" data-id="${filter.id}" style="padding: 0.35rem 0.75rem; border-radius: 1rem; font-size: 0.75rem; cursor: pointer; background: ${bg}; border: 1px solid ${border}; color: ${color}; font-weight: bold; transition: all 0.1s;">${filter.label}</div>`;
            }
            html += '</div><div style="display: flex; flex-wrap: wrap; gap: 4px;">';
            
            for (const filter of COLOR_FILTERS) {
                const isActive = activeColorFilter === filter.id;
                const bg = isActive ? `${filter.color}33` : 'rgba(255,255,255,0.05)';
                const border = isActive ? filter.color : 'transparent';
                const color = isActive ? 'var(--text-main)' : filter.color;
                html += `<div class="skill-filter-chip color-filter" data-color="${filter.id}" style="padding: 0.35rem 0.75rem; border-radius: 1rem; font-size: 0.75rem; cursor: pointer; background: ${bg}; border: 1px solid ${border}; color: ${color}; font-weight: bold; transition: all 0.1s;">${filter.label}</div>`;
            }
            html += '</div>';
            
            container.innerHTML = html;
            
            container.querySelectorAll('.affinity-filter').forEach(el => {
                el.addEventListener('click', () => {
                    let tagId = el.getAttribute('data-id');
                    if (tagId !== 'turf') tagId = Number(tagId);
                    
                    if (activeSkillFilter === tagId) activeSkillFilter = null;
                    else activeSkillFilter = tagId;
                    
                    renderSkillFilters();
                    renderSkillList();
                });
            });

            container.querySelectorAll('.color-filter').forEach(el => {
                el.addEventListener('click', () => {
                    const colorId = el.getAttribute('data-color');
                    
                    if (activeColorFilter === colorId) activeColorFilter = null;
                    else activeColorFilter = colorId;
                    
                    renderSkillFilters();
                    renderSkillList();
                });
            });
        }

        function renderSkillList() {
            const query = (els.skillSearch?.value || '').toLowerCase();
            const skills = skillDataCache || [];
            
            let count = 0;
            let html = '';
            for (const s of skills) {
                if (query && !s.name.toLowerCase().includes(query)) continue;
                
                if (activeSkillFilter !== null) {
                    const skillTags = s.tags || [];
                    if (activeSkillFilter === 'turf') {
                        if (skillTags.includes(502)) continue;
                    } else {
                        if (!skillTags.includes(activeSkillFilter)) continue;
                    }
                }
                
                if (activeColorFilter !== null) {
                    const iconId = String(s.icon_id || '');
                    const colorFilter = COLOR_FILTERS.find(filter => filter.id === activeColorFilter);
                    const skillColor = colorFilter && colorFilter.iconPrefixes.some(prefix => iconId.startsWith(prefix)) ? activeColorFilter : 'none';
                    
                    if (skillColor !== activeColorFilter) continue;
                }
                
                count++;
                
                html += `<div class="skill-list-item" data-name="${escapeAttr(s.name)}" style="padding: 0.5rem; background: rgba(255,255,255,0.03); border-radius: 4px; cursor: pointer; display: flex; align-items: center; gap: 8px; transition: background 0.1s;">
                    <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-main); font-size: 0.85rem;">${escapeHtml(s.name)}</span>
                </div>`;
            }
            
            if (els.skillList) {
                if (count === 0) {
                    els.skillList.innerHTML = `<div style="padding: 1rem; color: #a1a1aa; font-size: 0.85rem;">No skills found.</div>`;
                } else {
                    els.skillList.innerHTML = html;
                    els.skillList.querySelectorAll('.skill-list-item').forEach(el => {
                        el.addEventListener('click', () => {
                            const name = el.getAttribute('data-name');
                            addSkillToFocusedArea(name);
                        });
                        el.addEventListener('mouseenter', () => el.style.background = 'rgba(255,255,255,0.1)');
                        el.addEventListener('mouseleave', () => el.style.background = 'rgba(255,255,255,0.03)');
                    });
                }
            }
        }

        function renderSkillEditorRightSide() {
            const current = getCurrentPreset();
            if (!current) {
                if (els.skillTiersContainer) els.skillTiersContainer.innerHTML = '';
                if (els.skillBlacklistContainer) els.skillBlacklistContainer.innerHTML = '';
                return;
            }

            let tiersHtml = '';
            const storedTiers = current.learn_skill_list || [];
            const tiers = storedTiers.length > 0 ? storedTiers : [[]];
            tiers.forEach((tier, i) => {
                const isActive = activeEditTier === i;
                const itemsHtml = tier.map(s =>
                    `<div class="skill-tag">
                        ${escapeHtml(s)} <span class="skill-tag-del" data-tier="${i}" data-skill="${escapeAttr(s)}">&times;</span>
                    </div>`
                ).join('');

                tiersHtml += `
                <div class="skill-tier-dropzone ${isActive ? 'is-active' : ''}" data-tier="${i}">
                    <div class="skill-tier-header">
                        <span class="skill-tier-label">TIER ${i+1}</span>
                        <button class="btn btn-sm btn-danger-soft skill-editor-action tier-del-btn" data-tier="${i}">DEL</button>
                    </div>
                    <div class="skill-tag-list">
                        ${itemsHtml}
                    </div>
                </div>`;
            });
            if (els.skillTiersContainer) els.skillTiersContainer.innerHTML = tiersHtml;

            if (els.skillBlacklistContainer) {
                const isBlActive = activeEditTier === null;
                els.skillBlacklistContainer.classList.toggle('is-active', isBlActive);

                const blacklist = current.learn_skill_blacklist || [];
                els.skillBlacklistContainer.innerHTML = blacklist.map(s =>
                    `<div class="skill-tag blacklist">
                        ${escapeHtml(s)} <span class="skill-tag-del" data-blacklist="true" data-skill="${escapeAttr(s)}">&times;</span>
                    </div>`
                ).join('');
            }

            els.skillTiersContainer?.querySelectorAll('.skill-tier-dropzone').forEach(el => {
                el.addEventListener('click', (e) => {
                    if (e.target.classList.contains('tier-del-btn') || e.target.classList.contains('skill-tag-del')) return;
                    activeEditTier = parseInt(el.getAttribute('data-tier'));
                    renderSkillEditorRightSide();
                });
            });
            if (els.skillBlacklistContainer) {
                els.skillBlacklistContainer.onclick = (e) => {
                    if (e.target.classList.contains('skill-tag-del')) return;
                    activeEditTier = null;
                    renderSkillEditorRightSide();
                };
            }

            els.skillTiersContainer?.querySelectorAll('.tier-del-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const idx = parseInt(btn.getAttribute('data-tier'));
                    current.learn_skill_list = current.learn_skill_list || [];
                    current.learn_skill_list.splice(idx, 1);
                    if (activeEditTier === idx) activeEditTier = null;
                    else if (activeEditTier > idx) activeEditTier--;
                    await savePresetConfig();
                    renderSkillEditorRightSide();
                });
            });

            document.querySelectorAll('.skill-tag-del').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const skillName = btn.getAttribute('data-skill');
                    if (btn.hasAttribute('data-blacklist')) {
                        current.learn_skill_blacklist = current.learn_skill_blacklist.filter(s => s !== skillName);
                    } else {
                        const tierIdx = parseInt(btn.getAttribute('data-tier'));
                        current.learn_skill_list[tierIdx] = current.learn_skill_list[tierIdx].filter(s => s !== skillName);
                    }
                    await savePresetConfig();
                    renderSkillEditorRightSide();
                });
            });
        }

        async function addSkillToFocusedArea(name) {
            const current = getCurrentPreset();
            if (!current) return;

            if (activeEditTier === null) {
                if (!current.learn_skill_blacklist) current.learn_skill_blacklist = [];
                if (!current.learn_skill_blacklist.includes(name)) {
                    current.learn_skill_blacklist.push(name);
                }
            } else {
                if (!current.learn_skill_list) current.learn_skill_list = [];
                if (!current.learn_skill_list[activeEditTier]) current.learn_skill_list[activeEditTier] = [];
                if (!current.learn_skill_list[activeEditTier].includes(name)) {
                    current.learn_skill_list[activeEditTier].push(name);
                }
            }
            await savePresetConfig();
            renderSkillEditorRightSide();
        }

        function initSkillEditor() {
            if (!state.selectedPreset) return;
            activeEditTier = 0;

            els.skillModal.style.display = 'flex';
            if (els.skillSearch) els.skillSearch.value = '';
            activeSkillFilter = null;
            activeColorFilter = null;

            loadSkillData().then(() => {
                renderSkillFilters();
                renderSkillList();
            });
            renderSkillEditorRightSide();
        }

        async function savePresetConfig() {
            if (!state.selectedPreset || !state.presets) return;
            const current = getCurrentPreset();
            if (!current) return;

            current.learn_skill_threshold = parseInt(els.presetSkillThreshold.value) || 888;
            current.running_style = parseInt(els.presetRunningStyle?.value) || 1;

            try {
                await apiJson('/api/presets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ preset: current })
                });
            } catch (e) {}
        }

        function populatePresetUI() {
            if (!state.selectedPreset || !state.presets) return;
            const current = getCurrentPreset();
            if (!current) return;

            els.presetSkillThreshold.value = current.learn_skill_threshold || 888;
            if (els.presetRunningStyle) els.presetRunningStyle.value = current.running_style || 1;
        }

        function bindPresetHandlers() {
            if (els.presetSelect) {
                els.presetSelect.addEventListener('change', async (e) => {
                    state.selectedPreset = e.target.value;
                    localStorage.setItem('uma_selected_preset', state.selectedPreset);
                    syncSelectedPresetRaces();
                    populatePresetUI();
                    renderRaces();
                });
            }

            const saveHandler = () => savePresetConfig();
            els.presetSkillThreshold?.addEventListener('change', saveHandler);
            els.presetRunningStyle?.addEventListener('change', saveHandler);

            els.presetEditSkillsBtn?.addEventListener('click', () => {
                if (!state.selectedPreset) return;
                activeEditTier = 0;

                els.skillModal.style.display = 'flex';
                if (els.skillSearch) els.skillSearch.value = '';
                activeSkillFilter = null;

                loadSkillData().then(() => {
                    renderSkillFilters();
                    renderSkillList();
                });
                renderSkillEditorRightSide();
            });
            els.skillModalClose?.addEventListener('click', () => { els.skillModal.style.display = 'none'; });

            els.skillSearch?.addEventListener('input', renderSkillList);

            els.skillAddTierBtn?.addEventListener('click', async () => {
                const current = getCurrentPreset();
                if (!current) return;
                if (!current.learn_skill_list) current.learn_skill_list = [];
                current.learn_skill_list.push([]);
                activeEditTier = current.learn_skill_list.length - 1;
                await savePresetConfig();
                renderSkillEditorRightSide();
            });

            document.getElementById('skill-select-all-btn')?.addEventListener('click', async () => {
                const current = getCurrentPreset();
                if (!current) return;
                const visibleNodes = els.skillList?.querySelectorAll('.skill-list-item') || [];
                let changed = false;

                visibleNodes.forEach(node => {
                    const name = node.getAttribute('data-name');
                    if (activeEditTier === null) {
                        if (!current.learn_skill_blacklist) current.learn_skill_blacklist = [];
                        if (!current.learn_skill_blacklist.includes(name)) {
                            current.learn_skill_blacklist.push(name);
                            changed = true;
                        }
                    } else {
                        if (!current.learn_skill_list) current.learn_skill_list = [];
                        if (!current.learn_skill_list[activeEditTier]) current.learn_skill_list[activeEditTier] = [];
                        if (!current.learn_skill_list[activeEditTier].includes(name)) {
                            current.learn_skill_list[activeEditTier].push(name);
                            changed = true;
                        }
                    }
                });
                if (changed) {
                    await savePresetConfig();
                    renderSkillEditorRightSide();
                }
            });

            document.getElementById('skill-deselect-all-btn')?.addEventListener('click', async () => {
                const current = getCurrentPreset();
                if (!current) return;
                const visibleNodes = els.skillList?.querySelectorAll('.skill-list-item') || [];
                let changed = false;

                const namesToRemove = Array.from(visibleNodes).map(node => node.getAttribute('data-name'));

                if (activeEditTier === null) {
                    if (current.learn_skill_blacklist) {
                        const originalLen = current.learn_skill_blacklist.length;
                        current.learn_skill_blacklist = current.learn_skill_blacklist.filter(s => !namesToRemove.includes(s));
                        if (current.learn_skill_blacklist.length !== originalLen) changed = true;
                    }
                } else {
                    if (current.learn_skill_list && current.learn_skill_list[activeEditTier]) {
                        const originalLen = current.learn_skill_list[activeEditTier].length;
                        current.learn_skill_list[activeEditTier] = current.learn_skill_list[activeEditTier].filter(s => !namesToRemove.includes(s));
                        if (current.learn_skill_list[activeEditTier].length !== originalLen) changed = true;
                    }
                }

                if (changed) {
                    await savePresetConfig();
                    renderSkillEditorRightSide();
                }
            });

            document.getElementById('skill-blacklist-all-btn')?.addEventListener('click', async () => {
                const current = getCurrentPreset();
                if (!current) return;
                const visibleNodes = els.skillList?.querySelectorAll('.skill-list-item') || [];
                let changed = false;

                if (!current.learn_skill_blacklist) current.learn_skill_blacklist = [];
                visibleNodes.forEach(node => {
                    const name = node.getAttribute('data-name');
                    if (!current.learn_skill_blacklist.includes(name)) {
                        current.learn_skill_blacklist.push(name);
                        changed = true;
                    }
                });

                if (changed) {
                    await savePresetConfig();
                    renderSkillEditorRightSide();
                }
            });
            document.getElementById('skill-clear-blacklist-btn')?.addEventListener('click', async () => {
                const current = getCurrentPreset();
                if (!current) return;
                if (current.learn_skill_blacklist && current.learn_skill_blacklist.length > 0) {
                    current.learn_skill_blacklist = [];
                    await savePresetConfig();
                    renderSkillEditorRightSide();
                }
            });

            els.presetAddBtn?.addEventListener('click', async () => {
                const newName = prompt("Enter new preset name:");
                if (!newName || !newName.trim()) return;
                const normalizedName = normalizePresetName(newName);
                if (!normalizedName) {
                    alert("Preset name cannot be empty.");
                    return;
                }
                if (presetNameExists(normalizedName)) {
                    alert("A preset with that name already exists.");
                    return;
                }

                const newPreset = {
                    name: normalizedName,
                    running_style: 1,
                    learn_skill_list: [],
                    learn_skill_blacklist: [],
                    extra_race_list: [],
                    learn_skill_threshold: 888
                };

                try {
                    const res = await apiJson('/api/presets', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ preset: newPreset })
                    });
                    if (!res.success || !res.preset?.name) {
                        alert(res.detail || "Failed to save new preset.");
                        return;
                    }
                    state.selectedPreset = res.preset.name;
                    localStorage.setItem('uma_selected_preset', state.selectedPreset);
                    await loadPresets();
                    if (els.presetSelect) els.presetSelect.value = state.selectedPreset;
                    syncSelectedPresetRaces();
                    populatePresetUI();
                    renderRaces();
                } catch (e) { alert("Failed to save new preset."); }
            });

            els.presetDelBtn?.addEventListener('click', async () => {
                if (!state.selectedPreset) return;
                const deletedName = state.selectedPreset;
                if (!confirm(`Are you sure you want to delete preset '${deletedName}'?`)) return;

                try {
                    const res = await apiJson('/api/presets/delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name: deletedName })
                    });
                    if (!res.success) {
                        alert(res.detail || "Failed to delete preset.");
                        return;
                    }
                    await loadPresets();
                } catch (e) { alert("Failed to delete preset."); }
            });
        }

        async function loadPresets() {
            try {
                const res = await apiJson('/api/presets');
                if (res.success && res.presets && res.presets.length > 0) {
                    state.presets = res.presets;
                    if (els.presetSelect) {
                        els.presetSelect.innerHTML = state.presets.map(p => `<option value="${escapeAttr(p.name)}">${escapeHtml(p.name)}</option>`).join('');
                    }
                    const saved = localStorage.getItem('uma_selected_preset');
                    if (saved && state.presets.some(p => p.name === saved)) {
                        state.selectedPreset = saved;
                    } else {
                        state.selectedPreset = state.presets[0].name;
                    }
                    localStorage.setItem('uma_selected_preset', state.selectedPreset);
                    if (els.presetSelect) els.presetSelect.value = state.selectedPreset;
                    populatePresetUI();
                } else {
                    state.presets = [];
                    state.selectedPreset = "";
                    localStorage.removeItem('uma_selected_preset');
                    if (els.presetSelect) els.presetSelect.innerHTML = "";
                    populatePresetUI();
                }
            } catch(e) {
                state.presets = [];
                state.selectedPreset = "";
                localStorage.removeItem('uma_selected_preset');
                populatePresetUI();
            }
            syncStartButton();
            await loadRaceData();
        }

        function renderFriends() {
            const friends = (dashData && dashData.friends) || [];
            clearInvalidFriendSelection();
            const visibleFriends = getVisibleFriends();
            if (dashData) dashData.visibleFriends = visibleFriends;

            if (state.pendingFriendSelection) {
                const f = visibleFriends.find(v =>
                    String(v.viewer_id) === state.pendingFriendSelection.viewer_id &&
                    String(v.support_card_id) === state.pendingFriendSelection.support_card_id
                );
                if (f) {
                    selection.friend = f;
                    state.pendingFriendSelection = null;
                }
            }

            els.friendCount.innerText = `(${visibleFriends.length}/${friends.length})`;
            els.friendGrid.innerHTML = visibleFriends.map(friend => {
                const imgId = friend.support_card_id || '10001';
                const lb = friend.limit_break_count ?? '?';
                return `<div class="grid-card friend-card">
                    <img src="/api/images/${imgId}.png" onerror="hideBrokenImage(this)">
                    <div class="grid-card-overlay">
                        <span class="grid-card-name">${friend.support_name || 'Unknown'}</span>
                        <span class="grid-card-kicker">${friend.type || '?'} | LB${lb}</span>
                    </div>
                </div>`;
            }).filter(Boolean).join('');
            attachFriendHandlers();
            syncFriendSelection();
            renderTeamPanel();
        }
        function appendSeenFriendIds(ids) {
            if (!dashData) return;
            const seen = new Set(dashData.friendExcludeIds || []);
            (ids || []).forEach(id => {
                if (id) seen.add(id);
            });
            dashData.friendExcludeIds = Array.from(seen);
        }
        async function loadFriends(refresh = false) {
            if (!dashData || state.isFetchingFriends) return;
            const isCareerActive = dashData.account && dashData.account.career && dashData.account.career.active;
            if (isCareerActive) {
                els.friendRefreshBtn.disabled = true;
                els.friendStatus.classList.remove('error');
                els.friendStatus.innerText = 'Active career, endpoint blocked';
                return;
            }
            state.isFetchingFriends = true;
            els.friendRefreshBtn.disabled = true;
            els.friendStatus.classList.remove('error');
            els.friendStatus.innerText = refresh ? 'Refreshing friends...' : 'Loading friends...';
            const excludeIds = refresh ? (dashData.friendExcludeIds || []) : [];
            try {
                const data = await apiJson('/api/career/friends', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ exclude_viewer_ids: excludeIds })
                });
                if (!data.success) throw new Error(data.detail || 'Friend load failed');
                dashData.friends = data.friends || [];
                appendSeenFriendIds(data.exclude_viewer_ids || []);
                renderFriends();
                if (data.source === 'Active Career (Skip)') {
                    els.friendStatus.innerText = 'Active career, endpoint blocked';
                    return;
                }
                const source = data.source === 'initial' ? 'initial' : 'refresh';
                const visibleCount = ((dashData && dashData.visibleFriends) || []).length;
                els.friendStatus.innerText = `${source} list: ${visibleCount}/${dashData.friends.length} cards`;
            } catch (e) {
                els.friendStatus.innerText = e.message || 'Friend load failed';
                els.friendStatus.classList.add('error');
            } finally {
                state.isFetchingFriends = false;
                const stillActive = dashData.account && dashData.account.career && dashData.account.career.active;
                els.friendRefreshBtn.disabled = !!stillActive;
            }
        }
        function attachFriendHandlers() {
            const visibleFriends = (dashData && dashData.visibleFriends) || [];
            document.querySelectorAll('#friend-grid .grid-card').forEach((el, i) => {
                el.classList.add('selectable');
                el.addEventListener('click', () => {
                    const friend = visibleFriends[i];
                    const already = selection.friend && friendKey(selection.friend) === friendKey(friend);
                    document.querySelectorAll('#friend-grid .grid-card').forEach(c => c.classList.remove('selected'));
                    selection.friend = already ? null : friend;
                    if (!already) el.classList.add('selected');
                    renderTeamPanel();
                });
            });
        }
        function formatRunEstimate(n) {
            // rough: ~30-37 min per career (current pacing)
            const fmt = (m) => m < 90 ? `${Math.round(m)} min` : `${(m / 60).toFixed(1)} hr`;
            return `${fmt(n * 30)} – ${fmt(n * 37)}`;
        }
        function closeRunConfirm() {
            if (els.runConfirmModal) els.runConfirmModal.style.display = 'none';
        }
        function openRunConfirm() {
            const n = state.runCount;
            const activeCareer = state.account && state.account.career && state.account.career.active;
            const lead = activeCareer ? 'Resume the active career, then run ' : 'The bot will run ';
            let copy, infinite = false;
            if (n === 0) {
                infinite = true;
                copy = `<strong style="color:#ffcf48">⚠️ INFINITE MODE</strong><br>${lead}careers <strong>continuously</strong> until you click <strong>STOP</strong>. It won't stop on its own.`;
            } else if (n === 1) {
                copy = `${lead}<strong>1 career</strong> (single run), then stop.<br><span style="opacity:.7">Est. ~${formatRunEstimate(1)}</span>`;
            } else {
                copy = `${lead}<strong>${n} careers</strong> back-to-back, then stop automatically.<br><span style="opacity:.7">Est. total ~${formatRunEstimate(n)}</span>`;
            }
            els.runConfirmCopy.innerHTML = copy;
            els.runConfirmOk.textContent = infinite ? 'YES, RUN ∞' : `YES, RUN ${n}×`;
            els.runConfirmOk.classList.toggle('btn-danger', infinite);
            els.runConfirmOk.classList.toggle('btn-primary', !infinite);
            els.runConfirmModal.style.display = 'flex';
        }
        function requestStartCareer() {
            const reason = getStartMissingReason();
            if (reason || state.isStartingCareer) {
                syncStartButton();
                return;
            }
            openRunConfirm();
        }
        async function startCareer() {
            const reason = getStartMissingReason();
            if (reason || state.isStartingCareer) {
                syncStartButton();
                return;
            }
            state.isStartingCareer = true;
            syncStartButton();
            let finalMessage = '';
            let finalIsError = false;
            const activeCareer = state.account && state.account.career && state.account.career.active;
            const body = activeCareer ? {
                preset_name: state.selectedPreset,
                max_steps: 2500,
                burn_clocks: state.burnClocks,
                run_count: state.runCount
            } : {
                card_id: Number(selection.trainee.id),
                support_card_ids: selection.deck.cards.map(card => Number(card.id)),
                friend_viewer_id: Number(selection.friend.viewer_id),
                friend_card_id: Number(selection.friend.support_card_id),
                parent_id_1: Number(selection.veterans[0].instance_id),
                parent_id_2: Number(selection.veterans[1].instance_id),
                deck_id: Number(selection.deck.id),
                scenario_id: 4,
                use_tp: 30,
                difficulty_id: 0,
                difficulty: 0,
                is_boost: 0,
                boost_story_event_id: 0,
                preset_name: state.selectedPreset,
                max_steps: 2500,
                burn_clocks: state.burnClocks,
                run_count: state.runCount
            };
            try {
                const data = await apiJson('/api/career/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });
                if (!data.success) throw new Error(data.detail || 'Start failed');
                state.displayedClocksUsed = Number(data.runner && data.runner.clocks_used || 0);
                renderAccountStrip(data.account);
                if (data.account && data.account.career && data.account.career.active) {
                    autoLoadCareerSelection();
                    renderFriends();
                }
                startRunnerPolling();
                finalMessage = 'Career runner started';
            } catch (e) {
                finalMessage = e.message || 'Start failed';
                finalIsError = true;
                if (state.devEnabled) {
                    setDevEnabled(false, { persist: true });
                }
            } finally {
                state.isStartingCareer = false;
                syncStartButton();
                if (finalMessage) {
                    els.startStatus.innerText = finalMessage;
                    els.startStatus.classList.toggle('error', finalIsError);
                }
            }
        }
        function applyRunnerSettings(runner) {
            if (runner.running && runner.burn_clocks !== undefined && state.burnClocks !== runner.burn_clocks) {
                setBurnClocks(runner.burn_clocks, { persist: true });
            }
        }
        function applyRunnerClockUsage(runner) {
            const clocksUsed = Number(runner.clocks_used || 0);
            if (state.account && clocksUsed > state.displayedClocksUsed) {
                const delta = clocksUsed - state.displayedClocksUsed;
                state.account = {
                    ...state.account,
                    clocks: Math.max(0, Number(state.account.clocks || 0) - delta)
                };
                state.displayedClocksUsed = clocksUsed;
                renderAccountStrip(state.account);
            } else if (clocksUsed < state.displayedClocksUsed) {
                state.displayedClocksUsed = clocksUsed;
            }
        }
        function updatePauseButton(runner) {
            if (!els.navPauseBtn) return;
            const active = !!(runner && (runner.running || runner.loop_active));
            els.navPauseBtn.style.display = active ? '' : 'none';
            if (active) {
                const paused = !!(runner && runner.paused);
                els.navPauseBtn.textContent = paused ? 'RESUME' : 'PAUSE';
                els.navPauseBtn.classList.toggle('paused', paused);
            }
        }
        async function togglePause() {
            const paused = !!(state.runner && state.runner.paused);
            const endpoint = paused ? '/api/career/runner/resume' : '/api/career/runner/pause';
            els.navPauseBtn.disabled = true;
            try {
                const data = await apiJson(endpoint, { method: 'POST' });
                if (data && data.runner) applyRunnerSnapshot(data.runner);
            } catch (e) {
            } finally {
                els.navPauseBtn.disabled = false;
            }
        }
        function applyRunnerSnapshot(runner) {
            state.runner = runner;
            applyRunnerSettings(runner);
            applyRunnerClockUsage(runner);
            updatePauseButton(runner);
        }
        async function refreshRunnerStatus() {
            try {
                const data = await apiJson('/api/career/runner');
                if (!data.success || !data.runner) return;
                const runner = data.runner;
                applyRunnerSnapshot(runner);

                const rows = (runner.action_history && runner.action_history.length) ? runner.action_history : deriveActionHistory(runner.log || []);
                if (rows.length) renderActionHistory(rows);
                if (runner.running) {
                    els.startStatus.classList.toggle('error', false);
                    els.startStatus.classList.remove('backoff');
                    if (!rows.length) els.startStatus.innerText = `Turn ${runner.turn || '?'} / ${runner.last_action || 'running'} / ${runner.steps || 0}`;
                    return;
                }
                if (state.runnerTimer && !runner.loop_active) {
                    bgClearTimer(state.runnerTimer);
                    state.runnerTimer = 0;
                }
                if (runner.circuit_tripped) {
                    // Auto-backoff: the bot stopped itself after repeated server errors.
                    // Show it distinctly (amber, not red) so it doesn't read as a crash,
                    // and always show the message even when an action table is present.
                    els.startStatus.classList.toggle('error', false);
                    els.startStatus.classList.add('backoff');
                    els.startStatus.innerText = '🛑 Auto-backoff: too many server errors in a short time. The bot stopped ITSELF to protect your account — this is intentional, not a crash. Wait a while (ideally hours) before running again.';
                } else if (runner.last_error) {
                    els.startStatus.classList.remove('backoff');
                    els.startStatus.classList.toggle('error', true);
                    if (!rows.length) els.startStatus.innerText = runner.last_error;
                } else if (runner.finished && !runner.last_error) {
                    els.startStatus.classList.remove('backoff');
                    state.consecutiveRunnerFails = 0;
                    els.startStatus.classList.toggle('error', false);
                    if (!rows.length) els.startStatus.innerText = runner.loop_active ? 'Career finished! Restarting...' : 'Career finished!';
                    if (state.account && state.account.career) state.account.career.active = false;
                    renderAccountStrip(state.account);
                } else if (runner.steps) {
                    els.startStatus.classList.remove('backoff');
                    els.startStatus.classList.toggle('error', false);
                    if (!rows.length) els.startStatus.innerText = `Runner stopped after ${runner.steps} steps`;
                }
            } catch (e) {}
        }
        function renderActionHistory(rows) {
            if (!els.startStatus) return;
            if (!rows.length) {
                els.startStatus.innerText = '';
                return;
            }
            const formatStatsDetail = row => {
                const stats = row.stats || {};
                if (!Object.keys(stats).length) return row.detail || '';
                return [
                    `HP ${stats.hp ?? 0}/${stats.max_hp ?? 100}`,
                    `MOOD ${stats.motivation ?? 0}`,
                    `SPD ${stats.speed ?? 0} STA ${stats.stamina ?? 0} PWR ${stats.power ?? 0} GUT ${stats.guts ?? 0} WIT ${stats.wit ?? 0} SP ${stats.skill_point ?? 0}`
                ].join(' | ');
            };
            const body = rows.map(row => `
                    <tr>
                        <td>${escapeHtml(row.turn)}</td>
                        <td><span class="action-pill action-pill-${escapeAttr(normalizeHistoryAction(row).action)}">${escapeHtml(normalizeHistoryAction(row).action)}</span></td>
                        <td>${escapeHtml(row.facility)}</td>
                        <td class="action-history-detail">${escapeHtml(formatStatsDetail(row))}</td>
                    </tr>
                `).join('');
            els.startStatus.innerHTML = `
                <div class="action-history-wrap">
                    <table class="action-history-table">
                        <thead>
                            <tr>
                                <th>TURN</th>
                                <th>ACTION</th>
                                <th>FACILITY</th>
                                <th>DETAIL</th>
                            </tr>
                        </thead>
                        <tbody>${body}</tbody>
                    </table>
                </div>
            `;
            const wrap = els.startStatus.querySelector('.action-history-wrap');
            if (wrap) wrap.scrollTop = wrap.scrollHeight;
        }
        function deriveActionHistory(log) {
            return log.filter(item => ['command', 'race', 'race_progress', 'finish', 'api_delay', 'turn_delay', 'complex_delay'].includes(item.action)).map(item => {
                const detail = String(item.detail || '');
                let action = item.action;
                let facility = '';
                if (action === 'command') {
                    if (detail.startsWith('training ')) {
                        action = 'train';
                        facility = detail.replace('training ', '');
                    } else if (detail.startsWith('rest ')) {
                        action = 'rest';
                        facility = detail.replace('rest ', '');
                        if (['301', '302', '303', '304', '305', '390'].includes(facility)) action = 'recreation';
                    } else if (detail.startsWith('challenge ')) {
                        action = 'rest';
                        facility = detail.replace('challenge ', '');
                    } else if (detail.startsWith('recreation ')) {
                        action = 'recreation';
                        facility = detail.replace('recreation ', '');
                    } else if (detail.startsWith('command 8:')) {
                        action = 'medic';
                    }
                } else if (action === 'race_progress') {
                    action = 'race';
                }
                return { turn: item.turn, action, facility, detail };
            });
        }
        function normalizeHistoryAction(row) {
            const facility = String(row.facility ?? '');
            if (row.action === 'rest' && ['301', '302', '303', '304', '305', '390'].includes(facility)) {
                return { ...row, action: 'recreation' };
            }
            return row;
        }
        const timerWorkerBlob = new Blob([`
            let activeTimers = {};
            self.onmessage = function(e) {
                const { action, id, ms } = e.data;
                if (action === 'setInterval') {
                    activeTimers[id] = setInterval(() => postMessage({ id }), ms);
                } else if (action === 'setTimeout') {
                    activeTimers[id] = setTimeout(() => {
                        postMessage({ id });
                        delete activeTimers[id];
                    }, ms);
                } else if (action === 'clear') {
                    clearInterval(activeTimers[id]);
                    clearTimeout(activeTimers[id]);
                    delete activeTimers[id];
                }
            };
        `], {type: 'application/javascript'});
        const timerWorker = new Worker(URL.createObjectURL(timerWorkerBlob));
        let nextTimerId = 1;
        const timerCallbacks = {};
        timerWorker.onmessage = function(e) {
            if (timerCallbacks[e.data.id]) timerCallbacks[e.data.id]();
        };
        function bgSetInterval(cb, ms) {
            const id = nextTimerId++;
            timerCallbacks[id] = cb;
            timerWorker.postMessage({ action: 'setInterval', id, ms });
            return id;
        }
        function bgSetTimeout(cb, ms) {
            const id = nextTimerId++;
            timerCallbacks[id] = () => { delete timerCallbacks[id]; cb(); };
            timerWorker.postMessage({ action: 'setTimeout', id, ms });
            return id;
        }
        function bgClearTimer(id) {
            delete timerCallbacks[id];
            timerWorker.postMessage({ action: 'clear', id });
        }
        function startRunnerPolling() {
            if (state.runnerTimer) bgClearTimer(state.runnerTimer);
            refreshRunnerStatus();
            state.runnerTimer = bgSetInterval(refreshRunnerStatus, 1500);
        }
        els.friendRefreshBtn.addEventListener('click', event => {
            event.stopPropagation();
            loadFriends(true);
        });
        els.startCareerBtn.addEventListener('click', requestStartCareer);
        if (els.navRunBtn) els.navRunBtn.addEventListener('click', requestStartCareer);
        if (els.navPauseBtn) els.navPauseBtn.addEventListener('click', togglePause);
        if (els.runConfirmOk) els.runConfirmOk.addEventListener('click', () => { closeRunConfirm(); startCareer(); });
        if (els.runConfirmCancel) els.runConfirmCancel.addEventListener('click', closeRunConfirm);
        if (els.runConfirmModal) els.runConfirmModal.addEventListener('click', event => {
            if (event.target === els.runConfirmModal) closeRunConfirm();
        });

        function selectDeck(index, element) {
            const alreadySelected = element.classList.contains('selected');
            document.querySelectorAll('.deck-container.selected').forEach(card => card.classList.remove('selected'));
            selection.deck = null;
            if (!alreadySelected) {
                element.classList.add('selected');
                selection.deck = dashData.validDecks[index];
            }
            renderFriends();
            renderTeamPanel();
            syncSelectionToServer();
        }
        function selectTrainee(index, element) {
            const alreadySelected = element.classList.contains('selected');
            document.querySelectorAll('#uma-grid .grid-card.selected').forEach(card => card.classList.remove('selected'));
            selection.trainee = null;
            if (!alreadySelected) {
                element.classList.add('selected');
                selection.trainee = dashData.umas[index];
            }
            renderFriends();
            updateVetSelectability();
            renderTeamPanel();
            syncSelectionToServer();
        }
        function selectParent(index, element) {
            if (element.classList.contains('vet-full')) return;
            if (element.classList.contains('selected')) {
                element.classList.remove('selected');
                selection.veterans = selection.veterans.filter(parent => parent._gridIdx !== index);
            } else if (selection.veterans.length < 2) {
                element.classList.add('selected');
                selection.veterans.push({ ...dashData.parents[index], _gridIdx: index });
            }
            updateVetSelectability();
            renderTeamPanel();
            syncSelectionToServer();
        }
        function attachSelectionHandlers() {
            document.querySelectorAll('.deck-container').forEach((element, index) => {
                element.addEventListener('click', () => selectDeck(index, element));
            });
            document.querySelectorAll('#uma-grid .grid-card').forEach((element, index) => {
                element.classList.add('selectable');
                element.addEventListener('click', () => selectTrainee(index, element));
            });
            document.querySelectorAll('#parent-grid .grid-card').forEach((element, index) => {
                element.classList.add('selectable');
                element.addEventListener('click', () => selectParent(index, element));
            });
        }
        function isValidDeck(deck) {
            return deck.cards.every(card => {
                const id = card.id || '';
                const name = card.name || '';
                return !id.includes('{') && !id.includes('-') && !name.includes('Unknown');
            });
        }
        function renderCounts(data) {
            els.umaCount.innerText = `(${data.umas.length})`;
            els.cardCount.innerText = `(${data.supports.length})`;
            els.parentCount.innerText = `(${data.parents.length})`;
        }
        function renderDecks(decks) {
            els.deckList.innerHTML = decks.map(deck => {
                const cards = deck.cards.map(card => {
                    const imgId = card.id || '10001';
                    return `<div class="grid-card deck-card">
                        <img src="/api/images/${imgId}.png" onerror="hideBrokenImage(this)">
                        <div class="grid-card-overlay">
                            <span class="grid-card-kicker">${card.type || '?'} | ${card.rarity || '?'}</span>
                            <span class="grid-card-name">${card.name || 'Unknown'}</span>
                        </div>
                    </div>`;
                }).join('');
                return `<div class="deck-container">
                    <div class="deck-header">
                        <span>${deck.name.toUpperCase()}</span>
                        <span style="font-size:0.85rem; opacity:0.8">SLOT ${deck.id}</span>
                    </div>
                    <div class="deck-cards">${cards}</div>
                </div>`;
            }).join('');
        }
        function renderFactors(factors) {
            const star = String.fromCharCode(9733);
            return factors.map(factor => `
                <div class="factor-badge f-${factor.category}">
                    ${factor.name} <span class="stars">${star.repeat(factor.stars)}</span>
                </div>
            `).join('');
        }
        function renderWins(wins) {
            if (!wins || !wins.total) return '<span class="spark-win-chip">Wins --</span>';
            return `
                <span class="spark-win-chip">G1 ${wins.g1 || 0}</span>
                <span class="spark-win-chip">G2 ${wins.g2 || 0}</span>
                <span class="spark-win-chip">G3 ${wins.g3 || 0}</span>
            `;
        }
        function renderParentSparks(parent, fallbackImgId) {
            const tree = parent.tree || {};
            return ['self', 'p1', 'p2'].map(key => {
                const node = tree[key];
                if (!node || !node.factors || node.factors.length === 0) return '';
                const nodeImg = node.card_id || fallbackImgId;
                const nodeClass = key === 'self' ? 'spark-node spark-node-self' : 'spark-node';
                return `<div class="${nodeClass}" style="--node-bg: url('/api/images/${nodeImg}.png')">
                    <div class="spark-node-header">
                        <img class="spark-node-portrait" src="/api/images/${nodeImg}.png" onerror="hideBrokenImage(this)">
                        <div class="spark-node-meta">
                            <div class="spark-node-title">${node.name || `Card ${node.card_id || '?'}`}</div>
                            <div class="spark-win-row">${renderWins(node.wins)}</div>
                        </div>
                    </div>
                    <div class="spark-factor-list">
                        ${renderFactors(node.factors)}
                    </div>
                </div>`;
            }).join('');
        }
        function renderParents(parents) {
            els.parentGrid.innerHTML = parents.map(parent => {
                const imgId = parent.card_id || '100101';
                return `<div class="grid-card">
                    <div class="rank-badge">${rankMap[parent.rank] || '??'}</div>
                    <img src="/api/images/${imgId}.png" onerror="hideBrokenImage(this)">
                    <div class="sparks-tooltip" style="--spark-bg: url('/api/images/${imgId}.png')">
                        <div class="sparks-tooltip-title"></div>
                        <div class="sparks-tooltip-scroll">
                            <div class="sparks-lineage-grid">
                                ${renderParentSparks(parent, imgId)}
                            </div>
                        </div>
                    </div>
                    <div class="grid-card-overlay">
                        <span class="grid-card-kicker">ID: ${parent.instance_id || '?'}</span>
                        <span class="grid-card-name">${parent.name || 'Unknown'}</span>
                    </div>
                </div>`;
            }).join('');
        }
        function renderTrainees(umas) {
            els.umaGrid.innerHTML = umas.map(uma => {
                const imgId = uma.id || '100101';
                return `<div class="grid-card">
                    <img src="/api/images/${imgId}.png" onerror="hideBrokenImage(this)">
                    <div class="grid-card-overlay"><span class="grid-card-name">${uma.name || 'Unknown'}</span></div>
                </div>`;
            }).join('');
        }
        function renderSupports(supports) {
            els.cardGrid.innerHTML = supports.map(card => {
                const imgId = card.id || '10001';
                return `<div class="grid-card support-card">
                    <img src="/api/images/${imgId}.png" onerror="hideBrokenImage(this)">
                    <div class="grid-card-overlay">
                        <span class="grid-card-kicker">${(card.rarity || '?') + ' | ' + (card.type || '?')}</span>
                        <span class="grid-card-name">${card.name || 'Unknown'}</span>
                    </div>
                </div>`;
            }).join('');
        }
        function showDashboardView(data) {
            document.body.classList.add('dashboard-mode');
            els.loginView.style.display = 'none';
            els.dashboardView.style.display = '';
            els.dashboardView.classList.add('active');
            els.logoutBtn.style.display = 'block';
            if (els.refreshBtn) els.refreshBtn.style.display = 'block';
            showNavbar();
            renderAccountStrip(data.account);
            syncDashboardHeight();
        }

        function autoLoadCareerSelection() {
            const activeCareer = state.account && state.account.career && state.account.career.active ? state.account.career : null;
            if (!activeCareer) return;

            resetSelection();
            document.querySelectorAll('.deck-container.selected, #uma-grid .grid-card.selected, #parent-grid .grid-card.selected, #friend-grid .grid-card.selected')
                .forEach(el => el.classList.remove('selected'));

            selectCareerDeck(activeCareer);

            if (activeCareer.card_id && dashData.umas) {
                const umaIdx = dashData.umas.findIndex(u => String(u.id) === String(activeCareer.card_id));
                if (umaIdx >= 0) {
                    selection.trainee = dashData.umas[umaIdx];
                    const umaEls = document.querySelectorAll('#uma-grid .grid-card');
                    if (umaEls[umaIdx]) umaEls[umaIdx].classList.add('selected');
                }
            }

            if (dashData.parents) {
                const p1 = activeCareer.parent_id_1;
                const p2 = activeCareer.parent_id_2;

                if (p1 || p2) {
                    dashData.parents.forEach((p, idx) => {
                        const pId = Number(p.instance_id);
                        if ((p1 && pId === Number(p1)) || (p2 && pId === Number(p2))) {
                            if (selection.veterans.length < 2 && !selection.veterans.find(v => Number(v.instance_id) === pId)) {
                                p._gridIdx = idx;
                                selection.veterans.push(p);
                                const parentEls = document.querySelectorAll('#parent-grid .grid-card');
                                if (parentEls[idx]) parentEls[idx].classList.add('selected');
                            }
                        }
                    });
                    updateVetSelectability();
                }
            }

            selectCareerFriend(activeCareer);
            renderTeamPanel();
        }

        function applyServerSelection(serverSelection) {
            if (!serverSelection) return;
            if (serverSelection.deck && dashData.validDecks) {
                const deckIdx = dashData.validDecks.findIndex(d => Number(d.id) === Number(serverSelection.deck.id));
                if (deckIdx >= 0) {
                    selection.deck = dashData.validDecks[deckIdx];
                    const deckEls = document.querySelectorAll('.deck-container');
                    if (deckEls[deckIdx]) deckEls[deckIdx].classList.add('selected');
                }
            }
            if (serverSelection.trainee && dashData.umas) {
                const umaIdx = dashData.umas.findIndex(u => String(u.id) === String(serverSelection.trainee.id));
                if (umaIdx >= 0) {
                    selection.trainee = dashData.umas[umaIdx];
                    const umaEls = document.querySelectorAll('#uma-grid .grid-card');
                    if (umaEls[umaIdx]) umaEls[umaIdx].classList.add('selected');
                }
            }
            if (serverSelection.veterans && dashData.parents) {
                serverSelection.veterans.forEach(v => {
                    const pIdx = dashData.parents.findIndex(p => Number(p.instance_id) === Number(v.instance_id));
                    if (pIdx >= 0 && selection.veterans.length < 2) {
                        const parent = dashData.parents[pIdx];
                        parent._gridIdx = pIdx;
                        selection.veterans.push(parent);
                        const parentEls = document.querySelectorAll('#parent-grid .grid-card');
                        if (parentEls[pIdx]) parentEls[pIdx].classList.add('selected');
                    }
                });
                updateVetSelectability();
            }
            if (serverSelection.friend) {
                state.pendingFriendSelection = {
                    viewer_id: String(serverSelection.friend.viewer_id),
                    support_card_id: String(serverSelection.friend.support_card_id)
                };
            }
        }

        async function renderDashboard(data, options = {}) {
            dashData = data;
            dashData.validDecks = data.decks.filter(isValidDeck);
            dashData.friends = data.friends || [];
            dashData.friendExcludeIds = data.friendExcludeIds || [];
            showDashboardView(data);
            renderCounts(data);
            renderDecks(dashData.validDecks);
            renderParents(data.parents);
            renderTrainees(dashData.umas);
            renderSupports(data.supports);
            resetSelection();
            if (data.selection) applyServerSelection(data.selection);
            autoLoadCareerSelection();

            await loadPresets();
            if (!dashData.friends.length) {
                loadFriends(false);
            } else {
                renderFriends();
            }
            bindSparkTooltips();
            attachSelectionHandlers();
            bindRaceHandlers();
            bindPresetHandlers();
            renderTeamPanel();

            startRunnerPolling();
            await waitForDomPaint(2);
            setLoadingScreen(false);
            await waitForDomPaint(2);
            if (options.animateIntro !== false) {
                playBrandIntro();
                if (options.waitForIntro) await sleep(780);
            }
        }

        async function restoreSession() {
            try {
                const data = await apiJson('/api/session?t=' + Date.now());
                if (data && data.success) await renderDashboard(data, { animateIntro: true, waitForIntro: false });
                else {
                    hideNavbar();
                    setLoadingScreen(false);
                }
            } catch (e) {
                hideNavbar();
                setLoadingScreen(false);
            }
        }
        bindDelayControls();
        bindMasterDataControls();
        bindDiscordWebhookControls();
        setLoadingScreen(true);
        restoreSession();
})();
