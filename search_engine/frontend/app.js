/**
 * Deep Strata — Geology Search Engine
 * Frontend orchestration: search, sub-tabs, collapsible frames, rendering.
 */

// ── DOM refs ─────────────────────────────────────────────────
const heroZone = document.getElementById('heroZone');
const searchForm = document.getElementById('searchForm');
const queryInput = document.getElementById('queryInput');
const modelPills = document.getElementById('modelPills');
const metaBar = document.getElementById('metaBar');
const metaContent = document.getElementById('metaContent');
const strata = document.getElementById('strata');

const relevanceResults = document.getElementById('relevanceResults');
const relevanceSubtabs = document.getElementById('relevanceSubtabs');
const clusterLegend = document.getElementById('clusterLegend');
const clustersResults = document.getElementById('clustersResults');
const expansionBanner = document.getElementById('expansionBanner');
const expansionResults = document.getElementById('expansionResults');
const googleBody = document.getElementById('googleBody');
const bingBody = document.getElementById('bingBody');
const googleTeaser = document.getElementById('googleTeaser');
const bingTeaser = document.getElementById('bingTeaser');

// ── State ────────────────────────────────────────────────────
let currentModel = 'combined';
let lastData = null;         // cache full response for sub-tab switching
let allModelResults = {};    // cached per-model results for instant subtab switching

// ── Cluster colors (deterministic for up to 8 clusters) ──────
const CLUSTER_COLORS = [
    '#c8a96e', '#6ec8b4', '#8a6ec8', '#4285f4',
    '#00b4d8', '#e07a5f', '#81b29a', '#f2cc8f',
];

// ── Helpers ───────────────────────────────────────────────────

function esc(text) {
    const el = document.createElement('span');
    el.textContent = text || '';
    return el.innerHTML;
}

function shortUrl(url) {
    try {
        const u = new URL(url);
        let p = u.pathname;
        if (p.length > 45) p = p.slice(0, 42) + '...';
        return u.hostname + p;
    } catch { return url; }
}

function spinnerHtml() {
    return '<div class="spinner"><div class="spinner__dot"></div><div class="spinner__dot"></div><div class="spinner__dot"></div></div>';
}

function renderResultRow(doc, opts = {}) {
    const rank = doc.rank ? String(doc.rank).padStart(2, '0') : '';
    const score = doc.score != null ? `score: ${doc.score.toFixed(4)}` : '';
    const badge = opts.badge ? `<span class="result-row__badge">${esc(opts.badge)}</span>` : '';
    const dotStyle = opts.dotColor ? `style="color: ${opts.dotColor}"` : '';

    return `<div class="result-row">
        <span class="result-row__rank" ${dotStyle}>${rank}</span>
        <div class="result-row__body">
            <a href="${esc(doc.url)}" target="_blank" rel="noopener" class="result-row__title">${esc(doc.title)}</a>
            <span class="result-row__url">${shortUrl(doc.url)}${badge}</span>
            ${doc.snippet ? `<p class="result-row__snippet">${esc(doc.snippet)}</p>` : ''}
        </div>
        <span class="result-row__score">${score}</span>
    </div>`;
}


// ── Model Pill Selection ─────────────────────────────────────

modelPills.addEventListener('click', (e) => {
    const pill = e.target.closest('.pill');
    if (!pill) return;
    modelPills.querySelectorAll('.pill').forEach(p => p.classList.remove('pill--active'));
    pill.classList.add('pill--active');
    currentModel = pill.dataset.model;

    // If we already have results, re-fire search
    if (lastData) {
        executeSearch(queryInput.value.trim(), currentModel);
    }
});


// ── Collapsible Stratum Frames ──────────────────────────────

