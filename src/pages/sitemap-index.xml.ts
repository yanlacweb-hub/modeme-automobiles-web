import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import { categorySlug } from '../utils/categories';

const SITE = 'https://modeme-automobiles.com';

export const GET: APIRoute = async () => {
  const posts = await getCollection('posts');

  const categories = new Set<string>();
  posts.forEach((post) => {
    (post.data.categories || []).forEach((cat: string) => categories.add(cat));
  });

  const urls: { loc: string; lastmod?: string; priority: string }[] = [
    { loc: `${SITE}/`, priority: '1.0' },
    { loc: `${SITE}/articles/`, priority: '0.7' },
  ];

  for (const cat of categories) {
    urls.push({ loc: `${SITE}/category/${categorySlug(cat)}/`, priority: '0.7' });
  }

  for (const post of posts) {
    urls.push({
      loc: `${SITE}/${post.data.postSlug}/`,
      lastmod: (post.data.updatedDate || post.data.pubDate || '').toString().slice(0, 10) || undefined,
      priority: '0.6',
    });
  }

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls
  .map(
    (u) => `  <url>
    <loc>${u.loc}</loc>${u.lastmod ? `\n    <lastmod>${u.lastmod}</lastmod>` : ''}
    <priority>${u.priority}</priority>
  </url>`
  )
  .join('\n')}
</urlset>
`;

  return new Response(body, {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
};
