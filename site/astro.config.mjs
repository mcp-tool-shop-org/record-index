// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: 'https://mcp-tool-shop-org.github.io',
  base: '/record-index',
  integrations: [
    starlight({
      title: 'record-index',
      description: 'Query the record instead of reading it — the handbook.',
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/mcp-tool-shop-org/record-index' },
      ],
      // armature's shape, not facet's. Starlight 0.39.0 REMOVED the
      // `{ label, autogenerate }` shorthand facet's config still uses; on 0.41
      // it is a hard config error rather than a deprecation warning, so the
      // autogenerate config sits inside an `items` array.
      sidebar: [
        {
          label: 'Handbook',
          items: [{ autogenerate: { directory: 'handbook' } }],
        },
      ],
      // site-theme's BaseLayout.astro hardcodes `<link rel="icon"
      // href="{base}favicon.svg">` with no prop and no head slot, so a repo on
      // the theme that ships no favicon.svg serves a 404 for it. This one ships
      // one.
      favicon: '/favicon.svg',
      customCss: ['./src/styles/starlight-custom.css'],
      disable404Route: true,
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
  },
});