document.querySelectorAll('.stratum__header[data-toggle]').forEach(header => {
    header.addEventListener('click', () => {
        const stratum = header.closest('.stratum');
        const toggle = header.querySelector('.stratum__toggle');
        stratum.classList.toggle('stratum--collapsed');
        toggle.innerHTML = stratum.classList.contains('stratum--collapsed') ? '+' : '&minus;';
    });
});


// ── Relevance Sub-tabs (instant model switching inside Frame 1) ──

relevanceSubtabs.addEventListener('click', async (e) => {
    const tab = e.target.closest('.subtab');
    if (!tab) return;

    const model = tab.dataset.subtab;
    relevanceSubtabs.querySelectorAll('.subtab').forEach(t => t.classList.remove('subtab--active'));
    tab.classList.add('subtab--active');

    // If we have cached data for this model, render instantly
    if (allModelResults[model]) {
        renderRelevanceList(allModelResults[model]);
        return;
    }

    // Otherwise fetch the model results
    relevanceResults.innerHTML = spinnerHtml();
    try {
        const res = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: queryInput.value.trim(), model }),
        });
        const data = await res.json();
        allModelResults[model] = data.relevance;
        renderRelevanceList(data.relevance);
    } catch (err) {
        relevanceResults.innerHTML = `<div class="stratum__error">${esc(err.message)}</div>`;
    }
});


// ── Render Functions ─────────────────────────────────────────

function renderRelevanceList(data) {
    if (data.error) {
        relevanceResults.innerHTML = `<div class="stratum__error">${esc(data.error)}</div>`;
        return;
    }
    const docs = data.documents || [];
    if (docs.length === 0) {
        relevanceResults.innerHTML = '<div class="stratum__placeholder">No results</div>';
        return;
    }
    relevanceResults.innerHTML = docs.map(d => renderResultRow(d)).join('');
    relevanceResults.classList.remove('stratum__results--fade');
    void relevanceResults.offsetWidth; // force reflow
    relevanceResults.classList.add('stratum__results--fade');
}

function renderClusters(clusters) {
    if (!Array.isArray(clusters) || clusters.length === 0) {
        clusterLegend.innerHTML = '';
        clustersResults.innerHTML = '<div class="stratum__placeholder">No clusters available</div>';
        return;
    }

    // Legend
    let legendHtml = '';
    clusters.forEach((c, i) => {
        const color = CLUSTER_COLORS[i % CLUSTER_COLORS.length];
        const count = (c.documents || []).length;
        legendHtml += `<span class="cluster-legend__item">
            <span class="cluster-legend__dot" style="background:${color}"></span>
            ${esc(c.cluster_label)} (${count})
        </span>`;
    });
    clusterLegend.innerHTML = legendHtml;

    // Grouped results
    let html = '';
    clusters.forEach((c, i) => {
        const color = CLUSTER_COLORS[i % CLUSTER_COLORS.length];
        const docs = c.documents || [];
        html += `<div class="cluster-section">
            <div class="cluster-section__header" onclick="this.parentElement.classList.toggle('cluster-section--collapsed')">
                <span class="cluster-section__dot" style="background:${color}"></span>
                ${esc(c.cluster_label)}
                <span class="cluster-section__count">(${docs.length})</span>
            </div>
            <div class="cluster-section__body">
                ${docs.map(d => renderResultRow(d, { dotColor: color })).join('')}
            </div>
        </div>`;
    });
    clustersResults.innerHTML = html;
}

