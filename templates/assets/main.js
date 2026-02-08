/**
 * 保健食品產品情報系統 — 主要互動邏輯
 */

(function() {
    'use strict';

    // =========================================
    // Utility Functions
    // =========================================

    /**
     * Format number with thousands separator
     */
    function formatNumber(num) {
        if (num === null || num === undefined) return '-';
        return num.toLocaleString('zh-TW');
    }

    /**
     * Format percentage
     */
    function formatPercent(num, decimals = 1) {
        if (num === null || num === undefined) return '-';
        return num.toFixed(decimals) + '%';
    }

    /**
     * Calculate percentage change
     */
    function calcChange(oldVal, newVal) {
        if (!oldVal || oldVal === 0) return null;
        return ((newVal - oldVal) / oldVal) * 100;
    }

    /**
     * Get trend indicator HTML
     */
    function getTrendIndicator(change) {
        if (change === null || change === undefined) {
            return '<span class="trend-indicator neutral">-</span>';
        }
        if (change > 0) {
            return `<span class="trend-indicator up"><span class="trend-arrow">↑</span> +${formatPercent(change)}</span>`;
        } else if (change < 0) {
            return `<span class="trend-indicator down"><span class="trend-arrow">↓</span> ${formatPercent(change)}</span>`;
        }
        return '<span class="trend-indicator neutral">→ 0%</span>';
    }

    // =========================================
    // Table Enhancement
    // =========================================

    /**
     * Enhance tables with sorting and filtering
     */
    function enhanceTables() {
        const tables = document.querySelectorAll('.data-table, .md-content table');

        tables.forEach(table => {
            // Add data-table class if not present
            if (!table.classList.contains('data-table')) {
                table.classList.add('data-table');
            }

            // Make numeric cells right-aligned
            const cells = table.querySelectorAll('td');
            cells.forEach(cell => {
                const text = cell.textContent.trim();
                // Check if content is numeric (including formatted numbers)
                if (/^[\d,\.]+%?$/.test(text.replace(/,/g, ''))) {
                    cell.classList.add('number');
                }
            });

            // Add sortable headers
            const headers = table.querySelectorAll('th');
            headers.forEach((th, index) => {
                th.style.cursor = 'pointer';
                th.addEventListener('click', () => sortTable(table, index));
            });
        });
    }

    /**
     * Sort table by column
     */
    function sortTable(table, columnIndex) {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        const rows = Array.from(tbody.querySelectorAll('tr'));
        const th = table.querySelectorAll('th')[columnIndex];

        // Determine sort direction
        const currentDir = th.dataset.sortDir || 'none';
        const newDir = currentDir === 'asc' ? 'desc' : 'asc';

        // Reset other headers
        table.querySelectorAll('th').forEach(header => {
            header.dataset.sortDir = 'none';
            header.textContent = header.textContent.replace(/ [↑↓]$/, '');
        });

        // Set new direction
        th.dataset.sortDir = newDir;
        th.textContent += newDir === 'asc' ? ' ↑' : ' ↓';

        // Sort rows
        rows.sort((a, b) => {
            const aCell = a.querySelectorAll('td')[columnIndex];
            const bCell = b.querySelectorAll('td')[columnIndex];

            if (!aCell || !bCell) return 0;

            let aVal = aCell.textContent.trim();
            let bVal = bCell.textContent.trim();

            // Try numeric comparison
            const aNum = parseFloat(aVal.replace(/[,%]/g, ''));
            const bNum = parseFloat(bVal.replace(/[,%]/g, ''));

            if (!isNaN(aNum) && !isNaN(bNum)) {
                return newDir === 'asc' ? aNum - bNum : bNum - aNum;
            }

            // String comparison
            return newDir === 'asc'
                ? aVal.localeCompare(bVal, 'zh-TW')
                : bVal.localeCompare(aVal, 'zh-TW');
        });

        // Re-append sorted rows
        rows.forEach(row => tbody.appendChild(row));
    }

    // =========================================
    // Compare Selection (Index Page)
    // =========================================

    /**
     * Initialize compare selection functionality
     */
    window.initializeCompareSelection = function(rootPath) {
        const checkboxes = document.querySelectorAll('.compare-checkbox');
        const compareBar = document.getElementById('compare-bar');
        const compareCount = document.getElementById('compare-count');
        const compareBtn = document.getElementById('compare-btn');
        const compareClear = document.getElementById('compare-clear');

        if (!checkboxes.length || !compareBar) return;

        let selected = [];

        function updateUI() {
            const count = selected.length;
            compareCount.textContent = `已選擇 ${count} 份報告`;

            if (count >= 2) {
                compareBar.classList.remove('hidden');
                compareBtn.disabled = false;
            } else if (count === 1) {
                compareBar.classList.remove('hidden');
                compareBtn.disabled = true;
            } else {
                compareBar.classList.add('hidden');
            }

            // Warn if different modes
            if (count === 2) {
                const modes = [...new Set(selected.map(s => s.mode))];
                if (modes.length > 1) {
                    compareCount.textContent += ' (不同類型，可能無法比較)';
                }
            }
        }

        checkboxes.forEach(cb => {
            cb.addEventListener('change', function() {
                const path = this.dataset.path;
                const mode = this.dataset.mode;
                const title = this.dataset.title;

                if (this.checked) {
                    if (selected.length >= 2) {
                        // Remove oldest selection
                        const oldest = selected.shift();
                        const oldCb = document.querySelector(`.compare-checkbox[data-path="${oldest.path}"]`);
                        if (oldCb) oldCb.checked = false;
                    }
                    selected.push({ path, mode, title });
                } else {
                    selected = selected.filter(s => s.path !== path);
                }

                updateUI();
            });
        });

        if (compareBtn) {
            compareBtn.addEventListener('click', function() {
                if (selected.length === 2) {
                    const url = `${rootPath}/compare.html?left=${encodeURIComponent(selected[0].path)}&right=${encodeURIComponent(selected[1].path)}`;
                    window.location.href = url;
                }
            });
        }

        if (compareClear) {
            compareClear.addEventListener('click', function() {
                selected = [];
                checkboxes.forEach(cb => cb.checked = false);
                updateUI();
            });
        }
    };

    // =========================================
    // Highlight Boxes Enhancement
    // =========================================

    /**
     * Convert blockquotes with special prefixes to highlight boxes
     */
    function enhanceBlockquotes() {
        const blockquotes = document.querySelectorAll('.md-content blockquote');

        blockquotes.forEach(bq => {
            const text = bq.textContent.trim();

            // Check for special prefixes
            const patterns = [
                { prefix: /^(注意|警告|Warning)/i, class: 'warning' },
                { prefix: /^(錯誤|Error|危險|Danger)/i, class: 'danger' },
                { prefix: /^(提示|Tip|Info|資訊)/i, class: 'info' },
                { prefix: /^(成功|Success|OK)/i, class: 'success' }
            ];

            for (const pattern of patterns) {
                if (pattern.prefix.test(text)) {
                    bq.classList.add('highlight-box', pattern.class);
                    break;
                }
            }
        });
    }

    // =========================================
    // Market Badge Enhancement
    // =========================================

    /**
     * Auto-detect and style market references
     */
    function enhanceMarketReferences() {
        const content = document.querySelector('.md-content');
        if (!content) return;

        // Market patterns
        const markets = {
            '🇺🇸': 'us',
            '🇨🇦': 'ca',
            '🇰🇷': 'kr',
            '🇯🇵': 'jp',
            '🇹🇼': 'tw',
            'US': 'us',
            'CA': 'ca',
            'KR': 'kr',
            'JP': 'jp',
            'TW': 'tw'
        };

        // This is a simple enhancement - full implementation would use TreeWalker
        // For now, just ensure flag emojis have proper spacing
    }

    // =========================================
    // Initialization
    // =========================================

    document.addEventListener('DOMContentLoaded', function() {
        // Enhance tables
        enhanceTables();

        // Enhance blockquotes
        enhanceBlockquotes();

        // Enhance market references
        enhanceMarketReferences();

        // Initialize charts if function exists
        if (typeof initializeCharts === 'function') {
            initializeCharts();
        }
    });

    // Export utilities to window
    window.ReportUtils = {
        formatNumber,
        formatPercent,
        calcChange,
        getTrendIndicator
    };

})();
