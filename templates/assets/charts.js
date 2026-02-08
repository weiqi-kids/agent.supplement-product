/**
 * 保健食品產品情報系統 — D3.js 圖表模組
 */

(function() {
    'use strict';

    // =========================================
    // Configuration
    // =========================================

    const CONFIG = {
        colors: [
            '#4e79a7', '#f28e2c', '#e15759', '#76b7b2',
            '#59a14f', '#edc949', '#af7aa1', '#ff9da7'
        ],
        marketColors: {
            us: '#3b82f6',
            ca: '#ef4444',
            kr: '#10b981',
            jp: '#f59e0b',
            tw: '#8b5cf6'
        },
        margin: { top: 20, right: 30, bottom: 40, left: 150 },
        transition: 300
    };

    // =========================================
    // Utility Functions
    // =========================================

    /**
     * Parse number from formatted string
     */
    function parseFormattedNumber(str) {
        if (typeof str === 'number') return str;
        if (!str) return 0;
        // Remove commas, percentage signs, and other formatting
        const cleaned = str.toString().replace(/[,\s%K]/g, '');
        // Handle 'K' suffix for thousands
        if (str.toString().includes('K')) {
            return parseFloat(cleaned) * 1000;
        }
        return parseFloat(cleaned) || 0;
    }

    /**
     * Format number for display
     */
    function formatDisplayNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString('zh-TW');
    }

    /**
     * Extract data from HTML table
     */
    function extractTableData(table) {
        const headers = [];
        const rows = [];

        // Get headers
        const headerCells = table.querySelectorAll('thead th, tr:first-child th');
        headerCells.forEach(th => {
            headers.push(th.textContent.trim());
        });

        // Get rows
        const bodyRows = table.querySelectorAll('tbody tr, tr:not(:first-child)');
        bodyRows.forEach(tr => {
            const row = {};
            const cells = tr.querySelectorAll('td');
            cells.forEach((td, i) => {
                const key = headers[i] || `col${i}`;
                row[key] = td.textContent.trim();
            });
            if (Object.keys(row).length > 0) {
                rows.push(row);
            }
        });

        return { headers, rows };
    }

    // =========================================
    // Bar Chart
    // =========================================

    /**
     * Create horizontal bar chart
     */
    function createBarChart(container, data, options = {}) {
        const {
            valueKey = null,
            labelKey = null,
            title = '',
            maxItems = 10,
            showValues = true
        } = options;

        // Clear container
        container.innerHTML = '';

        // Determine keys
        const headers = Object.keys(data[0] || {});

        // Smart label detection: skip columns that look like rankings (1, 2, 3...)
        let actualLabelKey = labelKey;
        let rankingCol = null;
        if (!actualLabelKey) {
            // Check if first column is numeric ranking
            const firstColValues = data.map(d => d[headers[0]]).filter(v => v);
            const isRanking = firstColValues.every(v => /^\d+$/.test(v.toString().trim()));
            if (isRanking && headers.length > 1) {
                rankingCol = headers[0];
                actualLabelKey = headers[1];
            } else {
                actualLabelKey = headers[0];
            }
        }

        // Smart value detection: prefer "合計" column, or column with "數" in name, then find numeric
        let actualValueKey = valueKey;
        if (!actualValueKey) {
            // Look for 合計 (total) column
            const totalCol = headers.find(h => h.includes('合計') || h.toLowerCase().includes('total'));
            // Look for column with 數 (count) in name
            const countCol = headers.find(h => h.includes('產品數') || h.includes('數'));
            if (totalCol) {
                actualValueKey = totalCol;
            } else if (countCol) {
                actualValueKey = countCol;
            } else {
                // Find the first numeric column that's not the label or ranking column
                actualValueKey = headers.find(h =>
                    h !== actualLabelKey && h !== rankingCol && !isNaN(parseFormattedNumber(data[0]?.[h]))
                ) || headers[2] || headers[1];
            }
        }

        // Prepare data - filter out summary rows (e.g., "合計", "Total")
        const chartData = data
            .filter(d => {
                const label = (d[actualLabelKey] || '').toString().toLowerCase();
                return !label.includes('合計') && !label.includes('total') && !label.startsWith('**');
            })
            .slice(0, maxItems)
            .map(d => ({
                label: d[actualLabelKey],
                value: parseFormattedNumber(d[actualValueKey])
            }))
            .filter(d => d.value > 0);

        if (chartData.length === 0) {
            container.innerHTML = '<p class="text-muted">無可視覺化的數據</p>';
            container.dataset.chartFailed = 'true';
            return;
        }

        // Dimensions
        const containerWidth = container.clientWidth || 600;
        const width = containerWidth - CONFIG.margin.left - CONFIG.margin.right;
        const barHeight = 30;
        const height = chartData.length * barHeight + CONFIG.margin.top + CONFIG.margin.bottom;

        // Create SVG
        const svg = d3.select(container)
            .append('svg')
            .attr('width', containerWidth)
            .attr('height', height)
            .attr('class', 'chart-svg');

        const g = svg.append('g')
            .attr('transform', `translate(${CONFIG.margin.left},${CONFIG.margin.top})`);

        // Scales
        const x = d3.scaleLinear()
            .domain([0, d3.max(chartData, d => d.value)])
            .range([0, width]);

        const y = d3.scaleBand()
            .domain(chartData.map(d => d.label))
            .range([0, chartData.length * barHeight])
            .padding(0.2);

        // Tooltip
        const tooltip = d3.select(container)
            .append('div')
            .attr('class', 'chart-tooltip');

        // Bars
        g.selectAll('.chart-bar')
            .data(chartData)
            .enter()
            .append('rect')
            .attr('class', 'chart-bar')
            .attr('x', 0)
            .attr('y', d => y(d.label))
            .attr('height', y.bandwidth())
            .attr('width', 0)
            .attr('fill', (d, i) => CONFIG.colors[i % CONFIG.colors.length])
            .on('mouseover', function(event, d) {
                d3.select(this).attr('fill', CONFIG.colors[1]);
                tooltip
                    .style('opacity', 1)
                    .html(`<strong>${d.label}</strong><br>${formatDisplayNumber(d.value)}`);
            })
            .on('mousemove', function(event) {
                tooltip
                    .style('left', (event.offsetX + 10) + 'px')
                    .style('top', (event.offsetY - 10) + 'px');
            })
            .on('mouseout', function(event, d) {
                const i = chartData.indexOf(d);
                d3.select(this).attr('fill', CONFIG.colors[i % CONFIG.colors.length]);
                tooltip.style('opacity', 0);
            })
            .transition()
            .duration(CONFIG.transition)
            .attr('width', d => x(d.value));

        // Value labels
        if (showValues) {
            g.selectAll('.value-label')
                .data(chartData)
                .enter()
                .append('text')
                .attr('class', 'value-label')
                .attr('x', d => x(d.value) + 5)
                .attr('y', d => y(d.label) + y.bandwidth() / 2)
                .attr('dy', '0.35em')
                .style('font-size', '11px')
                .style('fill', '#666')
                .text(d => formatDisplayNumber(d.value));
        }

        // Y Axis (labels)
        g.append('g')
            .attr('class', 'chart-axis')
            .call(d3.axisLeft(y).tickSize(0))
            .select('.domain')
            .remove();

        // Title
        if (title) {
            svg.append('text')
                .attr('x', containerWidth / 2)
                .attr('y', 15)
                .attr('text-anchor', 'middle')
                .style('font-weight', '600')
                .text(title);
        }
    }

    // =========================================
    // Donut Chart
    // =========================================

    /**
     * Create donut/pie chart
     */
    function createDonutChart(container, data, options = {}) {
        const {
            valueKey = null,
            labelKey = null,
            title = '',
            maxItems = 8
        } = options;

        // Clear container
        container.innerHTML = '';

        // Determine keys
        const headers = Object.keys(data[0] || {});

        // Smart label detection: skip columns that look like rankings (1, 2, 3...)
        let actualLabelKey = labelKey;
        let rankingCol = null;
        if (!actualLabelKey) {
            const firstColValues = data.map(d => d[headers[0]]).filter(v => v);
            const isRanking = firstColValues.every(v => /^\d+$/.test(v.toString().trim()));
            if (isRanking && headers.length > 1) {
                rankingCol = headers[0];
                actualLabelKey = headers[1];
            } else {
                actualLabelKey = headers[0];
            }
        }

        // Smart value detection: prefer "合計" column, or column with "數" in name, then find numeric
        let actualValueKey = valueKey;
        if (!actualValueKey) {
            const totalCol = headers.find(h => h.includes('合計') || h.toLowerCase().includes('total'));
            const countCol = headers.find(h => h.includes('產品數') || h.includes('數'));
            if (totalCol) {
                actualValueKey = totalCol;
            } else if (countCol) {
                actualValueKey = countCol;
            } else {
                actualValueKey = headers.find(h =>
                    h !== actualLabelKey && h !== rankingCol && !isNaN(parseFormattedNumber(data[0]?.[h]))
                ) || headers[2] || headers[1];
            }
        }

        // Prepare data - filter out summary rows (e.g., "合計", "Total")
        let chartData = data
            .filter(d => {
                const label = (d[actualLabelKey] || '').toString().toLowerCase();
                return !label.includes('合計') && !label.includes('total') && !label.startsWith('**');
            })
            .map(d => ({
                label: d[actualLabelKey],
                value: parseFormattedNumber(d[actualValueKey])
            }))
            .filter(d => d.value > 0)
            .sort((a, b) => b.value - a.value);

        // Group small items as "Other"
        if (chartData.length > maxItems) {
            const topItems = chartData.slice(0, maxItems - 1);
            const otherValue = chartData.slice(maxItems - 1).reduce((sum, d) => sum + d.value, 0);
            chartData = [...topItems, { label: '其他', value: otherValue }];
        }

        if (chartData.length === 0) {
            container.innerHTML = '<p class="text-muted">無可視覺化的數據</p>';
            container.dataset.chartFailed = 'true';
            return;
        }

        // Dimensions
        const containerWidth = container.clientWidth || 400;
        const size = Math.min(containerWidth, 400);
        const radius = size / 2 - 40;

        // Create SVG
        const svg = d3.select(container)
            .append('svg')
            .attr('width', size)
            .attr('height', size)
            .append('g')
            .attr('transform', `translate(${size / 2},${size / 2})`);

        // Pie generator
        const pie = d3.pie()
            .value(d => d.value)
            .sort(null);

        // Arc generator
        const arc = d3.arc()
            .innerRadius(radius * 0.5)
            .outerRadius(radius);

        // Hover arc
        const arcHover = d3.arc()
            .innerRadius(radius * 0.5)
            .outerRadius(radius * 1.05);

        // Color scale
        const color = d3.scaleOrdinal()
            .domain(chartData.map(d => d.label))
            .range(CONFIG.colors);

        // Tooltip
        const tooltip = d3.select(container)
            .append('div')
            .attr('class', 'chart-tooltip');

        // Total for percentage
        const total = d3.sum(chartData, d => d.value);

        // Draw arcs
        const arcs = svg.selectAll('.arc')
            .data(pie(chartData))
            .enter()
            .append('g')
            .attr('class', 'arc');

        arcs.append('path')
            .attr('d', arc)
            .attr('fill', d => color(d.data.label))
            .style('stroke', '#fff')
            .style('stroke-width', 2)
            .on('mouseover', function(event, d) {
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr('d', arcHover);

                const pct = ((d.data.value / total) * 100).toFixed(1);
                tooltip
                    .style('opacity', 1)
                    .html(`<strong>${d.data.label}</strong><br>${formatDisplayNumber(d.data.value)} (${pct}%)`);
            })
            .on('mousemove', function(event) {
                tooltip
                    .style('left', (event.offsetX + 10) + 'px')
                    .style('top', (event.offsetY - 10) + 'px');
            })
            .on('mouseout', function() {
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr('d', arc);
                tooltip.style('opacity', 0);
            });

        // Center text
        svg.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '-0.2em')
            .style('font-size', '24px')
            .style('font-weight', '700')
            .text(formatDisplayNumber(total));

        svg.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '1.2em')
            .style('font-size', '12px')
            .style('fill', '#666')
            .text('總計');

        // Legend
        const legend = d3.select(container)
            .append('div')
            .style('display', 'flex')
            .style('flex-wrap', 'wrap')
            .style('justify-content', 'center')
            .style('gap', '10px')
            .style('margin-top', '15px');

        chartData.forEach((d, i) => {
            legend.append('div')
                .style('display', 'flex')
                .style('align-items', 'center')
                .style('gap', '5px')
                .style('font-size', '12px')
                .html(`<span style="width:12px;height:12px;background:${color(d.label)};border-radius:2px;"></span>${d.label}`);
        });
    }

    // =========================================
    // Heatmap
    // =========================================

    /**
     * Create heatmap chart
     */
    function createHeatmap(container, data, options = {}) {
        const {
            rowKey = null,
            colKeys = null,
            title = ''
        } = options;

        // Clear container
        container.innerHTML = '';

        if (!data || data.length === 0) {
            container.innerHTML = '<p class="text-muted">無可視覺化的數據</p>';
            return;
        }

        // Determine keys
        const headers = Object.keys(data[0]);
        const actualRowKey = rowKey || headers[0];
        const actualColKeys = colKeys || headers.filter(h => h !== actualRowKey);

        // Prepare data
        const rows = data.map(d => d[actualRowKey]);
        const cols = actualColKeys;

        // Find max value for color scale
        let maxVal = 0;
        data.forEach(d => {
            cols.forEach(col => {
                const val = parseFormattedNumber(d[col]);
                if (val > maxVal) maxVal = val;
            });
        });

        // Dimensions
        const containerWidth = container.clientWidth || 600;
        const cellSize = 50;
        const width = cols.length * cellSize + CONFIG.margin.left + CONFIG.margin.right;
        const height = rows.length * cellSize + CONFIG.margin.top + CONFIG.margin.bottom;

        // Create SVG
        const svg = d3.select(container)
            .append('svg')
            .attr('width', Math.max(containerWidth, width))
            .attr('height', height);

        const g = svg.append('g')
            .attr('transform', `translate(${CONFIG.margin.left},${CONFIG.margin.top})`);

        // Color scale
        const colorScale = d3.scaleSequential()
            .interpolator(d3.interpolateBlues)
            .domain([0, maxVal]);

        // Tooltip
        const tooltip = d3.select(container)
            .append('div')
            .attr('class', 'chart-tooltip');

        // Draw cells
        data.forEach((rowData, rowIndex) => {
            cols.forEach((col, colIndex) => {
                const value = parseFormattedNumber(rowData[col]);

                g.append('rect')
                    .attr('x', colIndex * cellSize)
                    .attr('y', rowIndex * cellSize)
                    .attr('width', cellSize - 2)
                    .attr('height', cellSize - 2)
                    .attr('fill', value > 0 ? colorScale(value) : '#f0f0f0')
                    .attr('rx', 4)
                    .style('cursor', 'pointer')
                    .on('mouseover', function(event) {
                        d3.select(this).style('stroke', '#333').style('stroke-width', 2);
                        tooltip
                            .style('opacity', 1)
                            .html(`<strong>${rowData[actualRowKey]}</strong> × <strong>${col}</strong><br>${formatDisplayNumber(value)}`);
                    })
                    .on('mousemove', function(event) {
                        tooltip
                            .style('left', (event.offsetX + 10) + 'px')
                            .style('top', (event.offsetY - 10) + 'px');
                    })
                    .on('mouseout', function() {
                        d3.select(this).style('stroke', 'none');
                        tooltip.style('opacity', 0);
                    });
            });
        });

        // Row labels
        g.selectAll('.row-label')
            .data(rows)
            .enter()
            .append('text')
            .attr('x', -10)
            .attr('y', (d, i) => i * cellSize + cellSize / 2)
            .attr('text-anchor', 'end')
            .attr('dy', '0.35em')
            .style('font-size', '11px')
            .text(d => d);

        // Column labels
        g.selectAll('.col-label')
            .data(cols)
            .enter()
            .append('text')
            .attr('x', (d, i) => i * cellSize + cellSize / 2)
            .attr('y', -10)
            .attr('text-anchor', 'middle')
            .style('font-size', '11px')
            .text(d => d);
    }

    // =========================================
    // Auto-detect and Initialize Charts
    // =========================================

    /**
     * Check if table is a cross-tabulation (multiple numeric columns)
     */
    function isCrossTab(data) {
        if (!data.headers || data.headers.length < 3) return false;

        // Count numeric columns (excluding first column which is usually label)
        let numericColCount = 0;
        const firstRow = data.rows[0] || {};

        for (let i = 1; i < data.headers.length; i++) {
            const val = firstRow[data.headers[i]];
            if (val !== undefined && !isNaN(parseFormattedNumber(val))) {
                numericColCount++;
            }
        }

        // If more than 2 numeric columns, it's likely a cross-tab
        return numericColCount > 2;
    }

    /**
     * Initialize charts for tables with data-chart attribute
     */
    window.initializeCharts = function() {
        // Find tables with chart attribute
        const chartTables = document.querySelectorAll('table[data-chart]');

        chartTables.forEach(table => {
            // Skip if already processed
            if (table.dataset.chartProcessed === 'true') return;
            table.dataset.chartProcessed = 'true';

            const chartType = table.dataset.chart;
            const chartTitle = table.dataset.chartTitle || '';
            const data = extractTableData(table);

            // Parse maxItems from title (e.g., "Top 20" → 20)
            const topMatch = chartTitle.match(/Top\s*(\d+)/i);
            const maxItemsFromTitle = topMatch ? parseInt(topMatch[1], 10) : null;

            if (data.rows.length === 0) return;

            // Skip chart for cross-tabulation tables (multi-column numeric data)
            if (isCrossTab(data) && (chartType === 'donut' || chartType === 'pie')) {
                // Don't create chart wrapper, just keep the table as-is
                return;
            }

            // Create chart container
            const container = document.createElement('div');
            container.className = 'chart-container chart-view';
            container.style.marginTop = '20px';

            // Add toggle buttons (no title - already shown in h2/h3 above)
            const headerDiv = document.createElement('div');
            headerDiv.className = 'chart-header';
            headerDiv.style.cssText = 'display: flex; justify-content: flex-end; align-items: center; margin-bottom: 10px;';

            const toggleDiv = document.createElement('div');
            toggleDiv.className = 'chart-toggle';
            toggleDiv.innerHTML = `
                <button class="chart-toggle-btn active" data-view="chart">📈 圖表</button>
                <button class="chart-toggle-btn" data-view="table">📋 表格</button>
            `;

            headerDiv.appendChild(toggleDiv);

            // Wrap table
            const wrapper = document.createElement('div');
            wrapper.className = 'chart-table-wrapper';
            table.parentNode.insertBefore(wrapper, table);
            table.classList.add('table-view');
            wrapper.appendChild(headerDiv);
            wrapper.appendChild(container);
            wrapper.appendChild(table);

            // Hide table initially if chart is shown
            table.style.display = 'none';

            // Determine maxItems
            const maxItems = parseInt(table.dataset.chartMaxItems) || maxItemsFromTitle || 10;

            // Create chart
            switch (chartType) {
                case 'bar':
                    createBarChart(container, data.rows, {
                        title: '',  // Don't show title in chart (already in h2/h3)
                        maxItems: maxItems
                    });
                    break;
                case 'donut':
                case 'pie':
                    createDonutChart(container, data.rows, {
                        title: '',
                        maxItems: maxItems
                    });
                    break;
                case 'heatmap':
                    createHeatmap(container, data.rows, {
                        title: ''
                    });
                    break;
                default:
                    createBarChart(container, data.rows, { title: '', maxItems: maxItems });
            }

            // Check if chart rendering failed
            if (container.dataset.chartFailed === 'true') {
                // Hide toggle buttons and show table instead
                toggleDiv.style.display = 'none';
                container.style.display = 'none';
                table.style.display = 'table';
                return;
            }

            // Toggle handlers
            toggleDiv.addEventListener('click', function(e) {
                if (e.target.classList.contains('chart-toggle-btn')) {
                    const view = e.target.dataset.view;

                    toggleDiv.querySelectorAll('.chart-toggle-btn').forEach(btn => {
                        btn.classList.remove('active');
                    });
                    e.target.classList.add('active');

                    if (view === 'chart') {
                        container.style.display = 'block';
                        table.style.display = 'none';
                    } else {
                        container.style.display = 'none';
                        table.style.display = 'table';
                    }
                }
            });
        });

        // Also initialize any manual chart containers
        const manualCharts = document.querySelectorAll('[data-chart-data]');
        manualCharts.forEach(container => {
            try {
                const data = JSON.parse(container.dataset.chartData);
                const chartType = container.dataset.chartType || 'bar';

                switch (chartType) {
                    case 'bar':
                        createBarChart(container, data);
                        break;
                    case 'donut':
                        createDonutChart(container, data);
                        break;
                    case 'heatmap':
                        createHeatmap(container, data);
                        break;
                }
            } catch (e) {
                console.error('Failed to parse chart data:', e);
            }
        });
    };

    // Export chart functions
    window.Charts = {
        createBarChart,
        createDonutChart,
        createHeatmap,
        extractTableData
    };

})();
