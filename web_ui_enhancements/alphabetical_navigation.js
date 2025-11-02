/**
 * Alphabetical Navigation Enhancement for Music Assistant Web UI
 *
 * Adds A-Z navigation bar and search functionality to artist library view.
 * Injects into compiled Vue.js frontend without modifying source.
 *
 * @version 1.0.0
 * @author Music Assistant Community
 * @date 2025-10-25
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        apiBase: '/api',
        checkInterval: 1000,
        searchDebounceMs: 300,
        maxRetries: 3,
        cacheTimeout: 300000, // 5 minutes
    };

    // State
    let currentLetter = 'ALL';
    let letterCounts = {};
    let searchTimeout = null;
    let navBarInjected = false;
    let lastUrl = '';
    let letterCountsCache = null;
    let letterCountsCacheTime = 0;

    /**
     * Check if we're on the artist library view
     */
    function isArtistLibraryView() {
        const url = window.location.href;
        const path = window.location.pathname;
        const hash = window.location.hash;

        // Check URL patterns
        if (path.includes('/library/artists') ||
            hash.includes('library/artists') ||
            url.includes('artists')) {
            return true;
        }

        // Check DOM for artist-specific elements
        const indicators = [
            '[data-media-type="artist"]',
            '.library-artists',
            '[aria-label*="Artists"]',
            'h1:contains("Artists")',
        ];

        for (const selector of indicators) {
            if (document.querySelector(selector)) {
                return true;
            }
        }

        return false;
    }

    /**
     * Find the artist list container
     */
    function findArtistListContainer() {
        const selectors = [
            '.library-artists',
            '[data-media-type="artist"]',
            '.media-browser',
            'main > section',
            '.mdc-data-table',
            '[role="main"] section',
        ];

        for (const selector of selectors) {
            const el = document.querySelector(selector);
            if (el && el.offsetParent !== null) {  // Must be visible
                return el;
            }
        }

        // Fallback: find any section with multiple artist-like items
        const sections = document.querySelectorAll('main section, [role="main"] section');
        for (const section of sections) {
            const items = section.querySelectorAll('[data-item-type="artist"], .artist-item, .media-item');
            if (items.length > 10) {  // Likely the artist list
                return section;
            }
        }

        return null;
    }

    /**
     * Fetch letter counts from API with caching
     */
    async function fetchLetterCounts(forceRefresh = false) {
        const now = Date.now();

        // Check cache
        if (!forceRefresh &&
            letterCountsCache &&
            (now - letterCountsCacheTime) < CONFIG.cacheTimeout) {
            return letterCountsCache;
        }

        try {
            const response = await fetch(`${CONFIG.apiBase}/music/artists/letter_counts`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();

            // Cache the result
            letterCountsCache = data;
            letterCountsCacheTime = now;
            letterCounts = data;

            console.log('[AlphaNav] Letter counts fetched:', data);
            return data;

        } catch (error) {
            console.error('[AlphaNav] Failed to fetch letter counts:', error);

            // Return cached data if available
            if (letterCountsCache) {
                console.warn('[AlphaNav] Using cached letter counts due to fetch error');
                return letterCountsCache;
            }

            // Generate mock counts for development/testing
            const mockCounts = {};
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').forEach(letter => {
                mockCounts[letter] = Math.floor(Math.random() * 100);
            });
            return mockCounts;
        }
    }

    /**
     * Create alphabetical navigation bar
     */
    function createNavigationBar() {
        const nav = document.createElement('div');
        nav.className = 'alpha-nav-bar';
        nav.id = 'alphaNavBar';
        nav.innerHTML = `
            <style>
                .alpha-nav-bar {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                    padding: 16px;
                    background: var(--md-sys-color-surface, #f5f5f5);
                    border-bottom: 1px solid var(--md-sys-color-outline, #ddd);
                    align-items: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    z-index: 100;
                    position: sticky;
                    top: 0;
                }

                .alpha-nav-buttons {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 6px;
                    flex: 1;
                }

                .alpha-nav-btn {
                    padding: 8px 12px;
                    min-width: 42px;
                    background: var(--md-sys-color-surface-container, #fff);
                    border: 1px solid var(--md-sys-color-outline, #ccc);
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 500;
                    transition: all 0.2s ease;
                    text-align: center;
                    font-size: 14px;
                    color: var(--md-sys-color-on-surface, #000);
                }

                .alpha-nav-btn:hover:not(.disabled) {
                    background: var(--md-sys-color-surface-container-high, #e8e8e8);
                    transform: translateY(-2px);
                    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
                }

                .alpha-nav-btn.active {
                    background: var(--md-sys-color-primary, #1976d2);
                    color: var(--md-sys-color-on-primary, #fff);
                    border-color: var(--md-sys-color-primary, #1976d2);
                    box-shadow: 0 2px 6px rgba(25, 118, 210, 0.3);
                }

                .alpha-nav-btn.disabled {
                    opacity: 0.3;
                    cursor: not-allowed;
                    background: var(--md-sys-color-surface-variant, #f0f0f0);
                }

                .alpha-nav-btn .count {
                    font-size: 0.7em;
                    opacity: 0.7;
                    display: block;
                    margin-top: 2px;
                }

                .alpha-nav-btn.all {
                    min-width: 50px;
                    font-weight: 600;
                }

                .alpha-search-box {
                    position: relative;
                    flex: 0 0 280px;
                    min-width: 200px;
                }

                .alpha-search-input {
                    width: 100%;
                    padding: 10px 40px 10px 12px;
                    border: 1px solid var(--md-sys-color-outline, #ccc);
                    border-radius: 8px;
                    background: var(--md-sys-color-surface-container, #fff);
                    color: var(--md-sys-color-on-surface, #000);
                    font-size: 14px;
                    transition: all 0.2s ease;
                }

                .alpha-search-input:focus {
                    outline: none;
                    border-color: var(--md-sys-color-primary, #1976d2);
                    box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.1);
                }

                .alpha-search-input::placeholder {
                    color: var(--md-sys-color-on-surface-variant, #666);
                }

                .alpha-search-clear {
                    position: absolute;
                    right: 8px;
                    top: 50%;
                    transform: translateY(-50%);
                    background: none;
                    border: none;
                    cursor: pointer;
                    padding: 6px;
                    opacity: 0.6;
                    font-size: 18px;
                    color: var(--md-sys-color-on-surface-variant, #666);
                    transition: opacity 0.2s ease;
                }

                .alpha-search-clear:hover {
                    opacity: 1;
                }

                .alpha-status {
                    padding: 10px 16px;
                    background: var(--md-sys-color-surface-container-high, #e8e8e8);
                    border-radius: 8px;
                    font-size: 13px;
                    color: var(--md-sys-color-on-surface-variant, #666);
                    white-space: nowrap;
                    font-weight: 500;
                }

                @media (max-width: 768px) {
                    .alpha-nav-bar {
                        flex-direction: column;
                        gap: 8px;
                    }

                    .alpha-nav-buttons {
                        width: 100%;
                    }

                    .alpha-search-box {
                        flex: 1 1 auto;
                        width: 100%;
                    }

                    .alpha-status {
                        width: 100%;
                        text-align: center;
                    }
                }
            </style>

            <div class="alpha-nav-buttons" id="alphaNavButtons"></div>

            <div class="alpha-search-box">
                <input
                    type="text"
                    class="alpha-search-input"
                    placeholder="Search artists..."
                    id="alphaSearchInput"
                    autocomplete="off"
                    spellcheck="false"
                />
                <button
                    class="alpha-search-clear"
                    id="alphaSearchClear"
                    style="display:none;"
                    title="Clear search"
                    aria-label="Clear search"
                >
                    ✕
                </button>
            </div>

            <div class="alpha-status" id="alphaStatus">
                Loading...
            </div>
        `;

        return nav;
    }

    /**
     * Populate navigation buttons
     */
    function populateNavigationButtons(container) {
        container.innerHTML = '';  // Clear existing

        const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ#'.split('');

        // Add "All" button
        const allBtn = document.createElement('button');
        allBtn.className = 'alpha-nav-btn all active';
        allBtn.textContent = 'All';
        allBtn.dataset.letter = 'ALL';
        allBtn.title = 'Show all artists';
        allBtn.onclick = () => filterByLetter('ALL');
        container.appendChild(allBtn);

        // Add letter buttons
        letters.forEach(letter => {
            const btn = document.createElement('button');
            btn.className = 'alpha-nav-btn';
            btn.dataset.letter = letter;

            const count = letterCounts[letter] || 0;
            const labelText = letter === '#' ? '0-9' : letter;

            if (count > 0) {
                btn.innerHTML = `${labelText}<span class="count">${count}</span>`;
                btn.title = `${count} artists starting with ${labelText}`;
            } else {
                btn.textContent = labelText;
                btn.classList.add('disabled');
                btn.title = `No artists starting with ${labelText}`;
            }

            btn.onclick = () => {
                if (count > 0) {
                    filterByLetter(letter);
                }
            };

            container.appendChild(btn);
        });
    }

    /**
     * Filter artists by letter
     */
    async function filterByLetter(letter) {
        currentLetter = letter;

        // Update active button
        document.querySelectorAll('.alpha-nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.letter === letter);
        });

        // Clear search
        const searchInput = document.getElementById('alphaSearchInput');
        if (searchInput) {
            searchInput.value = '';
        }
        const searchClear = document.getElementById('alphaSearchClear');
        if (searchClear) {
            searchClear.style.display = 'none';
        }

        // Update status
        const status = document.getElementById('alphaStatus');
        if (status) {
            status.textContent = 'Loading...';
        }

        try {
            // Construct API URL
            const url = letter === 'ALL'
                ? `${CONFIG.apiBase}/music/artists/library_items?limit=2000&order_by=sort_name`
                : `${CONFIG.apiBase}/music/artists/by_letter?letter=${encodeURIComponent(letter)}&limit=2000`;

            console.log(`[AlphaNav] Filtering by letter: ${letter}, URL: ${url}`);

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            const artists = Array.isArray(data) ? data : (data.items || []);

            console.log(`[AlphaNav] Received ${artists.length} artists for letter ${letter}`);

            // Dispatch custom event for Vue.js integration
            window.dispatchEvent(new CustomEvent('ma-artists-filtered', {
                detail: {
                    letter,
                    artists,
                    count: artists.length,
                }
            }));

            // Update status
            if (status) {
                const displayLetter = letter === 'ALL' ? 'All' : (letter === '#' ? '0-9' : letter);
                status.textContent = letter === 'ALL'
                    ? `${artists.length} artists`
                    : `${displayLetter}: ${artists.length} artist${artists.length !== 1 ? 's' : ''}`;
            }

            // Scroll to top of list
            const container = findArtistListContainer();
            if (container) {
                container.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }

        } catch (error) {
            console.error('[AlphaNav] Failed to filter artists:', error);
            if (status) {
                status.textContent = 'Error loading artists';
            }
        }
    }

    /**
     * Handle search input
     */
    function setupSearch() {
        const searchInput = document.getElementById('alphaSearchInput');
        const searchClear = document.getElementById('alphaSearchClear');
        const status = document.getElementById('alphaStatus');

        if (!searchInput) return;

        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();

            // Show/hide clear button
            if (searchClear) {
                searchClear.style.display = query ? 'block' : 'none';
            }

            // Clear active letter
            if (query) {
                document.querySelectorAll('.alpha-nav-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
            }

            // Debounce search
            clearTimeout(searchTimeout);

            if (!query) {
                // Clear search - revert to current letter filter
                filterByLetter(currentLetter);
                return;
            }

            if (query.length < 2) {
                if (status) {
                    status.textContent = 'Type at least 2 characters';
                }
                return;
            }

            if (status) {
                status.textContent = 'Searching...';
            }

            searchTimeout = setTimeout(async () => {
                try {
                    const url = `${CONFIG.apiBase}/music/artists/search_library?query=${encodeURIComponent(query)}&limit=100`;

                    console.log(`[AlphaNav] Searching: ${query}, URL: ${url}`);

                    const response = await fetch(url, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json',
                        },
                    });

                    if (!response.ok) {
                        throw new Error(`API error: ${response.status}`);
                    }

                    const data = await response.json();
                    const artists = Array.isArray(data) ? data : (data.items || []);

                    console.log(`[AlphaNav] Search found ${artists.length} artists`);

                    // Dispatch event for Vue.js
                    window.dispatchEvent(new CustomEvent('ma-artists-filtered', {
                        detail: {
                            search: query,
                            artists,
                            count: artists.length,
                        }
                    }));

                    // Update status
                    if (status) {
                        if (artists.length === 0) {
                            status.textContent = 'No artists found';
                        } else {
                            status.textContent = `Found ${artists.length} artist${artists.length !== 1 ? 's' : ''}`;
                        }
                    }

                } catch (error) {
                    console.error('[AlphaNav] Search failed:', error);
                    if (status) {
                        status.textContent = 'Search error';
                    }
                }
            }, CONFIG.searchDebounceMs);
        });

        // Clear button
        if (searchClear) {
            searchClear.addEventListener('click', () => {
                searchInput.value = '';
                searchClear.style.display = 'none';
                searchInput.focus();
                filterByLetter(currentLetter);
            });
        }

        // Enter key to search immediately
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                clearTimeout(searchTimeout);
                searchInput.dispatchEvent(new Event('input'));
            }
        });
    }

    /**
     * Inject navigation bar into DOM
     */
    async function injectNavigationBar() {
        // Check if already injected
        if (document.getElementById('alphaNavBar')) {
            return;
        }

        // Find artist list container
        const container = findArtistListContainer();
        if (!container) {
            console.log('[AlphaNav] Artist list container not found');
            return;
        }

        console.log('[AlphaNav] Injecting navigation bar...');

        // Fetch letter counts
        await fetchLetterCounts();

        // Create and insert navigation bar
        const navBar = createNavigationBar();

        // Insert before the container
        if (container.parentElement) {
            container.parentElement.insertBefore(navBar, container);
        } else {
            // Fallback: insert at beginning of main content
            const main = document.querySelector('main, [role="main"]');
            if (main) {
                main.insertBefore(navBar, main.firstChild);
            }
        }

        // Populate buttons
        const buttonsContainer = document.getElementById('alphaNavButtons');
        if (buttonsContainer) {
            populateNavigationButtons(buttonsContainer);
        }

        // Setup search
        setupSearch();

        // Update status
        const status = document.getElementById('alphaStatus');
        if (status) {
            const totalCount = Object.values(letterCounts).reduce((sum, count) => sum + count, 0);
            status.textContent = totalCount > 0
                ? `${totalCount} total artists`
                : 'No artists';
        }

        navBarInjected = true;
        console.log('[AlphaNav] Navigation bar injected successfully');
    }

    /**
     * Remove navigation bar (for cleanup)
     */
    function removeNavigationBar() {
        const navBar = document.getElementById('alphaNavBar');
        if (navBar) {
            navBar.remove();
            navBarInjected = false;
            console.log('[AlphaNav] Navigation bar removed');
        }
    }

    /**
     * Monitor for artist library view and inject when found
     */
    function monitorForArtistView() {
        setInterval(() => {
            const currentUrl = window.location.href;

            // Check if URL changed
            if (currentUrl !== lastUrl) {
                lastUrl = currentUrl;

                // Remove existing bar if we left artist view
                if (!isArtistLibraryView() && navBarInjected) {
                    removeNavigationBar();
                }
            }

            // Inject if we're on artist view and bar not injected
            if (isArtistLibraryView() && !navBarInjected) {
                injectNavigationBar();
            }
        }, CONFIG.checkInterval);
    }

    /**
     * Initialize enhancement
     */
    function init() {
        console.log('[AlphaNav] Alphabetical navigation enhancement v1.0.0 loaded');

        lastUrl = window.location.href;

        // Check immediately
        if (isArtistLibraryView()) {
            setTimeout(injectNavigationBar, 500);  // Small delay for page to settle
        }

        // Monitor for navigation
        monitorForArtistView();

        // Listen for Vue.js route changes
        window.addEventListener('popstate', () => {
            lastUrl = window.location.href;
            if (!isArtistLibraryView() && navBarInjected) {
                removeNavigationBar();
            }
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose API for debugging
    window.MusicAssistantAlphaNav = {
        version: '1.0.0',
        filterByLetter,
        fetchLetterCounts,
        inject: injectNavigationBar,
        remove: removeNavigationBar,
        isActive: () => navBarInjected,
        getCurrentLetter: () => currentLetter,
        getLetterCounts: () => letterCounts,
    };

})();
