import categoriesData from '../data/categories.json';

type CategoryEntry = { name: string; slug: string };
const data = categoriesData as Record<string, CategoryEntry>;

const nameToSlug: Record<string, string> = {};
for (const id in data) {
  nameToSlug[data[id].name] = data[id].slug;
}

// Canonical slug for a category name, falling back to a derived slug
// if the name isn't found in categories.json (shouldn't normally happen).
export function categorySlug(name: string): string {
  if (nameToSlug[name]) return nameToSlug[name];
  return name.toLowerCase().trim().replace(/\s+/g, '-').replace(/[|&]/g, '');
}

export function allCategoryNames(): string[] {
  return Object.values(data).map((c) => c.name);
}
