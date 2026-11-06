import { defineCollection, z } from 'astro:content';

const posts = defineCollection({
  type: 'content',
  schema: z.any(),
});

export const collections = {
  posts,
};
