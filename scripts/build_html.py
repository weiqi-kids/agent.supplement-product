#!/usr/bin/env python3
"""
Narrator 報告 HTML 生成器

用法：
    python3 scripts/build_html.py              # 建置所有報告
    python3 scripts/build_html.py --watch      # 監控模式（開發用）
    python3 scripts/build_html.py --clean      # 清除並重建
    python3 scripts/build_html.py --verbose    # 詳細輸出
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Third-party imports with fallback
try:
    import markdown
    from markdown.extensions import tables, toc, fenced_code
except ImportError:
    print("Error: 'markdown' package not found. Install with: pip install markdown")
    sys.exit(1)

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    print("Error: 'jinja2' package not found. Install with: pip install jinja2")
    sys.exit(1)

try:
    import yaml
except ImportError:
    yaml = None  # YAML frontmatter is optional


# =========================================
# Configuration
# =========================================

class Config:
    """Build configuration"""
    # Paths
    PROJECT_ROOT = Path(__file__).parent.parent
    NARRATOR_DIR = PROJECT_ROOT / "docs" / "Narrator"
    OUTPUT_DIR = PROJECT_ROOT / "docs" / "html"
    TEMPLATE_DIR = PROJECT_ROOT / "templates"
    ASSETS_DIR = TEMPLATE_DIR / "assets"

    # Mode display names (only implemented modes)
    MODE_NAMES = {
        "market_snapshot": {"display": "市場快照", "icon": "📊", "frequency": "週報"},
        "ingredient_radar": {"display": "成分雷達", "icon": "🧪", "frequency": "月報"},
        # Future modes (not yet implemented):
        # "trend_analysis": {"display": "趨勢分析", "icon": "📈", "frequency": "季報"},
        # "competitive_intel": {"display": "競爭情報", "icon": "🏢", "frequency": "不定期"},
    }

    # Market codes
    MARKETS = {
        "us": {"name": "美國", "flag": "🇺🇸", "code": "US"},
        "ca": {"name": "加拿大", "flag": "🇨🇦", "code": "CA"},
        "kr": {"name": "韓國", "flag": "🇰🇷", "code": "KR"},
        "jp": {"name": "日本", "flag": "🇯🇵", "code": "JP"},
        "tw": {"name": "台灣", "flag": "🇹🇼", "code": "TW"},
    }


# =========================================
# Markdown Processing
# =========================================

class MarkdownProcessor:
    """Process Markdown files with extensions"""

    def __init__(self):
        self.md = markdown.Markdown(
            extensions=[
                'tables',
                'toc',
                'fenced_code',
                'nl2br',
                'sane_lists',
            ],
            extension_configs={
                'toc': {
                    'title': '目錄',
                    'toc_depth': 3,
                },
            }
        )

    def convert(self, text: str) -> dict:
        """Convert markdown to HTML and extract metadata"""
        self.md.reset()

        # Extract YAML frontmatter if present
        frontmatter = {}
        content = text

        if text.startswith('---'):
            parts = text.split('---', 2)
            if len(parts) >= 3:
                if yaml:
                    try:
                        frontmatter = yaml.safe_load(parts[1]) or {}
                    except yaml.YAMLError:
                        pass
                content = parts[2].strip()

        # Convert markdown
        html = self.md.convert(content)

        # Post-process: add chart attributes to tables based on context
        html = self._enhance_tables(html)

        return {
            'html': html,
            'toc': self.md.toc,
            'frontmatter': frontmatter,
        }

    def _enhance_tables(self, html: str) -> str:
        """Add chart visualization hints to tables based on preceding heading"""
        import re

        # Patterns to detect chart type from heading text
        chart_patterns = [
            (r'Top\s*\d+|排名|Ranking', 'bar'),
            (r'分布|Distribution|佔比|比例', 'donut'),
            (r'矩陣|Matrix|熱力|Heatmap', 'heatmap'),
            (r'Top|前\s*\d+|成分|Ingredient', 'bar'),  # default patterns
        ]

        # Find all tables and their positions
        table_positions = [(m.start(), m.end()) for m in re.finditer(r'<table', html)]

        if not table_positions:
            return html

        # Find all headings and their positions
        heading_pattern = r'<h[2-4][^>]*>([^<]+)</h[2-4]>'
        headings = [(m.start(), m.end(), m.group(1)) for m in re.finditer(heading_pattern, html)]

        # For each table, find the closest preceding heading
        modifications = []
        for table_start, table_end in table_positions:
            # Find the closest heading before this table
            closest_heading = None
            for h_start, h_end, h_text in headings:
                if h_end < table_start:
                    closest_heading = (h_start, h_end, h_text)
                else:
                    break

            if not closest_heading:
                continue

            h_start, h_end, heading_text = closest_heading

            # Determine chart type
            chart_type = None
            for pattern, ctype in chart_patterns:
                if re.search(pattern, heading_text, re.IGNORECASE):
                    chart_type = ctype
                    break

            if chart_type:
                # Store modification: position and new text
                new_table = f'<table data-chart="{chart_type}" data-chart-title="{heading_text.strip()}"'
                modifications.append((table_start, table_start + 6, new_table))

        # Apply modifications in reverse order to preserve positions
        result = html
        for start, end, new_text in reversed(modifications):
            result = result[:start] + new_text + result[end:]

        return result


# =========================================
# Report Parser
# =========================================

class ReportParser:
    """Parse report files and extract metadata"""

    # Pattern for report filenames: YYYY-Www or YYYY-MM format
    DATE_PATTERNS = [
        (r'(\d{4})-W(\d{2})', 'weekly'),  # 2026-W06
        (r'(\d{4})-(\d{2})', 'monthly'),   # 2026-02
    ]

    @staticmethod
    def parse_filename(filename: str) -> dict:
        """Extract date/period info from filename"""
        stem = Path(filename).stem

        for pattern, period_type in ReportParser.DATE_PATTERNS:
            match = re.match(pattern, stem)
            if match:
                if period_type == 'weekly':
                    year, week = match.groups()
                    return {
                        'period': f"{year}-W{week}",
                        'period_type': 'weekly',
                        'year': int(year),
                        'week': int(week),
                        'sort_key': f"{year}W{week}",
                    }
                else:
                    year, month = match.groups()
                    return {
                        'period': f"{year}-{month}",
                        'period_type': 'monthly',
                        'year': int(year),
                        'month': int(month),
                        'sort_key': f"{year}{month}",
                    }

        return {
            'period': stem,
            'period_type': 'unknown',
            'sort_key': stem,
        }

    @staticmethod
    def extract_summary(content: str, max_length: int = 200) -> str:
        """Extract summary from markdown content"""
        # Remove frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2]

        # Remove markdown formatting
        text = re.sub(r'#+ ', '', content)  # Headers
        text = re.sub(r'\*\*|\*|__|_', '', text)  # Bold/italic
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
        text = re.sub(r'```[\s\S]*?```', '', text)  # Code blocks
        text = re.sub(r'`[^`]+`', '', text)  # Inline code
        text = re.sub(r'\|[^\n]+\|', '', text)  # Tables
        text = re.sub(r'\n+', ' ', text)  # Newlines

        # Get first meaningful paragraph
        text = text.strip()
        if len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0] + '...'

        return text

    @staticmethod
    def extract_data_sources(content: str) -> list:
        """Extract data source references from content"""
        sources = []
        flags = {'🇺🇸': 'us', '🇨🇦': 'ca', '🇰🇷': 'kr', '🇯🇵': 'jp', '🇹🇼': 'tw'}

        for flag, code in flags.items():
            if flag in content:
                sources.append({
                    'code': code,
                    'flag': flag,
                    'name': Config.MARKETS[code]['name'],
                })

        return sources


# =========================================
# HTML Builder
# =========================================

class HTMLBuilder:
    """Build HTML from templates and markdown"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.md_processor = MarkdownProcessor()

        # Setup Jinja2
        self.env = Environment(
            loader=FileSystemLoader(str(Config.TEMPLATE_DIR)),
            autoescape=select_autoescape(['html', 'xml']),
        )

        # Add custom filters
        self.env.filters['truncate'] = self._truncate

    def _truncate(self, s: str, length: int = 50) -> str:
        """Truncate string with ellipsis"""
        if len(s) <= length:
            return s
        return s[:length].rsplit(' ', 1)[0] + '...'

    def _log(self, msg: str):
        """Log message if verbose"""
        if self.verbose:
            print(f"  {msg}")

    def build_all(self):
        """Build all HTML files"""
        print("Building HTML reports...")

        # Ensure output directory exists
        Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Copy assets
        self._copy_assets()

        # Discover and process reports
        reports = self._discover_reports()

        # Store for navigation purposes
        self._all_reports = reports

        # Build individual report pages
        for report in reports:
            self._build_report(report)

        # Build index page
        self._build_index(reports)

        # Build compare page
        self._build_compare(reports)

        # Build search index
        self._build_search_index(reports)

        print(f"Done! Built {len(reports)} reports to {Config.OUTPUT_DIR}")

    def _copy_assets(self):
        """Copy static assets to output"""
        self._log("Copying assets...")

        output_assets = Config.OUTPUT_DIR / "assets"

        # Remove existing assets
        if output_assets.exists():
            shutil.rmtree(output_assets)

        # Copy from templates
        shutil.copytree(Config.ASSETS_DIR, output_assets)

    def _discover_reports(self) -> list:
        """Discover all report markdown files"""
        self._log("Discovering reports...")

        reports = []

        if not Config.NARRATOR_DIR.exists():
            print(f"Warning: {Config.NARRATOR_DIR} does not exist")
            return reports

        for mode_dir in Config.NARRATOR_DIR.iterdir():
            if not mode_dir.is_dir():
                continue

            mode_name = mode_dir.name
            mode_info = Config.MODE_NAMES.get(mode_name, {
                'display': mode_name,
                'icon': '📄',
                'frequency': '',
            })

            for md_file in mode_dir.glob('*.md'):
                file_info = ReportParser.parse_filename(md_file.name)
                content = md_file.read_text(encoding='utf-8')

                reports.append({
                    'path': f"{mode_name}/{md_file.stem}",
                    'file': md_file,
                    'mode': mode_name,
                    'mode_display': mode_info['display'],
                    'mode_icon': mode_info['icon'],
                    'mode_frequency': mode_info['frequency'],
                    'period': file_info['period'],
                    'period_type': file_info['period_type'],
                    'sort_key': file_info['sort_key'],
                    'content': content,
                    'summary': ReportParser.extract_summary(content),
                    'data_sources': ReportParser.extract_data_sources(content),
                    'mtime': md_file.stat().st_mtime,
                })

        # Sort by mode, then by sort_key descending
        reports.sort(key=lambda r: (r['mode'], r['sort_key']), reverse=True)

        self._log(f"Found {len(reports)} reports")
        return reports

    def _build_report(self, report: dict):
        """Build single report HTML"""
        self._log(f"Building {report['path']}...")

        # Convert markdown
        result = self.md_processor.convert(report['content'])

        # Determine navigation
        same_mode = [r for r in self._all_reports if r['mode'] == report['mode']]
        same_mode.sort(key=lambda r: r['sort_key'])

        idx = next((i for i, r in enumerate(same_mode) if r['path'] == report['path']), -1)
        prev_report = same_mode[idx - 1] if idx > 0 else None
        next_report = same_mode[idx + 1] if idx < len(same_mode) - 1 else None

        # Prepare template context
        context = {
            'title': f"{report['mode_display']} {report['period']}",
            'description': report['summary'],
            'assets_path': '../assets',
            'root_path': '..',
            'generation_date': datetime.now().strftime('%Y-%m-%d'),
            'mode': report['mode'],
            'mode_display_name': report['mode_display'],
            'report_period': report['period'],
            'data_sources': report['data_sources'],
            'current_report_path': report['path'],
            'content': result['html'],
            'toc': result['toc'],
            'prev_report': {
                'path': prev_report['path'],
                'title': f"{prev_report['mode_display']} {prev_report['period']}",
                'url': f"../{prev_report['path']}.html",
            } if prev_report else None,
            'next_report': {
                'path': next_report['path'],
                'title': f"{next_report['mode_display']} {next_report['period']}",
                'url': f"../{next_report['path']}.html",
            } if next_report else None,
        }

        # Render template
        template = self.env.get_template('report.html')
        html = template.render(**context)

        # Write output
        output_path = Config.OUTPUT_DIR / f"{report['path']}.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding='utf-8')

    def _build_index(self, reports: list):
        """Build index page"""
        self._log("Building index page...")

        # Store for navigation
        self._all_reports = reports

        # Group by mode
        modes = {}
        for report in reports:
            mode = report['mode']
            if mode not in modes:
                modes[mode] = {
                    'name': mode,
                    'display_name': report['mode_display'],
                    'icon': report['mode_icon'],
                    'frequency': report['mode_frequency'],
                    'reports': [],
                }
            modes[mode]['reports'].append({
                'path': report['path'],
                'period': report['period'],
                'title': f"{report['mode_display']} {report['period']}",
                'date': datetime.fromtimestamp(report['mtime']).strftime('%Y-%m-%d'),
                'summary': report['summary'],
                'url': f"{report['path']}.html",
            })

        # Sort reports within each mode by sort_key descending
        for mode in modes.values():
            mode['reports'].sort(
                key=lambda r: r['period'],
                reverse=True
            )

        # Get latest reports (one per mode)
        latest_reports = []
        for mode in modes.values():
            if mode['reports']:
                r = mode['reports'][0]
                latest_reports.append({
                    'icon': mode['icon'],
                    'title': r['title'],
                    'description': r['summary'],
                    'date': r['date'],
                    'url': r['url'],
                    'mode_display': mode['display_name'],
                    'data_sources': [],
                })

        # Calculate stats
        stats = {
            'total_reports': len(reports),
            'modes_count': len(modes),
            'latest_date': max(r['date'] for m in modes.values() for r in m['reports']) if reports else '-',
            'markets_count': 5,
        }

        # Prepare context
        context = {
            'title': '報告索引',
            'assets_path': 'assets',
            'root_path': '.',
            'generation_date': datetime.now().strftime('%Y-%m-%d'),
            'stats': stats,
            'latest_reports': latest_reports,
            'modes': list(modes.values()),
        }

        # Render
        template = self.env.get_template('index.html')
        html = template.render(**context)

        # Write
        output_path = Config.OUTPUT_DIR / "index.html"
        output_path.write_text(html, encoding='utf-8')

    def _build_compare(self, reports: list):
        """Build compare page"""
        self._log("Building compare page...")

        # Group by mode for selection
        modes = {}
        for report in reports:
            mode = report['mode']
            if mode not in modes:
                modes[mode] = {
                    'name': mode,
                    'display_name': report['mode_display'],
                    'reports': [],
                }
            modes[mode]['reports'].append({
                'path': report['path'],
                'period': report['period'],
                'title': f"{report['mode_display']} {report['period']}",
            })

        context = {
            'title': '報告比較',
            'assets_path': 'assets',
            'root_path': '.',
            'generation_date': datetime.now().strftime('%Y-%m-%d'),
            'modes': list(modes.values()),
        }

        template = self.env.get_template('compare.html')
        html = template.render(**context)

        output_path = Config.OUTPUT_DIR / "compare.html"
        output_path.write_text(html, encoding='utf-8')

    def _build_search_index(self, reports: list):
        """Build search index JSON"""
        self._log("Building search index...")

        index = []
        for report in reports:
            # Extract highlights (key data points)
            highlights = self._extract_highlights(report['content'])

            index.append({
                'id': report['path'],
                'title': f"{report['mode_display']} {report['period']}",
                'mode': report['mode'],
                'date': datetime.fromtimestamp(report['mtime']).strftime('%Y-%m-%d'),
                'content': self._clean_for_search(report['content']),
                'highlights': highlights,
            })

        output_path = Config.OUTPUT_DIR / "search-index.json"
        output_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    def _extract_highlights(self, content: str) -> list:
        """Extract key highlights from content"""
        highlights = []

        # Look for numbers with context
        patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*(筆|個|種|項|產品)',
            r'([\d.]+)%',
            r'Top\s*\d+[：:]\s*([^\n]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches[:3]:
                if isinstance(match, tuple):
                    highlights.append(' '.join(match))
                else:
                    highlights.append(match)

        return highlights[:5]

    def _clean_for_search(self, content: str) -> str:
        """Clean content for search indexing"""
        # Remove frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2]

        # Remove markdown formatting but keep text
        content = re.sub(r'```[\s\S]*?```', '', content)
        content = re.sub(r'`[^`]+`', '', content)
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        content = re.sub(r'#+ ', '', content)
        content = re.sub(r'\*\*|\*|__|_', '', content)
        content = re.sub(r'\|', ' ', content)
        content = re.sub(r'-{3,}', '', content)
        content = re.sub(r'\n+', ' ', content)
        content = re.sub(r'\s+', ' ', content)

        # Truncate for reasonable index size
        return content.strip()[:2000]

    def clean(self):
        """Clean output directory"""
        print(f"Cleaning {Config.OUTPUT_DIR}...")
        if Config.OUTPUT_DIR.exists():
            shutil.rmtree(Config.OUTPUT_DIR)
        print("Done!")


