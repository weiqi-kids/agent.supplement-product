#!/usr/bin/env python3
"""
Analyze product data for market snapshot weekly report.
Count products by layer and category, excluding REVIEW_NEEDED.
"""

import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import json

# Define category mapping
CATEGORIES = [
    'vitamins_minerals',
    'botanicals',
    'protein_amino',
    'probiotics',
    'omega_fatty_acids',
    'specialty',
    'sports_fitness',
    'other'
]

# Define layers to analyze (product layers only)
PRODUCT_LAYERS = ['us_dsld', 'ca_lnhpd', 'kr_hff', 'jp_foshu', 'jp_fnfc', 'tw_hf']

def parse_frontmatter(content):
    """Extract frontmatter from markdown file."""
    frontmatter_pattern = r'^---\n(.*?)\n---'
    match = re.match(frontmatter_pattern, content, re.DOTALL)
    if not match:
        return {}

    frontmatter = {}
    for line in match.group(1).split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            frontmatter[key.strip()] = value.strip().strip('"').strip("'")
    return frontmatter

def is_review_needed(content):
    """Check if product has REVIEW_NEEDED marker."""
    return '[REVIEW_NEEDED]' in content[:500]  # Check first 500 chars

def count_products(base_path, layer, start_date, end_date):
    """Count products by category for a given layer within date range."""
    layer_path = Path(base_path) / 'docs/Extractor' / layer

    if not layer_path.exists():
        return {}, 0

    category_counts = defaultdict(int)
    total_count = 0
    review_needed_count = 0

    # Scan all category directories
    for category_dir in layer_path.iterdir():
        if not category_dir.is_dir():
            continue

        category = category_dir.name

        # Count .md files in this category
        for md_file in category_dir.glob('*.md'):
            try:
                content = md_file.read_text(encoding='utf-8')

                # Skip REVIEW_NEEDED products (silent exclusion)
                if is_review_needed(content):
                    review_needed_count += 1
                    continue

                # Parse frontmatter to check fetched_at date
                frontmatter = parse_frontmatter(content)
                fetched_at = frontmatter.get('fetched_at', '')

                if fetched_at:
                    # Parse date (handle both YYYY-MM-DD and ISO8601 formats)
                    try:
                        if 'T' in fetched_at:
                            fetched_date = datetime.fromisoformat(fetched_at.replace('Z', '+00:00')).date()
                        else:
                            fetched_date = datetime.strptime(fetched_at, '%Y-%m-%d').date()

                        # Check if within date range
                        if start_date <= fetched_date <= end_date:
                            category_counts[category] += 1
                            total_count += 1
                    except (ValueError, AttributeError):
                        # If date parsing fails, include it anyway
                        category_counts[category] += 1
                        total_count += 1
                else:
                    # If no fetched_at, include it
                    category_counts[category] += 1
                    total_count += 1

            except Exception as e:
                print(f"Error reading {md_file}: {e}")
                continue

    return dict(category_counts), total_count

def get_sample_products(base_path, layer, count=3):
    """Get sample product names for highlights."""
    layer_path = Path(base_path) / 'docs/Extractor' / layer

    if not layer_path.exists():
        return []

    samples = []

    # Collect samples from different categories
    for category_dir in layer_path.iterdir():
        if not category_dir.is_dir() or len(samples) >= count:
            break

        for md_file in list(category_dir.glob('*.md'))[:2]:
            if len(samples) >= count:
                break

            try:
                content = md_file.read_text(encoding='utf-8')

                # Skip REVIEW_NEEDED
                if is_review_needed(content):
                    continue

                frontmatter = parse_frontmatter(content)
                product_name = frontmatter.get('product_name', '')

                if product_name:
                    samples.append(product_name)
            except Exception:
                continue

    return samples

def main():
    base_path = Path(__file__).parent.parent

    # Calculate date range (last 7 days)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)

    print(f"Report period: {start_date} ~ {end_date}")
    print(f"Current week: {datetime.now().strftime('%Y-W%V')}")
    print()

    # Collect data for all layers
    results = {}

    for layer in PRODUCT_LAYERS:
        print(f"Analyzing {layer}...")
        category_counts, total = count_products(base_path, layer, start_date, end_date)
        samples = get_sample_products(base_path, layer)

        results[layer] = {
            'total': total,
            'categories': category_counts,
            'samples': samples
        }

        print(f"  Total: {total}")
        print(f"  Top categories: {sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]}")
        print()

    # Output JSON for consumption by report generator
    output = {
        'period': {
            'start': str(start_date),
            'end': str(end_date),
            'week': datetime.now().strftime('%Y-W%V')
        },
        'layers': results
    }

    output_file = base_path / 'scripts' / 'market_snapshot_data.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Analysis complete. Data saved to {output_file}")

    # Print summary
    total_products = sum(r['total'] for r in results.values())
    print(f"\nTotal products across all markets: {total_products}")

if __name__ == '__main__':
    main()
