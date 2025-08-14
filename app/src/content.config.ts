// src/content/config.ts
import { defineCollection, z } from 'astro:content';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

const docsCollection = defineCollection({ loader: docsLoader(), schema: docsSchema() });

export const collections = {
  docs: docsCollection,
};
