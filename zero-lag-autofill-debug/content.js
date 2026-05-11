// ═══════════════════════════════════════════════════════════════
// ZERO-AG AUTO-FILL DEBUG — Content Script with Heavy Logging
// ═══════════════════════════════════════════════════════════════

(function() {
  'use strict';

  console.log('[ZLAF-CS] Content script loaded on:', location.href);

  if (window.__ZLAF_INIT__) {
    console.log('[ZLAF-CS] Already initialized, skipping');
    return;
  }
  window.__ZLAF_INIT__ = true;

  const PLATFORM_SELECTORS = {
    greenhouse: 'form input, form select, form textarea, [data-qa="input"], .application--input',
    ashby: 'input, select, textarea, [data-testid*="input"], [data-testid*="field"], [class*="input"], [class*="field"]',
    lever: 'form input, form select, form textarea, .application-field input, .application-field select, .application-field textarea',
    wellfound: 'form input, form select, form textarea, [data-test="job-application-form"] input',
    instahyre: 'form input, form select, form textarea, .application-form input, .application-form select',
    generic: 'form input, form select, form textarea'
  };

  function detectPlatform() {
    const host = location.host.toLowerCase();
    if (host.includes('greenhouse')) return 'greenhouse';
    if (host.includes('ashbyhq')) return 'ashby';
    if (host.includes('lever')) return 'lever';
    if (host.includes('wellfound') || host.includes('angel')) return 'wellfound';
    if (host.includes('instahyre')) return 'instahyre';
    return 'generic';
  }

  function extractForm() {
    console.log('[ZLAF-CS] Extracting form...');
    const platform = detectPlatform();
    console.log('[ZLAF-CS] Detected platform:', platform);

    // Try shadow DOM first (Ashby uses it)
    let shadowInputs = [];
    document.querySelectorAll('*').forEach(el => {
        if (el.shadowRoot) {
            el.shadowRoot.querySelectorAll('input, select, textarea').forEach(s => shadowInputs.push(s));
        }
    });
    console.log('[ZLAF-CS] Shadow DOM inputs found:', shadowInputs.length);

    const selector = PLATFORM_SELECTORS[platform] || PLATFORM_SELECTORS.generic;
    const elements = shadowInputs.length > 0 ? shadowInputs : document.querySelectorAll(selector);
    console.log('[ZLAF-CS] Found', elements.length, 'elements with selector:', selector);

    const fields = [];

    elements.forEach(el => {
      const type = (el.type || 'text').toLowerCase();
      if (type === 'file' || type === 'hidden' || type === 'submit' || type === 'button') return;

      const field = {
        tag: el.tagName.toLowerCase(),
        type: type,
        name: el.name || null,
        id: el.id || null,
        placeholder: el.placeholder || null,
        required: el.required || false,
        label: extractLabel(el),
        options: el.tagName === 'SELECT' ? Array.from(el.options).map(o => o.text.trim()) : null
      };

      const key = (field.name || '') + '|' + (field.id || '');
      if (!fields.find(f => (f.name || '') + '|' + (f.id || '') === key)) {
        fields.push(field);
      }
    });

    console.log('[ZLAF-CS] Extracted', fields.length, 'fields');
    console.log('[ZLAF-CS] Fields:', JSON.stringify(fields, null, 2));
    return { platform, url: location.href, fields };
  }

  function extractLabel(el) {
    if (el.id) {
      const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (lbl) return lbl.innerText.trim();
    }
    const parent = el.closest('label, .field, .form-group, .application-field');
    if (parent) {
      const txt = parent.querySelector('label, .label, .field-label, [class*="label"]');
      if (txt) return txt.innerText.trim();
    }
    return el.getAttribute('aria-label') || el.getAttribute('placeholder') || null;
  }

  function waitForStableDOM(timeout = 4000) {
    return new Promise(resolve => {
      let last = -1, stable = 0;
      const iv = setInterval(() => {
        const count = document.querySelectorAll('input, select, textarea').length;
        if (count === last && count > 0) {
          if (++stable >= 2) { clearInterval(iv); resolve(); }
        } else {
          stable = 0; last = count;
        }
      }, 400);
      setTimeout(() => { clearInterval(iv); resolve(); }, timeout);
    });
  }

  function fillForm(mapping) {
    console.log('[ZLAF-CS] fillForm called with mapping:', JSON.stringify(mapping, null, 2));
    let filled = 0, skipped = 0, total = Object.keys(mapping).length;

    Object.entries(mapping).forEach(([key, value]) => {
      console.log('[ZLAF-CS] Processing key:', key, 'value:', value);
      if (value === null || value === undefined || value === 'null') {
        console.log('[ZLAF-CS] Skipping null value for:', key);
        skipped++; return;
      }

      let el = document.querySelector(`[name="${CSS.escape(key)}"]`) ||
               document.querySelector(`#${CSS.escape(key)}`);

      if (!el) {
        el = Array.from(document.querySelectorAll('input, select, textarea'))
          .find(inp => inp.name && inp.name.includes(key));
      }
      if (!el) { 
        console.log('[ZLAF-CS] Element not found for key:', key);
        skipped++; return; 
      }

      console.log('[ZLAF-CS] Found element:', el.tagName, 'type:', el.type, 'name:', el.name, 'id:', el.id);

      const tag = el.tagName.toLowerCase();
      const type = (el.type || 'text').toLowerCase();
      const strVal = String(value);

      highlightField(el);

      if (tag === 'select') {
        const opt = Array.from(el.options).find(o =>
          o.text.toLowerCase().includes(strVal.toLowerCase()) ||
          o.value.toLowerCase() === strVal.toLowerCase()
        );
        if (opt) {
          el.value = opt.value;
          el.dispatchEvent(new Event('change', { bubbles: true }));
          el.dispatchEvent(new Event('input', { bubbles: true }));
          filled++;
          console.log('[ZLAF-CS] Filled select:', key, 'with:', opt.text);
        } else { 
          console.log('[ZLAF-CS] No matching option for:', key, 'value:', strVal);
          skipped++; 
        }
      }
      else if (tag === 'textarea' || ['text','email','tel','url','password','number'].includes(type)) {
        el.focus();
        el.value = strVal;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.blur();
        filled++;
        console.log('[ZLAF-CS] Filled input:', key, 'with:', strVal);
      }
      else if (type === 'radio' || type === 'checkbox') {
        const shouldCheck = ['yes','true','1','on'].includes(strVal.toLowerCase());
        if (shouldCheck !== el.checked) {
          el.checked = shouldCheck;
          el.dispatchEvent(new Event('change', { bubbles: true }));
          filled++;
        } else { skipped++; }
      }
      else { skipped++; }
    });

    console.log('[ZLAF-CS] Fill complete — filled:', filled, 'skipped:', skipped, 'total:', total);
    return { filled, skipped, total };
  }

  function highlightField(el) {
    const orig = el.style.transition;
    el.style.transition = 'box-shadow 0.3s ease';
    el.style.boxShadow = '0 0 0 2px #00c85340';
    setTimeout(() => {
      el.style.boxShadow = '';
      el.style.transition = orig;
    }, 2000);
  }

  function showToast(msg, isError = false) {
    const id = 'zlaf-toast';
    document.getElementById(id)?.remove();

    const div = document.createElement('div');
    div.id = id;
    div.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px">
        <span style="font-size:16px">${isError ? '⚠️' : '⚡'}</span>
        <span style="white-space:pre-line">${msg}</span>
      </div>
    `;
    div.style.cssText = `
      position:fixed; top:20px; right:20px; z-index:2147483647;
      padding:14px 20px; border-radius:10px; font-family:system-ui,sans-serif;
      font-size:13px; font-weight:500; color:#fff; max-width:380px; line-height:1.5;
      background:${isError ? '#ff6d00' : '#00c853'};
      box-shadow:0 8px 24px rgba(0,0,0,0.25);
      animation:zlafSlide 0.35s cubic-bezier(0.16,1,0.3,1);
    `;

    const style = document.createElement('style');
    style.textContent = `@keyframes zlafSlide{from{transform:translateX(120%);opacity:0}to{transform:translateX(0);opacity:1}}`;
    div.appendChild(style);
    document.body.appendChild(div);
    setTimeout(() => div.remove(), isError ? 10000 : 4000);
  }

  function signalQueueComplete() {
    try {
      chrome.runtime.sendMessage({ action: 'queueItemComplete' });
    } catch(e) {}
  }

  // ─── Listen for messages ─────────────────────────────────────
  chrome.runtime.onMessage.addListener((req, sender, sendResponse) => {
    console.log('[ZLAF-CS] Received message:', req.action);
    if (req.action === 'showToast') {
      showToast(req.payload.msg, req.payload.isError);
      sendResponse({ shown: true });
    }
    if (req.action === 'forceFill') {
      console.log('[ZLAF-CS] Force fill triggered');
      run(true);
      sendResponse({ started: true });
    }
    return true;
  });

  // ─── Main Flow ───────────────────────────────────────────────
  async function run(isQueueItem = false) {
    console.log('[ZLAF-CS] run() called, isQueueItem:', isQueueItem);

    const { enabled, profileJson } = await chrome.storage.local.get(['enabled', 'profileJson']);
    console.log('[ZLAF-CS] State:', { enabled, hasProfile: !!profileJson });

    if (!enabled && !isQueueItem) {
      console.log('[ZLAF-CS] Extension disabled, skipping');
      return;
    }
    if (!profileJson) {
      console.log('[ZLAF-CS] No profile loaded');
      showToast('No profile loaded.\nAdd via popup or wait for Sheet AI.', true);
      if (isQueueItem) signalQueueComplete();
      return;
    }

    console.log('[ZLAF-CS] Waiting for stable DOM...');
    await waitForStableDOM();

    const form = extractForm();
    if (form.fields.length === 0) {
      console.log('[ZLAF-CS] No form fields found');
      if (isQueueItem) signalQueueComplete();
      return;
    }

    // Check cache
    const cacheKey = 'zlaf_cache_' + btoa(location.pathname).replace(/[^a-z0-9]/gi,'');
    const { [cacheKey]: cached } = await chrome.storage.local.get(cacheKey);

    if (cached && (Date.now() - cached.ts) < 86400000) {
      console.log('[ZLAF-CS] Using cached mapping');
      const res = fillForm(cached.mapping);
      showToast(`✅ ${res.filled}/${res.total} filled (cached)`);
      if (isQueueItem) setTimeout(signalQueueComplete, 1500);
      return;
    }

    showToast('🔍 Analyzing form with AI...');
    console.log('[ZLAF-CS] Sending fillForm message to background...');

    chrome.runtime.sendMessage(
      { action: 'fillForm', payload: { formStructure: form, profileJson } },
      (response) => {
        console.log('[ZLAF-CS] Response received:', response);

        if (chrome.runtime.lastError) {
          console.error('[ZLAF-CS] Runtime error:', chrome.runtime.lastError);
          showToast('❌ Extension error:\n' + chrome.runtime.lastError.message, true);
          if (isQueueItem) signalQueueComplete();
          return;
        }
        if (!response) {
          console.error('[ZLAF-CS] No response from background');
          showToast('❌ No response from background script\nCheck Service Worker', true);
          if (isQueueItem) signalQueueComplete();
          return;
        }
        if (!response.success) {
          console.error('[ZLAF-CS] Background reported error:', response.error);
          showToast('❌ ALL PROVIDERS FAILED\n' + response.error, true);
          if (isQueueItem) signalQueueComplete();
          return;
        }

        const { mapping, source } = response.data;
        console.log('[ZLAF-CS] Success! Source:', source, 'Mapping keys:', Object.keys(mapping).length);
        const res = fillForm(mapping);
        chrome.storage.local.set({ [cacheKey]: { mapping, ts: Date.now() } });

        const sourceEmoji = source.includes('nvidia') ? '🟢 NVIDIA' : source.includes('gemini') ? '🔵 Gemini' : '🟣 Groq';
        showToast(`✅ ${res.filled}/${res.total} fields filled\n${sourceEmoji} (${source})`);

        if (isQueueItem) setTimeout(signalQueueComplete, 1500);
      }
    );
  }

  // ─── Auto-trigger ────────────────────────────────────────────
  console.log('[ZLAF-CS] Setting up auto-trigger...');
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      console.log('[ZLAF-CS] DOMContentLoaded fired');
      setTimeout(() => run(false), 800);
    });
  } else {
    console.log('[ZLAF-CS] Document already loaded, running now');
    setTimeout(() => run(false), 800);
  }

  // SPA navigation detection
  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      console.log('[ZLAF-CS] URL changed:', lastUrl, '->', location.href);
      lastUrl = location.href;
      setTimeout(() => run(false), 1200);
    }
  }).observe(document, { subtree: true, childList: true });

})();
