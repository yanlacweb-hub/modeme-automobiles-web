#!/usr/bin/env python3
"""
WordPress to Astro migration script for modeme-automobiles.com
Fetches posts, pages, categories, and media; prepares markdown files.
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
from html import unescape
import urllib.request
import urllib.error

BASE_URL = "https://modeme-automobiles.com"
WP_API_BASE = f"{BASE_URL}/wp-json/wp/v2"
OUTPUT_DIR = Path(__file__).parent / "src" / "content"
PUBLIC_DIR = Path(__file__).parent / "public"

# Ensure directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "posts").mkdir(exist_ok=True)
(OUTPUT_DIR / "pages").mkdir(exist_ok=True)

def clean_string(s):
    """Clean HTML entities and JSON escapes in strings."""
    if not s:
        return s
    # Unescape HTML entities
    s = unescape(s)
    # Clean JSON escapes
    s = s.replace(r"\/", "/")
    return s

def fetch_json(url):
    """Fetch JSON from URL."""
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"ERROR fetching {url}: {e}", file=sys.stderr)
        return None

def fetch_all_posts():
    """Fetch all published posts via pagination."""
    posts = []
    page = 1
    while True:
        url = f"{WP_API_BASE}/posts?per_page=100&status=publish&_embed&page={page}"
        data = fetch_json(url)
        if not data or len(data) == 0:
            break
        posts.extend(data)
        print(f"Fetched posts page {page}: {len(data)} posts (total so far: {len(posts)})")
        page += 1
    return posts

def fetch_pages():
    """Fetch static pages."""
    url = f"{WP_API_BASE}/pages?per_page=100&_embed"
    return fetch_json(url) or []

def fetch_categories():
    """Fetch all categories."""
    url = f"{WP_API_BASE}/categories?per_page=100"
    return fetch_json(url) or []

def fetch_head_metadata(post_url):
    """
    Fetch SEO metadata from page's HTML head.
    Returns dict with title, description, canonical, og:*, twitter:*, and schema.
    """
    try:
        req = urllib.request.Request(post_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"WARNING: Could not fetch HTML from {post_url}: {e}", file=sys.stderr)
        return {}

    metadata = {}
    
    # Extract title
    title_match = re.search(r'<title>([^<]+)</title>', html)
    if title_match:
        metadata['title'] = clean_string(title_match.group(1))
    
    # Extract meta description
    desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html)
    if desc_match:
        metadata['description'] = clean_string(desc_match.group(1))
    
    # Extract canonical
    canonical_match = re.search(r'<link\s+rel="canonical"\s+href="([^"]*)"', html)
    if canonical_match:
        metadata['canonical'] = canonical_match.group(1)
    
    # Extract all og:* and twitter:* meta tags
    meta_tags = re.findall(r'<meta\s+(?:property|name)="((?:og|twitter):[^"]+)"\s+content="([^"]*)"', html)
    for prop, content in meta_tags:
        metadata[prop] = content
    
    # Extract Rank Math JSON-LD schema
    schema_match = re.search(
        r'<script\s+type="application/ld\+json"\s+class="rank-math-schema"[^>]*>([^<]+)</script>',
        html,
        re.DOTALL
    )
    if schema_match:
        try:
            metadata['schema'] = json.loads(schema_match.group(1))
        except:
            pass
    
    return metadata

def download_image(url, dest_path):
    """Download image to destination, return True if successful."""
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        # Skip if already exists
        if dest_path.exists():
            return True
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(dest_path, 'wb') as f:
                f.write(response.read())
        return True
    except Exception as e:
        print(f"WARNING: Could not download image {url}: {e}", file=sys.stderr)
        return False

def extract_images_from_content(content_html):
    """Extract all image URLs from HTML content."""
    urls = re.findall(r'(?:src|href)="(https://modeme-automobiles\.com/wp-content/uploads/[^"]+)"', content_html)
    return list(set(urls))

def process_post(post_data):
    """
    Process a single post:
    1. Fetch head metadata from live URL
    2. Download featured image and content images
    3. Rewrite image URLs to relative paths
    4. Return frontmatter + content
    """
    post_id = post_data['id']
    slug = post_data['slug']
    
    # Construct live URL
    live_url = f"{BASE_URL}/{slug}/"
    
    print(f"Processing post {post_id}: {slug}")
    
    # Fetch SEO metadata from HTML head
    head_meta = fetch_head_metadata(live_url)
    
    # Prepare frontmatter
    frontmatter = {
        'postSlug': slug,
        'title': clean_string(post_data.get('title', {}).get('rendered', 'Untitled')),
        'description': head_meta.get('description', ''),
        'pubDate': post_data.get('date', ''),
        'updatedDate': post_data.get('modified', ''),
        'canonical': head_meta.get('canonical', live_url),
    }
    
    # Add OG tags
    for key in ['og:title', 'og:description', 'og:image', 'og:url', 'og:type']:
        if key in head_meta:
            frontmatter[key] = head_meta[key]
    
    # Add Twitter tags
    for key in ['twitter:card', 'twitter:title', 'twitter:description', 'twitter:image']:
        if key in head_meta:
            frontmatter[key] = head_meta[key]
    
    # Add schema if present
    if 'schema' in head_meta:
        frontmatter['schema'] = head_meta['schema']
    
    # Get categories
    categories = []
    if '_embedded' in post_data and 'wp:term' in post_data['_embedded']:
        for term_group in post_data['_embedded']['wp:term']:
            for term in term_group:
                if term.get('taxonomy') == 'category':
                    categories.append(term['name'])
    frontmatter['categories'] = categories
    
    # Download featured image
    images_downloaded = 0
    if '_embedded' in post_data and 'wp:featuredmedia' in post_data['_embedded']:
        for media in post_data['_embedded']['wp:featuredmedia']:
            media_url = media.get('source_url', '')
            if media_url:
                parsed = urlparse(media_url)
                # Extract path relative to domain
                rel_path = parsed.path.replace('/wp-content/uploads/', '')
                dest = PUBLIC_DIR / 'wp-content' / 'uploads' / rel_path
                if download_image(media_url, dest):
                    images_downloaded += 1
    
    # Process content: extract and download images
    content_html = post_data.get('content', {}).get('rendered', '')
    
    # Extract images from content
    image_urls = extract_images_from_content(content_html)
    images_failed = 0
    for img_url in image_urls:
        parsed = urlparse(img_url)
        rel_path = parsed.path.replace('/wp-content/uploads/', '')
        dest = PUBLIC_DIR / 'wp-content' / 'uploads' / rel_path
        if download_image(img_url, dest):
            images_downloaded += 1
        else:
            images_failed += 1
    
    # Rewrite absolute URLs to relative in content
    content_html = content_html.replace(
        'https://modeme-automobiles.com/wp-content/uploads/',
        '/wp-content/uploads/'
    )
    
    # Fix WordPress image size attributes and srcset quirks
    # Replace sizes="auto, (max-width: 300px) 100vw, 300px" with responsive value
    content_html = re.sub(
        r'sizes="auto,\s*\(max-width:\s*300px\)\s*100vw,\s*300px"',
        'sizes="(max-width: 780px) 100vw, 780px"',
        content_html
    )
    
    return frontmatter, content_html, images_downloaded, images_failed

def generate_markdown_file(post_slug, frontmatter, content_html):
    """Generate markdown file with YAML frontmatter."""
    fm_yaml = '---\n'
    for key, value in frontmatter.items():
        if isinstance(value, dict) or isinstance(value, list):
            fm_yaml += f'{key}: {json.dumps(value, ensure_ascii=False)}\n'
        elif isinstance(value, str):
            # Escape quotes in strings
            escaped = value.replace('"', '\\"')
            fm_yaml += f'{key}: "{escaped}"\n'
        else:
            fm_yaml += f'{key}: {value}\n'
    fm_yaml += '---\n\n'
    
    content = fm_yaml + content_html
    
    # Write to file
    file_path = OUTPUT_DIR / 'posts' / f'{post_slug}.mdx'
    file_path.write_text(content, encoding='utf-8')
    return file_path

def main():
    print("Starting WordPress to Astro migration...")
    
    # Fetch data
    print("\n1. Fetching posts...")
    posts = fetch_all_posts()
    print(f"   Total posts: {len(posts)}")
    
    print("\n2. Fetching pages...")
    pages = fetch_pages()
    print(f"   Total pages: {len(pages)}")
    
    print("\n3. Fetching categories...")
    categories = fetch_categories()
    print(f"   Total categories: {len(categories)}")
    
    # Save categories as JSON for reference
    categories_data = {cat['id']: {'name': cat['name'], 'slug': cat['slug']} for cat in categories}
    (OUTPUT_DIR / 'categories.json').write_text(json.dumps(categories_data, indent=2, ensure_ascii=False))
    
    # Process posts
    print("\n4. Processing posts...")
    posts_success = 0
    posts_failed = 0
    images_success = 0
    images_failed = 0
    
    for i, post in enumerate(posts, 1):
        try:
            fm, content, imgs_ok, imgs_fail = process_post(post)
            generate_markdown_file(post['slug'], fm, content)
            posts_success += 1
            images_success += imgs_ok
            images_failed += imgs_fail
            
            if i % 20 == 0:
                print(f"   Processed {i}/{len(posts)} posts...")
        except Exception as e:
            print(f"   ERROR processing post {post['id']}: {e}", file=sys.stderr)
            posts_failed += 1
    
    # Process pages
    print("\n5. Processing pages...")
    for page in pages:
        try:
            fm, content, imgs_ok, imgs_fail = process_post(page)
            generate_markdown_file(page['slug'], fm, content)
            posts_success += 1
            images_success += imgs_ok
            images_failed += imgs_fail
        except Exception as e:
            print(f"   ERROR processing page {page['id']}: {e}", file=sys.stderr)
            posts_failed += 1
    
    # Summary
    print("\n" + "="*60)
    print("MIGRATION SUMMARY")
    print("="*60)
    print(f"Posts/Pages processed successfully: {posts_success}")
    print(f"Posts/Pages failed: {posts_failed}")
    print(f"Images downloaded: {images_success}")
    print(f"Images failed: {images_failed}")
    print(f"Output directory: {OUTPUT_DIR / 'posts'}")
    print("="*60)

if __name__ == '__main__':
    main()
