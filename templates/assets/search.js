/**
 * 保健食品產品情報系統 — Fuse.js 搜尋模組
 */

(function() {
    'use strict';

    let fuse = null;
    let searchIndex = [];
    let rootPath = '';

    // =========================================
    // Initialize Search
    // =========================================

    /**
     * Initialize search functionality
     * @param {string} indexUrl - URL to search-index.json
     * @param {string} root - Root path for generating URLs
     */
    window.initializeSearch = async function(indexUrl, root = '') {
        rootPath = root;

        const searchInput = document.getElementById('search-input');
        const searchClear = document.getElementById('search-clear');
        const searchResults = document.getElementById('search-results');

        if (!searchInput || !searchResults) {
            return;
        }

        try {
            // Load search index
            const response = await fetch(indexUrl);
            if (!response.ok) {
                console.warn('Search index not found');
                return;
            }
            searchIndex = await response.json();

            // Initialize Fuse.js
            const fuseOptions = {
                keys: [
                    { name: 'title', weight: 0.4 },
                    { name: 'highlights', weight: 0.3 },
                    { name: 'content', weight: 0.2 },
                    { name: 'mode', weight: 0.1 }
                ],
                threshold: 0.3,
                ignoreLocation: true,
                includeMatches: true,
                minMatchCharLength: 2
            };

            fuse = new Fuse(searchIndex, fuseOptions);

            // Event listeners
            searchInput.addEventListener('input', debounce(handleSearchInput, 200));
            searchInput.addEventListener('focus', () => {
                if (searchInput.value.length >= 2) {
                    showResults();
                }
            });
            searchInput.addEventListener('keydown', handleKeyNavigation);

            if (searchClear) {
                searchClear.addEventListener('click', clearSearch);
            }

            // Close results when clicking outside
            document.addEventListener('click', (e) => {
                if (!e.target.closest('.search-container')) {
                    hideResults();
                }
            });

        } catch (error) {
            console.error('Failed to initialize search:', error);
        }
    };

    // =========================================
    // Search Handlers
    // =========================================

    /**
     * Handle search input
     */
    function handleSearchInput(e) {
        const query = e.target.value.trim();
        const searchClear = document.getElementById('search-clear');

        if (searchClear) {
            searchClear.classList.toggle('visible', query.length > 0);
        }

        if (query.length < 2) {
            hideResults();
            return;
        }

        performSearch(query);
    }

    /**
     * Perform search
     */
    function performSearch(query) {
        if (!fuse) return;

        const results = fuse.search(query, { limit: 10 });
        renderResults(results, query);
    }

    /**
     * Render search results
     */
    function renderResults(results, query) {
        const searchResults = document.getElementById('search-results');
        if (!searchResults) return;

        if (results.length === 0) {
            searchResults.innerHTML = `
                <div class="search-no-results">
                    找不到「${escapeHtml(query)}」相關的報告
                </div>
            `;
            showResults();
            return;
        }

        let html = '';
        results.forEach((result, index) => {
            const item = result.item;
            const excerpt = getHighlightedExcerpt(result, query);

            html += `
                <div class="search-result-item"
                     data-index="${index}"
                     data-url="${rootPath}/${item.id}.html">
                    <div class="search-result-title">
                        ${getModeIcon(item.mode)} ${escapeHtml(item.title)}
                    </div>
                    <div class="search-result-excerpt">${excerpt}</div>
                </div>
            `;
        });

        searchResults.innerHTML = html;

        // Add click handlers
        searchResults.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', () => {
                window.location.href = item.dataset.url;
            });
        });

        showResults();
    }

    /**
     * Get highlighted excerpt from search result
     */
    function getHighlightedExcerpt(result, query) {
        const item = result.item;

        // Try to find the best match context
        if (result.matches && result.matches.length > 0) {
            // Find match in content for context
            const contentMatch = result.matches.find(m => m.key === 'content');
            if (contentMatch && contentMatch.indices.length > 0) {
                const content = item.content;
                const firstMatch = contentMatch.indices[0];
                const start = Math.max(0, firstMatch[0] - 30);
                const end = Math.min(content.length, firstMatch[1] + 50);

                let excerpt = content.substring(start, end);
                if (start > 0) excerpt = '...' + excerpt;
                if (end < content.length) excerpt = excerpt + '...';

                // Highlight matches
                const queryWords = query.toLowerCase().split(/\s+/);
                queryWords.forEach(word => {
                    const regex = new RegExp(`(${escapeRegExp(word)})`, 'gi');
                    excerpt = excerpt.replace(regex, '<mark>$1</mark>');
                });

                return excerpt;
            }

            // Try highlights
            const highlightMatch = result.matches.find(m => m.key === 'highlights');
            if (highlightMatch && item.highlights && item.highlights.length > 0) {
                return item.highlights.slice(0, 2).join(' | ');
            }
        }

        // Fallback to first part of content
        if (item.content) {
            return item.content.substring(0, 100) + '...';
        }

        return '';
    }

    /**
     * Handle keyboard navigation
     */
    function handleKeyNavigation(e) {
        const searchResults = document.getElementById('search-results');
        if (!searchResults || !searchResults.classList.contains('visible')) return;

        const items = searchResults.querySelectorAll('.search-result-item');
        const selected = searchResults.querySelector('.search-result-item.selected');
        let currentIndex = selected ? parseInt(selected.dataset.index) : -1;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                currentIndex = Math.min(currentIndex + 1, items.length - 1);
                updateSelection(items, currentIndex);
                break;

            case 'ArrowUp':
                e.preventDefault();
                currentIndex = Math.max(currentIndex - 1, 0);
                updateSelection(items, currentIndex);
                break;

            case 'Enter':
                e.preventDefault();
                if (selected) {
                    window.location.href = selected.dataset.url;
                }
                break;

            case 'Escape':
                hideResults();
                break;
        }
    }

    /**
     * Update selection highlight
     */
    function updateSelection(items, index) {
        items.forEach((item, i) => {
            item.classList.toggle('selected', i === index);
        });

        // Scroll into view if needed
        const selected = items[index];
        if (selected) {
            selected.scrollIntoView({ block: 'nearest' });
        }
    }

    /**
     * Clear search
     */
    function clearSearch() {
        const searchInput = document.getElementById('search-input');
        const searchClear = document.getElementById('search-clear');

        if (searchInput) {
            searchInput.value = '';
            searchInput.focus();
        }

        if (searchClear) {
            searchClear.classList.remove('visible');
        }

        hideResults();
    }

    /**
     * Show results dropdown
     */
    function showResults() {
        const searchResults = document.getElementById('search-results');
        if (searchResults) {
            searchResults.classList.add('visible');
        }
    }

    /**
     * Hide results dropdown
     */
    function hideResults() {
        const searchResults = document.getElementById('search-results');
        if (searchResults) {
            searchResults.classList.remove('visible');
        }
    }

    // =========================================
    // Utility Functions
    // =========================================

    /**
     * Debounce function
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Escape HTML
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Escape regex special characters
     */
    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /**
     * Get mode icon
     */
    function getModeIcon(mode) {
        const icons = {
            'market_snapshot': '📊',
            'ingredient_radar': '🧪',
            'trend_analysis': '📈',
            'competitive_intel': '🏢'
        };
        return icons[mode] || '📄';
    }

    // =========================================
    // Export
    // =========================================

    window.Search = {
        performSearch,
        clearSearch
    };

})();
