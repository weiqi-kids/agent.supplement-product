/**
 * 保健食品產品情報系統 — 報告比較功能模組
 */

(function() {
    'use strict';

    let rootPath = '';
    let leftReport = null;
    let rightReport = null;

    // =========================================
    // Initialize Compare
    // =========================================

    /**
     * Initialize compare functionality
     * @param {string} root - Root path for loading reports
     */
    window.initializeCompare = async function(root = '') {
        rootPath = root;

        // Get DOM elements
        const selectLeft = document.getElementById('select-left');
        const selectRight = document.getElementById('select-right');
        const doCompareBtn = document.getElementById('do-compare');
        const swapBtn = document.getElementById('swap-reports');

        if (!selectLeft || !selectRight) return;

        // Check URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const leftPath = urlParams.get('left');
        const rightPath = urlParams.get('right');

        // Set initial values from URL
        if (leftPath) {
            selectLeft.value = leftPath;
        }
        if (rightPath) {
            selectRight.value = rightPath;
        }

        // Event listeners
        selectLeft.addEventListener('change', updateCompareButton);
        selectRight.addEventListener('change', updateCompareButton);

        if (doCompareBtn) {
            doCompareBtn.addEventListener('click', performCompare);
        }

        if (swapBtn) {
            swapBtn.addEventListener('click', swapReports);
        }

        // Auto-compare if both params present
        if (leftPath && rightPath) {
            await performCompare();
        }

        updateCompareButton();
    };

    /**
     * Update compare button state
     */
    function updateCompareButton() {
        const selectLeft = document.getElementById('select-left');
        const selectRight = document.getElementById('select-right');
        const doCompareBtn = document.getElementById('do-compare');

        if (!doCompareBtn) return;

        const leftVal = selectLeft?.value;
        const rightVal = selectRight?.value;

        doCompareBtn.disabled = !leftVal || !rightVal || leftVal === rightVal;

        // Warn if different types
        if (leftVal && rightVal) {
            const leftMode = selectLeft.querySelector(`option[value="${leftVal}"]`)?.dataset.mode;
            const rightMode = selectRight.querySelector(`option[value="${rightVal}"]`)?.dataset.mode;

            if (leftMode && rightMode && leftMode !== rightMode) {
                doCompareBtn.textContent = '比較 (類型不同)';
            } else {
                doCompareBtn.textContent = '開始比較';
            }
        }
    }

    /**
     * Swap left and right reports
     */
    function swapReports() {
        const selectLeft = document.getElementById('select-left');
        const selectRight = document.getElementById('select-right');

        if (!selectLeft || !selectRight) return;

        const temp = selectLeft.value;
        selectLeft.value = selectRight.value;
        selectRight.value = temp;

        updateCompareButton();
    }

    // =========================================
    // Compare Execution
    // =========================================

    /**
     * Perform the comparison
     */
    async function performCompare() {
        const selectLeft = document.getElementById('select-left');
        const selectRight = document.getElementById('select-right');
        const compareResults = document.getElementById('compare-results');
        const compareLoading = document.getElementById('compare-loading');
        const compareEmpty = document.getElementById('compare-empty');
        const compareSelector = document.getElementById('compare-selector');

        const leftPath = selectLeft?.value;
        const rightPath = selectRight?.value;

        if (!leftPath || !rightPath) return;

        // Update URL
        const newUrl = `${window.location.pathname}?left=${encodeURIComponent(leftPath)}&right=${encodeURIComponent(rightPath)}`;
        window.history.pushState({}, '', newUrl);

        // Show loading
        if (compareEmpty) compareEmpty.classList.add('hidden');
        if (compareLoading) compareLoading.classList.remove('hidden');
        if (compareResults) compareResults.classList.add('hidden');

        try {
            // Load both reports
            const [leftData, rightData] = await Promise.all([
                loadReport(leftPath),
                loadReport(rightPath)
            ]);

            leftReport = leftData;
            rightReport = rightData;

            // Generate comparison
            const comparison = generateComparison(leftData, rightData);

            // Render results
            renderComparison(leftData, rightData, comparison);

            // Hide loading, show results
            if (compareLoading) compareLoading.classList.add('hidden');
            if (compareResults) compareResults.classList.remove('hidden');

        } catch (error) {
            console.error('Compare failed:', error);
            if (compareLoading) compareLoading.classList.add('hidden');
            if (compareEmpty) {
                compareEmpty.classList.remove('hidden');
                compareEmpty.innerHTML = `
                    <p class="text-danger">載入報告失敗: ${error.message}</p>
                    <p class="text-muted">請確認報告路徑正確</p>
                `;
            }
        }
    }

    /**
     * Load report HTML content
     */
    async function loadReport(path) {
        const url = `${rootPath}/${path}.html`;

        // Check if running from file:// protocol
        if (window.location.protocol === 'file:') {
            throw new Error('比較功能需要透過 HTTP 伺服器存取。請在 docs/html 目錄執行 python3 -m http.server 8000，然後訪問 http://localhost:8000/compare.html');
        }

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`無法載入報告 ${path}（HTTP ${response.status}）`);
        }

        const html = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

        // Extract content
        const content = doc.querySelector('.md-content')?.innerHTML || '';
        const title = doc.querySelector('title')?.textContent?.replace(' - 保健食品情報系統', '') || path;
        const meta = {};

        doc.querySelectorAll('.report-meta-item').forEach(item => {
            const label = item.querySelector('.report-meta-label')?.textContent;
            const value = item.querySelector('.report-meta-value')?.textContent;
            if (label && value) {
                meta[label] = value;
            }
        });

        // Extract structured data from tables
        const tables = {};
        doc.querySelectorAll('.md-content table').forEach((table, index) => {
            const prevH3 = findPreviousHeading(table);
            const key = prevH3 || `table_${index}`;
            tables[key] = extractTableData(table);
        });

        return {
            path,
            title,
            content,
            meta,
            tables
        };
    }

    /**
     * Find previous heading for context
     */
    function findPreviousHeading(element) {
        let sibling = element.previousElementSibling;
        while (sibling) {
            if (/^H[1-6]$/.test(sibling.tagName)) {
                return sibling.textContent.trim();
            }
            sibling = sibling.previousElementSibling;
        }
        return null;
    }

    /**
     * Extract data from table
     */
    function extractTableData(table) {
        const headers = [];
        const rows = [];

        table.querySelectorAll('thead th, tr:first-child th').forEach(th => {
            headers.push(th.textContent.trim());
        });

        table.querySelectorAll('tbody tr, tr:not(:first-child)').forEach(tr => {
            const row = {};
            tr.querySelectorAll('td').forEach((td, i) => {
                row[headers[i] || `col${i}`] = td.textContent.trim();
            });
            if (Object.keys(row).length > 0) {
                rows.push(row);
            }
        });

        return { headers, rows };
    }

    // =========================================
    // Comparison Logic
    // =========================================

    /**
     * Generate comparison between two reports
     */
    function generateComparison(left, right) {
        const comparison = {
            summary: [],
            tableDiffs: {},
            numericChanges: []
        };

        // Compare tables
        const allTableKeys = new Set([
            ...Object.keys(left.tables || {}),
            ...Object.keys(right.tables || {})
        ]);

        allTableKeys.forEach(key => {
            const leftTable = left.tables?.[key];
            const rightTable = right.tables?.[key];

            if (leftTable && rightTable) {
                const diff = compareTableData(leftTable, rightTable, key);
                comparison.tableDiffs[key] = diff;

                // Add numeric changes to summary
                diff.changes.forEach(change => {
                    if (change.type === 'value_changed' && change.numericChange !== null) {
                        comparison.numericChanges.push({
                            table: key,
                            ...change
                        });
                    }
                });
            } else if (!leftTable) {
                comparison.summary.push(`新增表格：${key}`);
            } else if (!rightTable) {
                comparison.summary.push(`移除表格：${key}`);
            }
        });

        // Generate summary
        if (comparison.numericChanges.length > 0) {
            // Sort by absolute change
            const significantChanges = comparison.numericChanges
                .filter(c => Math.abs(c.numericChange) >= 5)
                .sort((a, b) => Math.abs(b.numericChange) - Math.abs(a.numericChange))
                .slice(0, 5);

            significantChanges.forEach(change => {
                const direction = change.numericChange > 0 ? '↑' : '↓';
                const pct = Math.abs(change.numericChange).toFixed(1);
                comparison.summary.push(`${change.row}: ${direction} ${pct}%`);
            });
        }

        return comparison;
    }

    /**
     * Compare two table datasets
     */
    function compareTableData(left, right, tableName) {
        const diff = {
            name: tableName,
            changes: [],
            added: [],
            removed: []
        };

        // Find common identifier column (usually first column)
        const idCol = left.headers[0];

        // Create lookup maps
        const leftMap = new Map();
        const rightMap = new Map();

        left.rows.forEach(row => {
            leftMap.set(row[idCol], row);
        });

        right.rows.forEach(row => {
            rightMap.set(row[idCol], row);
        });

        // Find added and removed
        rightMap.forEach((row, id) => {
            if (!leftMap.has(id)) {
                diff.added.push(row);
            }
        });

        leftMap.forEach((row, id) => {
            if (!rightMap.has(id)) {
                diff.removed.push(row);
            }
        });

        // Compare common rows
        leftMap.forEach((leftRow, id) => {
            const rightRow = rightMap.get(id);
            if (!rightRow) return;

            left.headers.forEach(col => {
                const leftVal = leftRow[col];
                const rightVal = rightRow[col];

                if (leftVal !== rightVal) {
                    const leftNum = parseNumber(leftVal);
                    const rightNum = parseNumber(rightVal);

                    let numericChange = null;
                    if (leftNum !== null && rightNum !== null) {
                        if (leftNum !== 0) {
                            numericChange = ((rightNum - leftNum) / leftNum) * 100;
                        } else if (rightNum !== 0) {
                            // When old value is 0 but new value exists, treat as 100% increase
                            numericChange = 100;
                        }
                    }

                    diff.changes.push({
                        type: 'value_changed',
                        row: id,
                        column: col,
                        oldValue: leftVal,
                        newValue: rightVal,
                        numericChange
                    });
                }
            });
        });

        return diff;
    }

    /**
     * Parse number from string
     */
    function parseNumber(str) {
        if (typeof str === 'number') return str;
        if (!str) return null;
        // Remove commas, spaces, percentage signs, and emoji checkmarks
        const cleaned = str.toString().replace(/[,\s%✅❌]/g, '');
        const num = parseFloat(cleaned);
        return isNaN(num) ? null : num;
    }

    // =========================================
    // Rendering
    // =========================================

    /**
     * Render comparison results
     */
    function renderComparison(left, right, comparison) {
        // Render headers
        document.getElementById('header-left').textContent = left.title;
        document.getElementById('header-right').textContent = right.title;

        // Render content panels
        document.getElementById('content-left').innerHTML = left.content;
        document.getElementById('content-right').innerHTML = right.content;

        // Render summary
        const summaryList = document.getElementById('summary-list');
        if (summaryList) {
            if (comparison.summary.length > 0) {
                summaryList.innerHTML = comparison.summary
                    .map(s => `<li>${escapeHtml(s)}</li>`)
                    .join('');
            } else {
                summaryList.innerHTML = '<li>無顯著變化</li>';
            }
        }

        // Render detailed diff
        renderDetailedDiff(comparison);

        // Highlight differences in content panels
        highlightDifferences(left, right, comparison);

        // Render trend chart
        renderTrendChart(comparison);

        // Initialize synchronized scrolling
        initSyncScroll();
    }

    /**
     * Render detailed diff section
     */
    function renderDetailedDiff(comparison) {
        const diffContent = document.getElementById('diff-content');
        if (!diffContent) return;

        let html = '';

        Object.entries(comparison.tableDiffs).forEach(([tableName, diff]) => {
            if (diff.changes.length === 0 && diff.added.length === 0 && diff.removed.length === 0) {
                return;
            }

            html += `<h4>${escapeHtml(tableName)}</h4>`;

            // Added rows
            if (diff.added.length > 0) {
                html += '<div class="diff-section diff-added"><strong>新增：</strong><ul>';
                diff.added.forEach(row => {
                    const firstCol = Object.values(row)[0];
                    html += `<li>${escapeHtml(firstCol)}</li>`;
                });
                html += '</ul></div>';
            }

            // Removed rows
            if (diff.removed.length > 0) {
                html += '<div class="diff-section diff-removed"><strong>移除：</strong><ul>';
                diff.removed.forEach(row => {
                    const firstCol = Object.values(row)[0];
                    html += `<li>${escapeHtml(firstCol)}</li>`;
                });
                html += '</ul></div>';
            }

            // Changed values
            const significantChanges = diff.changes.filter(c =>
                c.numericChange !== null && Math.abs(c.numericChange) >= 1
            );

            if (significantChanges.length > 0) {
                html += '<div class="diff-section diff-changed"><strong>數值變化：</strong>';
                html += '<table class="data-table"><thead><tr>';
                html += '<th>項目</th><th>欄位</th><th>原值</th><th>新值</th><th>變化</th>';
                html += '</tr></thead><tbody>';

                significantChanges.forEach(change => {
                    const changeClass = change.numericChange > 0 ? 'text-success' : 'text-danger';
                    const arrow = change.numericChange > 0 ? '↑' : '↓';
                    const pct = Math.abs(change.numericChange).toFixed(1);

                    html += `<tr>
                        <td>${escapeHtml(change.row)}</td>
                        <td>${escapeHtml(change.column)}</td>
                        <td>${escapeHtml(change.oldValue)}</td>
                        <td>${escapeHtml(change.newValue)}</td>
                        <td class="${changeClass}">${arrow} ${pct}%</td>
                    </tr>`;
                });

                html += '</tbody></table></div>';
            }
        });

        if (!html) {
            html = '<p class="text-muted">報告結構相同，無明顯差異</p>';
        }

        diffContent.innerHTML = html;
    }

    /**
     * Highlight differences in content panels
     */
    function highlightDifferences(left, right, comparison) {
        // Add highlighting to tables in the panels
        Object.entries(comparison.tableDiffs).forEach(([tableName, diff]) => {
            diff.changes.forEach(change => {
                // This is a simplified version - full implementation would
                // traverse DOM and highlight specific cells
            });
        });
    }

    /**
     * Render trend chart using D3.js lollipop chart
     */
    function renderTrendChart(comparison) {
        const container = document.getElementById('trend-chart-container');
        if (!container || typeof d3 === 'undefined') {
            console.error('D3 not available or container not found');
            return;
        }

        // Clear container
        container.innerHTML = '';

        // Filter: prefer 合計/Total columns, exclude summary rows
        const seenRows = new Set();
        const changes = comparison.numericChanges
            .filter(c => {
                if (c.numericChange === null || Math.abs(c.numericChange) < 0.5) return false;
                // Exclude summary rows (合計, Total, etc.)
                const rowName = (c.row || '').toLowerCase();
                if (rowName.includes('合計') || rowName.includes('total') || rowName.startsWith('**')) return false;
                return true;
            })
            // Prioritize 合計 columns for value
            .sort((a, b) => {
                const aIsTotal = (a.column || '').includes('合計') || (a.column || '').toLowerCase().includes('total');
                const bIsTotal = (b.column || '').includes('合計') || (b.column || '').toLowerCase().includes('total');
                if (aIsTotal && !bIsTotal) return -1;
                if (!aIsTotal && bIsTotal) return 1;
                return Math.abs(b.numericChange) - Math.abs(a.numericChange);
            })
            // Only keep one entry per row (prefer 合計 column)
            .filter(c => {
                if (seenRows.has(c.row)) return false;
                seenRows.add(c.row);
                return true;
            })
            .sort((a, b) => Math.abs(b.numericChange) - Math.abs(a.numericChange))
            .slice(0, 12);

        if (changes.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">無顯著數值變化</p>';
            return;
        }

        // Prepare data - simple labels
        const data = changes.map(c => ({
            label: c.row,
            value: c.numericChange,
            oldVal: c.oldValue,
            newVal: c.newValue
        }));

        // Dimensions
        const margin = { top: 30, right: 80, bottom: 20, left: 180 };
        const width = (container.clientWidth || 700) - margin.left - margin.right;
        const rowHeight = 32;
        const height = data.length * rowHeight;

        // Create SVG
        const svg = d3.select(container)
            .append('svg')
            .attr('width', width + margin.left + margin.right)
            .attr('height', height + margin.top + margin.bottom);

        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        // Find max absolute value
        const maxAbs = d3.max(data, d => Math.abs(d.value)) || 1;

        // X Scale - centered at 0
        const x = d3.scaleLinear()
            .domain([-maxAbs * 1.2, maxAbs * 1.2])
            .range([0, width]);

        // Y Scale
        const y = d3.scaleBand()
            .domain(data.map(d => d.label))
            .range([0, height])
            .padding(0.3);

        // Add vertical zero line
        g.append('line')
            .attr('x1', x(0))
            .attr('x2', x(0))
            .attr('y1', -10)
            .attr('y2', height + 10)
            .attr('stroke', '#999')
            .attr('stroke-width', 1)
            .attr('stroke-dasharray', '3,3');

        // Add horizontal grid lines
        g.selectAll('.grid-line')
            .data(data)
            .enter()
            .append('line')
            .attr('class', 'grid-line')
            .attr('x1', 0)
            .attr('x2', width)
            .attr('y1', d => y(d.label) + y.bandwidth() / 2)
            .attr('y2', d => y(d.label) + y.bandwidth() / 2)
            .attr('stroke', '#eee')
            .attr('stroke-width', 1);

        // Add lines (lollipop stems)
        g.selectAll('.stem')
            .data(data)
            .enter()
            .append('line')
            .attr('class', 'stem')
            .attr('x1', x(0))
            .attr('x2', d => x(d.value))
            .attr('y1', d => y(d.label) + y.bandwidth() / 2)
            .attr('y2', d => y(d.label) + y.bandwidth() / 2)
            .attr('stroke', d => d.value >= 0 ? '#198754' : '#dc3545')
            .attr('stroke-width', 3);

        // Add circles (lollipop heads)
        g.selectAll('.head')
            .data(data)
            .enter()
            .append('circle')
            .attr('class', 'head')
            .attr('cx', d => x(d.value))
            .attr('cy', d => y(d.label) + y.bandwidth() / 2)
            .attr('r', 8)
            .attr('fill', d => d.value >= 0 ? '#198754' : '#dc3545');

        // Add value labels
        g.selectAll('.value-label')
            .data(data)
            .enter()
            .append('text')
            .attr('class', 'value-label')
            .attr('x', d => x(d.value) + (d.value >= 0 ? 15 : -15))
            .attr('y', d => y(d.label) + y.bandwidth() / 2)
            .attr('dy', '0.35em')
            .attr('text-anchor', d => d.value >= 0 ? 'start' : 'end')
            .attr('fill', d => d.value >= 0 ? '#198754' : '#dc3545')
            .attr('font-size', '12px')
            .attr('font-weight', '600')
            .text(d => (d.value >= 0 ? '+' : '') + d.value.toFixed(1) + '%');

        // Add Y axis labels
        g.selectAll('.y-label')
            .data(data)
            .enter()
            .append('text')
            .attr('class', 'y-label')
            .attr('x', -10)
            .attr('y', d => y(d.label) + y.bandwidth() / 2)
            .attr('dy', '0.35em')
            .attr('text-anchor', 'end')
            .attr('fill', '#333')
            .attr('font-size', '12px')
            .text(d => d.label.length > 22 ? d.label.substring(0, 20) + '...' : d.label);

        // Add title
        svg.append('text')
            .attr('x', margin.left + width / 2)
            .attr('y', 18)
            .attr('text-anchor', 'middle')
            .attr('font-size', '14px')
            .attr('fill', '#666')
            .text('← 減少　　　增加 →');

        // Add explanation below chart
        const explanation = document.createElement('p');
        explanation.className = 'text-muted';
        explanation.style.cssText = 'font-size: 12px; margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 4px;';
        explanation.innerHTML = `
            <strong>說明：</strong>顯示兩份報告間各項目「合計」數值的變化百分比。<br>
            <span style="color:#198754">● 綠色 = 增加</span>
            <span style="color:#dc3545">● 紅色 = 減少</span>
            計算：(新值 - 舊值) ÷ 舊值 × 100%
        `;
        container.appendChild(explanation);
    }

    // =========================================
    // Utilities
    // =========================================

    /**
     * Escape HTML
     */
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // =========================================
    // Synchronized Scrolling
    // =========================================

    let syncScrollEnabled = true;
    let isScrolling = false;

    /**
     * Initialize synchronized scrolling between panels
     */
    function initSyncScroll() {
        const leftPanel = document.getElementById('content-left');
        const rightPanel = document.getElementById('content-right');

        if (!leftPanel || !rightPanel) return;

        // Build heading maps for both panels
        const leftHeadings = buildHeadingMap(leftPanel);
        const rightHeadings = buildHeadingMap(rightPanel);

        // Scroll handler for left panel
        leftPanel.addEventListener('scroll', function() {
            if (!syncScrollEnabled || isScrolling) return;
            syncToHeading(leftPanel, rightPanel, leftHeadings, rightHeadings);
        });

        // Scroll handler for right panel
        rightPanel.addEventListener('scroll', function() {
            if (!syncScrollEnabled || isScrolling) return;
            syncToHeading(rightPanel, leftPanel, rightHeadings, leftHeadings);
        });
    }

    /**
     * Build a map of heading text to offset positions
     */
    function buildHeadingMap(panel) {
        const headings = panel.querySelectorAll('h1, h2, h3, h4');
        const map = [];

        headings.forEach(h => {
            const text = normalizeHeadingText(h.textContent);
            map.push({
                text: text,
                element: h,
                offsetTop: h.offsetTop
            });
        });

        return map;
    }

    /**
     * Normalize heading text for matching
     */
    function normalizeHeadingText(text) {
        return text.trim()
            .replace(/\s+/g, ' ')
            .replace(/[—–-]\s*\d{4}.*$/g, '') // Remove date suffixes
            .toLowerCase();
    }

    /**
     * Sync scroll to matching heading
     */
    function syncToHeading(sourcePanel, targetPanel, sourceHeadings, targetHeadings) {
        const scrollTop = sourcePanel.scrollTop;
        const panelHeight = sourcePanel.clientHeight;

        // Find the heading currently at the top of the visible area
        let currentHeading = null;
        for (let i = sourceHeadings.length - 1; i >= 0; i--) {
            if (sourceHeadings[i].offsetTop <= scrollTop + 50) {
                currentHeading = sourceHeadings[i];
                break;
            }
        }

        if (!currentHeading) {
            // No heading found, sync by percentage
            isScrolling = true;
            const scrollPercent = scrollTop / (sourcePanel.scrollHeight - panelHeight);
            targetPanel.scrollTop = scrollPercent * (targetPanel.scrollHeight - targetPanel.clientHeight);
            setTimeout(() => { isScrolling = false; }, 50);
            return;
        }

        // Find matching heading in target panel
        const matchingHeading = targetHeadings.find(h => h.text === currentHeading.text);

        if (matchingHeading) {
            isScrolling = true;
            // Calculate offset within the current section
            const offsetInSection = scrollTop - currentHeading.offsetTop;
            targetPanel.scrollTop = matchingHeading.offsetTop + offsetInSection;
            setTimeout(() => { isScrolling = false; }, 50);
        }
    }

    // =========================================
    // Export
    // =========================================

    window.Compare = {
        performCompare,
        generateComparison,
        initSyncScroll
    };

})();
