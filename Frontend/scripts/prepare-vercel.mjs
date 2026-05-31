import { cpSync, mkdirSync, writeFileSync, existsSync } from 'fs';

const out = '.vercel/output';
if (existsSync(out)) { console.log('✓ already exists'); process.exit(0); }

mkdirSync(`${out}/static`, { recursive: true });
mkdirSync(`${out}/functions/index.func`, { recursive: true });

cpSync('dist/client', `${out}/static`, { recursive: true });
cpSync('dist/server', `${out}/functions/index.func`, { recursive: true });

writeFileSync(`${out}/functions/index.func/.vc-config.json`, JSON.stringify({
  runtime: 'nodejs20.x',
  handler: 'index.mjs',
  launcherType: 'Nodejs',
  shouldAddHelpers: true
}, null, 2));

writeFileSync(`${out}/config.json`, JSON.stringify({
  version: 3,
  routes: [
    { handle: 'filesystem' },
    { src: '/(.*)', dest: '/index' }
  ]
}, null, 2));

console.log('✓ .vercel/output ready');