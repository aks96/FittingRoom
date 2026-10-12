// Use only to withdraw an existing hosted preview with explicit user authorization.
// Preserves the local Next.js app, companion, model weights, and source files.
import fs from 'node:fs/promises';
import path from 'node:path';
const output=path.resolve('dist');
await fs.rm(output,{recursive:true,force:true});
await fs.mkdir(path.join(output,'server'),{recursive:true});
await fs.mkdir(path.join(output,'.openai'),{recursive:true});
await fs.copyFile('hosting/offline-worker.mjs',path.join(output,'server/index.js'));
await fs.copyFile('.openai/hosting.json',path.join(output,'.openai/hosting.json'));
console.log('Withdrawal artifact built: all hosted application routes return 503. Local app files retained.');
