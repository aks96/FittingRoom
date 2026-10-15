import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {companionDownloads,detectCompanionPlatform,downloadHref} from '../lib/companion-downloads.ts';
test('Mac and Windows buttons point to the existing exact archives and truthful metadata',async()=>{
 for(const platform of ['mac','windows'] as const){
  const item=companionDownloads[platform];const data=await readFile(new URL('../public'+downloadHref(platform),import.meta.url));
  assert.equal(data.length,item.bytes);assert.equal(createHash('sha256').update(data).digest('hex'),item.sha256);
  assert.ok(item.fileCount>0);assert.equal(item.generationAvailable,platform==='mac');
 }
 assert.match(companionDownloads.windows.filename,/windows\.zip$/);assert.equal(companionDownloads.windows.setup,'Set up.cmd');
 assert.equal(companionDownloads.windows.experimentalWorker,true);assert.equal(companionDownloads.windows.test,'Test Windows.cmd');
 assert.equal(detectCompanionPlatform('Mozilla/5.0 (Windows NT 10.0; Win64; x64)'),'windows');
 assert.equal(detectCompanionPlatform('Macintosh; Intel Mac OS X'),'mac');
});
