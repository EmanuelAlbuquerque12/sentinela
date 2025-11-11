/**
 * Sentinela - Frontend Application
 * Modern JavaScript for search interface
 */

// ==========================================
// Configuration
// ==========================================

const API_BASE_URL = window.location.origin;
const API_VERSION = '/api/v1';

// ==========================================
// State Management
// ==========================================

let currentPage = 0;
let currentQuery = '';
let currentFilters = {};
let totalResults = 0;
let allResults = [];

// ==========================================
// Initialize App
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    // Load theme from localStorage
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    // Setup event listeners
    setupEventListeners();

    // Load sources on page load
    loadSources();

    // Check API health
    checkAPIHealth();

    // Set default date (last 30 days)
    const today = new Date();
    const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate());
    document.getElementById('data-fim').valueAsDate = today;
    // Uncomment to set default start date
    // document.getElementById('data-inicio').valueAsDate = lastMonth;
}

// ==========================================
// Event Listeners
// ==========================================

function setupEventListeners() {
    // Search form
    document.getElementById('search-form').addEventListener('submit', handleSearch);

    // Enter key on search input
    document.getElementById('query-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleSearch(e);
        }
    });
}

// ==========================================
// Navigation
// ==========================================

function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });

    // Show selected section
    document.getElementById(`${sectionName}-section`).classList.add('active');

    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.closest('.nav-btn')?.classList.add('active');

    // Load sources if sources section
    if (sectionName === 'sources') {
        loadSources();
    }
}

// ==========================================
// Theme Toggle
// ==========================================

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// ==========================================
// Filters
// ==========================================

function toggleFilters() {
    const filters = document.getElementById('advanced-filters');
    const icon = document.getElementById('filters-icon');

    filters.classList.toggle('open');
    icon.textContent = filters.classList.contains('open') ? '▲' : '▼';
}

function clearFilters() {
    document.getElementById('data-inicio').value = '';
    document.getElementById('data-fim').value = '';
    document.getElementById('ufs').selectedIndex = 0;
    document.getElementById('sort-by').selectedIndex = 0;
    document.getElementById('page-size').selectedIndex = 0;

    // Reset checkboxes
    document.querySelectorAll('input[name="fonte"]').forEach(checkbox => {
        checkbox.checked = checkbox.value !== 'dou'; // Check all except DOU
    });
}

function getFiltersFromForm() {
    const filters = {};

    // Query
    filters.query = document.getElementById('query-input').value.trim();

    // Dates
    const dataInicio = document.getElementById('data-inicio').value;
    const dataFim = document.getElementById('data-fim').value;
    if (dataInicio) filters.data_inicio = dataInicio;
    if (dataFim) filters.data_fim = dataFim;

    // UFs (multiple select)
    const ufsSelect = document.getElementById('ufs');
    const selectedUFs = Array.from(ufsSelect.selectedOptions)
        .map(opt => opt.value)
        .filter(val => val !== '');
    if (selectedUFs.length > 0) {
        filters.ufs = selectedUFs.join(',');
    }

    // Sources (checkboxes)
    const selectedSources = Array.from(document.querySelectorAll('input[name="fonte"]:checked'))
        .map(cb => cb.value);
    if (selectedSources.length > 0 && selectedSources.length < 4) {
        filters.fontes = selectedSources.join(',');
    }

    // Sort
    filters.sort_by = document.getElementById('sort-by').value;

    // Page size
    filters.size = parseInt(document.getElementById('page-size').value);

    // Offset (pagination)
    filters.offset = currentPage * filters.size;

    return filters;
}

// ==========================================
// Search
// ==========================================

async function handleSearch(event) {
    event.preventDefault();

    const filters = getFiltersFromForm();

    if (!filters.query) {
        showError('Por favor, digite um termo de busca');
        return;
    }

    // Reset pagination
    currentPage = 0;
    filters.offset = 0;

    // Store current query and filters
    currentQuery = filters.query;
    currentFilters = filters;

    // Perform search
    await performSearch(filters);
}

