#!/usr/bin/env python3
"""
Generate sitemap.xml from built dist directory
"""
import os
from pathlib import Path
from datetime import datetime

dist_dir = Path('./dist')
base_url = 'https://modeme-automobiles-web.local'

# Find all index.html files in dist
pages = []
for root, dirs, files in os.walk(dist_dir):
    if 'index.html' in files:
        rel_path = os.path.relpath(root, dist_dir)
        if rel_path == '.':
            url = f'{base_url}/'
        else:
            url = f'{base_url}/{rel_path}/'
        
        # Get modification time
        html_file = os.path.join(root, 'index.html')
        mtime = os.path.getmtime(html_file)
        lastmod = datetime.fromtimestamp(mtime).isoformat()
        
        pages.append({
            'url': url,
            'lastmod': lastmod,
            'changefreq': 'weekly' if rel_path == '.' else 'monthly',
            'priority': '1.0' if rel_path == '.' else '0.8' if 'categories' in rel_path else '0.6'
        })

# Sort by priority
pages.sort(key=lambda x: x['priority'], reverse=True)

# Generate sitemap XML
sitemap_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
'''

for page in pages:
    sitemap_xml += f'''  <url>
    <loc>{page['url']}</loc>
    <lastmod>{page['lastmod']}</lastmod>
    <changefreq>{page['changefreq']}</changefreq>
    <priority>{page['priority']}</priority>
  </url>
'''

sitemap_xml += '</urlset>'

# Write sitemap
sitemap_path = dist_dir / 'sitemap.xml'
sitemap_path.write_text(sitemap_xml)

print(f'Generated sitemap with {len(pages)} URLs')
print(f'Sitemap saved to: {sitemap_path}')