# =========================================
# Watch Mode
# =========================================

def watch_mode(builder: HTMLBuilder):
    """Watch for file changes and rebuild"""
    print("Watching for changes... (Ctrl+C to stop)")

    last_build = 0

    try:
        while True:
            # Check for changes
            latest_mtime = 0

            # Check templates
            for f in Config.TEMPLATE_DIR.rglob('*'):
                if f.is_file():
                    latest_mtime = max(latest_mtime, f.stat().st_mtime)

            # Check source files
            if Config.NARRATOR_DIR.exists():
                for f in Config.NARRATOR_DIR.rglob('*.md'):
                    latest_mtime = max(latest_mtime, f.stat().st_mtime)

            # Rebuild if changed
            if latest_mtime > last_build:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Changes detected, rebuilding...")
                builder.build_all()
                last_build = time.time()

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopped watching.")


# =========================================
# Main
# =========================================

def main():
    parser = argparse.ArgumentParser(
        description='Build HTML reports from Narrator markdown files'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean output directory before building'
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Watch for changes and rebuild automatically'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    builder = HTMLBuilder(verbose=args.verbose)

    if args.clean:
        builder.clean()

    if args.watch:
        builder.build_all()
        watch_mode(builder)
    else:
        builder.build_all()


if __name__ == '__main__':
    main()