async function performSearch(filters) {
    // Show loading
    showLoading(true);
    hideResults();

    try {
        // Build query string
        const queryString = new URLSearchParams(filters).toString();
        const url = `${API_BASE_URL}${API_VERSION}/search?${queryString}`;

        // Fetch results
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // Store results
        allResults = data.resultados || [];
        totalResults = data.total_resultados || 0;

        // Display results
        displaySearchStats(data);
        displayResults(data.resultados || []);
        displayPagination(data.paginacao || {});

        // Show errors if any
        if (data.erros && data.erros.length > 0) {
            showWarning(`Algumas fontes falharam: ${data.erros.map(e => e.fonte).join(', ')}`);
        }

    } catch (error) {
        console.error('Search error:', error);
        showError(`Erro ao buscar: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

// ==========================================
// Display Results
// ==========================================

function displaySearchStats(data) {
    const statsDiv = document.getElementById('search-stats');

    const html = `
        <div>
            <span class="stat-label">Resultados:</span>
            <span class="stat-value">${data.total_resultados || 0}</span>
        </div>
        <div>
            <span class="stat-label">Fontes consultadas:</span>
            <span class="stat-value">${data.fontes_consultadas || 0}</span>
        </div>
        <div>
            <span class="stat-label">Fontes com sucesso:</span>
            <span class="stat-value">${data.fontes_sucesso || 0}</span>
        </div>
        <div>
            <span class="stat-label">Tempo:</span>
            <span class="stat-value">${data.tempo_consulta_ms || 0}ms</span>
        </div>
    `;

    statsDiv.innerHTML = html;
    statsDiv.style.display = 'flex';
}

function displayResults(results) {
    const container = document.getElementById('results-container');

    if (results.length === 0) {
        container.innerHTML = `
            <div class="no-results">
                <h3>😔 Nenhum resultado encontrado</h3>
                <p>Tente ajustar os filtros ou usar termos diferentes</p>
            </div>
        `;
        container.style.display = 'block';
        return;
    }

    const html = results.map(result => createResultCard(result)).join('');
    container.innerHTML = html;
    container.style.display = 'grid';

    // Highlight search terms
    highlightSearchTerms(currentQuery);
}

function createResultCard(result) {
    const relevancePercent = Math.round(result.relevancia * 100);
    const relevanceClass = relevancePercent >= 70 ? 'success' : relevancePercent >= 40 ? 'warning' : 'error';

    return `
        <article class="result-card">
            <div class="result-header">
                <div>
                    <h3 class="result-title">
                        <a href="${result.url_original}" target="_blank" rel="noopener">
                            ${escapeHtml(result.titulo)}
                        </a>
                    </h3>
                    <div class="result-meta">
                        <span class="meta-item">
                            📅 ${formatDate(result.data_publicacao)}
                        </span>
                        <span class="meta-item">
                            📍 ${escapeHtml(result.orgao)}
                        </span>
                        ${result.orgao_uf ? `
                        <span class="meta-item">
                            🗺️ ${escapeHtml(result.orgao_uf)}
                        </span>
                        ` : ''}
                    </div>
                </div>
            </div>

            <div class="result-snippet">
                ${escapeHtml(result.snippet)}
            </div>

            <div class="result-footer">
                <div class="result-tags">
                    <span class="tag source">${escapeHtml(result.fonte)}</span>
                    <span class="tag">${getSourceTypeLabel(result.fonte_tipo)}</span>
                </div>
                <span class="relevance-badge" style="background: var(--${relevanceClass}-color)">
                    ${relevancePercent}% relevante
                </span>
            </div>
        </article>
    `;
}

function getSourceTypeLabel(type) {
    const labels = {
        'municipal': '🏛️ Municipal',
        'estadual': '🏢 Estadual',
        'federal': '🏛️ Federal',
        'judicial': '⚖️ Judicial',
        'tcu': '📊 TCU'
    };
    return labels[type] || type;
}

function highlightSearchTerms(query) {
    if (!query) return;

    const terms = query.toLowerCase().split(' ').filter(t => t.length > 2);
    const snippets = document.querySelectorAll('.result-snippet');

    snippets.forEach(snippet => {
        let text = snippet.textContent;
        terms.forEach(term => {
            const regex = new RegExp(`(${escapeRegex(term)})`, 'gi');
            text = text.replace(regex, '<mark>$1</mark>');
        });
        snippet.innerHTML = text;
    });
}

// ==========================================
// Pagination
// ==========================================

function displayPagination(paginacao) {
    const container = document.getElementById('pagination');

    if (!paginacao || paginacao.total <= paginacao.size) {
        container.style.display = 'none';
        return;
    }

    const totalPages = Math.ceil(paginacao.total / paginacao.size);
    const currentPageNum = Math.floor(paginacao.offset / paginacao.size);

    let html = `
        <button class="page-btn" onclick="goToPage(0)" ${currentPageNum === 0 ? 'disabled' : ''}>
            « Primeira
        </button>
        <button class="page-btn" onclick="goToPage(${currentPageNum - 1})" ${!paginacao.has_prev ? 'disabled' : ''}>
            ‹ Anterior
        </button>
    `;

    // Page numbers (show max 5)
    const startPage = Math.max(0, currentPageNum - 2);
    const endPage = Math.min(totalPages, startPage + 5);

    for (let i = startPage; i < endPage; i++) {
        html += `
            <button class="page-btn ${i === currentPageNum ? 'active' : ''}" onclick="goToPage(${i})">
                ${i + 1}
            </button>
        `;
    }

    html += `
        <button class="page-btn" onclick="goToPage(${currentPageNum + 1})" ${!paginacao.has_next ? 'disabled' : ''}>
            Próxima ›
        </button>
        <button class="page-btn" onclick="goToPage(${totalPages - 1})" ${currentPageNum === totalPages - 1 ? 'disabled' : ''}>
            Última »
        </button>
    `;

    container.innerHTML = html;
    container.style.display = 'flex';
}

function goToPage(page) {
    currentPage = page;
    currentFilters.offset = currentPage * currentFilters.size;
    performSearch(currentFilters);

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==========================================
// Sources
// ==========================================

async function loadSources() {
    const container = document.getElementById('sources-list');
    container.innerHTML = '<div class="loading"><div class="spinner"></div><p>Carregando fontes...</p></div>';

    try {
        const response = await fetch(`${API_BASE_URL}${API_VERSION}/sources`);

        if (!response.ok) {
            throw new Error('Erro ao carregar fontes');
        }

        const data = await response.json();
        displaySources(data.fontes || []);

    } catch (error) {
        console.error('Error loading sources:', error);
        container.innerHTML = `
            <div class="error">
                <p>❌ Erro ao carregar fontes: ${error.message}</p>
            </div>
        `;
    }
}

function displaySources(sources) {
    const container = document.getElementById('sources-list');

    if (sources.length === 0) {
        container.innerHTML = '<p>Nenhuma fonte disponível</p>';
        return;
    }

    const html = sources.map(source => createSourceCard(source)).join('');
    container.innerHTML = html;
}

function createSourceCard(source) {
    const statusClass = source.status === 'online' ? 'online' : 'offline';

    return `
        <div class="source-card">
            <div class="source-header">
                <h3 class="source-name">${escapeHtml(source.nome)}</h3>
                <span class="status-badge ${statusClass}">
                    ${source.status === 'online' ? '🟢 Online' : '🔴 Offline'}
                </span>
            </div>

            <p class="source-description">${escapeHtml(source.descricao)}</p>

            <div class="source-details">
                <div class="detail-item">
                    <strong>Tipo:</strong> ${getSourceTypeLabel(source.tipo)}
                </div>
                <div class="detail-item">
                    <strong>Cobertura:</strong> ${escapeHtml(source.cobertura)}
                </div>
                <div class="detail-item">
                    <strong>Autenticação:</strong> ${source.requer_autenticacao ? '🔑 Sim (API Key)' : '✅ Não requerida'}
                </div>
            </div>

            ${source.limitacoes && source.limitacoes.length > 0 ? `
            <div class="source-limitations">
                <h4>⚠️ Limitações</h4>
                <ul>
                    ${source.limitacoes.map(lim => `<li>${escapeHtml(lim)}</li>`).join('')}
                </ul>
            </div>
            ` : ''}
        </div>
    `;
}

// ==========================================
// API Health Check
// ==========================================

async function checkAPIHealth() {
    const statusElement = document.getElementById('api-status');

    try {
        const response = await fetch(`${API_BASE_URL}${API_VERSION}/health`);
        const data = await response.json();

        const statusMap = {
            'healthy': { emoji: '🟢', text: 'Saudável', class: 'online' },
            'degraded': { emoji: '🟡', text: 'Degradado', class: 'warning' },
            'unhealthy': { emoji: '🔴', text: 'Indisponível', class: 'offline' }
        };

        const status = statusMap[data.status] || statusMap.unhealthy;

        statusElement.innerHTML = `
            Status: <span class="status-badge ${status.class}">${status.emoji} ${status.text}</span>
        `;

    } catch (error) {
        console.error('Health check error:', error);
        statusElement.innerHTML = `
            Status: <span class="status-badge offline">🔴 Erro</span>
        `;
    }
}

// ==========================================
// UI Helpers
// ==========================================

function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
}

function hideResults() {
    document.getElementById('search-stats').style.display = 'none';
    document.getElementById('results-container').innerHTML = '';
    document.getElementById('pagination').style.display = 'none';
}

function showError(message) {
    alert(`❌ ${message}`);
}

function showWarning(message) {
    console.warn(message);
    // Could implement a toast notification here
}

// ==========================================
// Utility Functions
// ==========================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeRegex(text) {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// ==========================================
// Make functions globally accessible
// ==========================================

window.showSection = showSection;
window.toggleTheme = toggleTheme;
window.toggleFilters = toggleFilters;
window.clearFilters = clearFilters;
window.goToPage = goToPage;
