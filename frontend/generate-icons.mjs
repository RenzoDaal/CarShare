import { Resvg } from '@resvg/resvg-js';
import { readFileSync, writeFileSync } from 'fs';

const svg = readFileSync('./public/favicon.svg', 'utf-8');

const sizes = [
  { name: 'apple-touch-icon-180x180.png', size: 180 },
  { name: 'pwa-64x64.png', size: 64 },
  { name: 'pwa-192x192.png', size: 192 },
  { name: 'pwa-512x512.png', size: 512 },
  { name: 'maskable-icon-512x512.png', size: 512 },
];

for (const { name, size } of sizes) {
  const resvg = new Resvg(svg, {
    fitTo: { mode: 'width', value: size },
    background: '#10b981',
  });
  const png = resvg.render().asPng();
  writeFileSync(`./public/${name}`, png);
  console.log(`✓ ${name}`);
}
