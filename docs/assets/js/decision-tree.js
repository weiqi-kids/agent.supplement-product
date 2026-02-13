/**
 * Interactive Decision Tree Component
 * Built with D3.js for supplement selection guidance
 */

class DecisionTree {
  constructor(containerId, data, options = {}) {
    this.container = d3.select(`#${containerId}`);
    this.data = data;
    this.options = {
      width: options.width || 800,
      height: options.height || 500,
      nodeRadius: options.nodeRadius || 8,
      duration: options.duration || 400,
      margin: options.margin || { top: 40, right: 120, bottom: 40, left: 120 },
      ...options
    };

    this.i = 0;
    this.root = null;
    this.svg = null;
    this.treemap = null;

    this.init();
  }

  init() {
    // Clear container
    this.container.html('');

    // Create SVG
    this.svg = this.container
      .append('svg')
      .attr('width', '100%')
      .attr('viewBox', `0 0 ${this.options.width} ${this.options.height}`)
      .attr('class', 'decision-tree-svg')
      .append('g')
      .attr('transform', `translate(${this.options.margin.left},${this.options.margin.top})`);

    // Create tree layout
    const innerWidth = this.options.width - this.options.margin.left - this.options.margin.right;
    const innerHeight = this.options.height - this.options.margin.top - this.options.margin.bottom;

    this.treemap = d3.tree().size([innerHeight, innerWidth]);

    // Process data
    this.root = d3.hierarchy(this.data, d => d.children);
    this.root.x0 = innerHeight / 2;
    this.root.y0 = 0;

    // Collapse all children initially except first level
    if (this.root.children) {
      this.root.children.forEach(child => this.collapse(child));
    }

    this.update(this.root);

    // Add legend
    this.addLegend();
  }

  collapse(d) {
    if (d.children) {
      d._children = d.children;
      d._children.forEach(child => this.collapse(child));
      d.children = null;
    }
  }

  update(source) {
    const treeData = this.treemap(this.root);
    const nodes = treeData.descendants();
    const links = treeData.descendants().slice(1);

    // Normalize for fixed-depth
    nodes.forEach(d => { d.y = d.depth * 180; });

    // ****************** Nodes section ***************************
    const node = this.svg.selectAll('g.node')
      .data(nodes, d => d.id || (d.id = ++this.i));

    // Enter new nodes
    const nodeEnter = node.enter().append('g')
      .attr('class', d => `node ${d.data.type || 'question'}`)
      .attr('transform', d => `translate(${source.y0},${source.x0})`)
      .on('click', (event, d) => this.click(d));

    // Add circles for nodes
    nodeEnter.append('circle')
      .attr('class', 'node-circle')
      .attr('r', 1e-6)
      .style('fill', d => this.getNodeColor(d));

    // Add labels
    nodeEnter.append('text')
      .attr('dy', '.35em')
      .attr('x', d => d.children || d._children ? -13 : 13)
      .attr('text-anchor', d => d.children || d._children ? 'end' : 'start')
      .text(d => d.data.name)
      .style('fill-opacity', 1e-6);

    // Add recommendation badge
    nodeEnter.filter(d => d.data.recommended)
      .append('text')
      .attr('class', 'badge recommended')
      .attr('dy', '-1.2em')
      .attr('x', 13)
      .text('推薦');

    // UPDATE
    const nodeUpdate = nodeEnter.merge(node);

    nodeUpdate.transition()
      .duration(this.options.duration)
      .attr('transform', d => `translate(${d.y},${d.x})`);

    nodeUpdate.select('circle.node-circle')
      .attr('r', this.options.nodeRadius)
      .style('fill', d => this.getNodeColor(d))
      .attr('cursor', d => d.children || d._children ? 'pointer' : 'default');

    nodeUpdate.select('text')
      .style('fill-opacity', 1);

    // EXIT
    const nodeExit = node.exit().transition()
      .duration(this.options.duration)
      .attr('transform', d => `translate(${source.y},${source.x})`)
      .remove();

    nodeExit.select('circle').attr('r', 1e-6);
    nodeExit.select('text').style('fill-opacity', 1e-6);

    // ****************** Links section ***************************
    const link = this.svg.selectAll('path.link')
      .data(links, d => d.id);

    // Enter new links
    const linkEnter = link.enter().insert('path', 'g')
      .attr('class', 'link')
      .attr('d', d => {
        const o = { x: source.x0, y: source.y0 };
        return this.diagonal(o, o);
      });

    // UPDATE
    const linkUpdate = linkEnter.merge(link);

    linkUpdate.transition()
      .duration(this.options.duration)
      .attr('d', d => this.diagonal(d, d.parent));

    // EXIT
    link.exit().transition()
      .duration(this.options.duration)
      .attr('d', d => {
        const o = { x: source.x, y: source.y };
        return this.diagonal(o, o);
      })
      .remove();

    // Store old positions
    nodes.forEach(d => {
      d.x0 = d.x;
      d.y0 = d.y;
    });
  }

  diagonal(s, d) {
    return `M ${s.y} ${s.x}
            C ${(s.y + d.y) / 2} ${s.x},
              ${(s.y + d.y) / 2} ${d.x},
              ${d.y} ${d.x}`;
  }

  click(d) {
    if (d.data.link) {
      window.location.href = d.data.link;
      return;
    }

    if (d.children) {
      d._children = d.children;
      d.children = null;
    } else {
      d.children = d._children;
      d._children = null;
    }
    this.update(d);
  }

  getNodeColor(d) {
    if (d.data.type === 'answer') {
      return d.data.recommended ? '#28a745' : '#17a2b8';
    }
    if (d._children) {
      return '#6c757d';
    }
    if (d.children) {
      return '#007bff';
    }
    return '#6c757d';
  }

  addLegend() {
    const legend = this.container.append('div')
      .attr('class', 'decision-tree-legend');

    legend.html(`
      <span class="legend-item">
        <span class="dot question"></span> 點擊展開選項
      </span>
      <span class="legend-item">
        <span class="dot answer"></span> 建議方案
      </span>
      <span class="legend-item">
        <span class="dot recommended"></span> 推薦選擇
      </span>
    `);
  }

  // Expand all nodes
  expandAll() {
    this.expandNode(this.root);
    this.update(this.root);
  }

  expandNode(d) {
    if (d._children) {
      d.children = d._children;
      d._children = null;
    }
    if (d.children) {
      d.children.forEach(child => this.expandNode(child));
    }
  }

  // Collapse all nodes
  collapseAll() {
    if (this.root.children) {
      this.root.children.forEach(child => this.collapse(child));
    }
    this.update(this.root);
  }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = DecisionTree;
}