function renderExpansion(data) {
    if (data.error) {
        expansionBanner.innerHTML = '';
        expansionResults.innerHTML = `<div class="stratum__error">${esc(data.error)}</div>`;
        return;
    }

    // Build expansion banner with chips for new terms
    const origTerms = new Set((data.original_query || '').toLowerCase().split(/\s+/));
    const expandedTerms = (data.expanded_query || '').split(/\s+/);

    let expandedHtml = '';
    expandedTerms.forEach(t => {
        if (origTerms.has(t.toLowerCase())) {
            expandedHtml += `${esc(t)} `;
        } else {
            expandedHtml += `<span class="expansion-chip">${esc(t)}</span> `;
        }
    });

    expansionBanner.innerHTML = `
        <div class="expansion-banner__row">
            <span class="expansion-banner__label">ORIGINAL</span>
            <span class="expansion-banner__text">${esc(data.original_query)}</span>
        </div>
        <div class="expansion-banner__arrow">&darr;</div>
        <div class="expansion-banner__row">
            <span class="expansion-banner__label">EXPANDED</span>
            <span class="expansion-banner__text">${expandedHtml.trim()}</span>
        </div>`;

    const docs = data.documents || [];
    if (docs.length === 0) {
        expansionResults.innerHTML = '<div class="stratum__placeholder">No expanded results</div>';
    } else {
        expansionResults.innerHTML = docs.map(d => renderResultRow(d)).join('');
    }
}

function renderExternal(engine, data, body, teaser) {
    teaser.textContent = `search externally \u2193`;

    body.innerHTML = `<div class="external-panel">
        <a href="${esc(data.search_url)}" target="_blank" rel="noopener" class="external-panel__link">
            Open ${engine} search &rarr;
        </a>
        <span class="external-panel__hint">Opens in a new tab for side-by-side comparison</span>
    </div>`;
}


// ── Stagger-reveal strata frames ─────────────────────────────

function revealStrata() {
    strata.classList.remove('strata--hidden');
    const frames = strata.querySelectorAll('.stratum');
    frames.forEach((frame, i) => {
        frame.classList.remove('stratum--visible');
        setTimeout(() => {
            frame.classList.add('stratum--visible');
        }, 80 * i);
    });
}


// ── Main Search Orchestration ────────────────────────────────

async function executeSearch(query, model) {
    // Pulse input
    queryInput.classList.remove('hero__input--pulse');
    void queryInput.offsetWidth;
    queryInput.classList.add('hero__input--pulse');

    // Compress hero
    heroZone.classList.add('hero--compact');

    // Show loading in all frames
    strata.classList.remove('strata--hidden');
    metaBar.classList.add('meta-bar--hidden');

    [relevanceResults, clustersResults, expansionResults, googleBody, bingBody].forEach(el => {
        el.innerHTML = spinnerHtml();
    });
    clusterLegend.innerHTML = '';
    expansionBanner.innerHTML = '';

    revealStrata();

    const startTime = performance.now();

    try {
        const res = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, model }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ error: 'Network error' }));
            throw new Error(err.error || `HTTP ${res.status}`);
        }

        const data = await res.json();
        lastData = data;
        const elapsed = performance.now() - startTime;

        // Cache model results for subtab switching
        allModelResults = {};
        allModelResults[model] = data.relevance;

        // Set active subtab to match current model
        relevanceSubtabs.querySelectorAll('.subtab').forEach(t => {
            t.classList.toggle('subtab--active', t.dataset.subtab === model);
        });

        // Meta bar
        const count = (data.relevance?.documents || []).length;
        metaContent.textContent = `${(elapsed / 1000).toFixed(2)}s \u00b7 ${count} results \u00b7 ${model.toUpperCase()}`;
        metaBar.classList.remove('meta-bar--hidden');

        // Render all panels
        renderRelevanceList(data.relevance);
        renderClusters(data.clusters);
        renderExpansion(data.expansion);
        renderExternal('Google', data.google, googleBody, googleTeaser);
        renderExternal('Bing', data.bing, bingBody, bingTeaser);

    } catch (err) {
        const errHtml = `<div class="stratum__error">${esc(err.message)}</div>`;
        [relevanceResults, clustersResults, expansionResults, googleBody, bingBody].forEach(el => {
            el.innerHTML = errHtml;
        });
    }
}


// ── Event Listeners ──────────────────────────────────────────

searchForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query) return;
    executeSearch(query, currentModel);
});

// Focus input on load
queryInput.focus();
