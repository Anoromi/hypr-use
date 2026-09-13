import test from 'node:test';
import assert from 'node:assert/strict';
import {imageBlock} from './image-block.mjs';
test('JPEG bytes are emitted with JPEG MIME, including typed array slices',()=>{
 const storage=Uint8Array.from([0,255,216,255,4,0]);
 const b=imageBlock(storage.subarray(1,5));
 assert.equal(b.mimeType,'image/jpeg');assert.deepEqual([...Buffer.from(b.data,'base64')],[255,216,255,4]);
 assert.throws(()=>imageBlock({bytes:storage.subarray(1,5),mimeType:'image/png'}),/does not match/);
});
test('PNG and unsupported bytes',()=>{
 assert.equal(imageBlock(Uint8Array.from([137,80,78,71,13,10,26,10])).mimeType,'image/png');
 assert.throws(()=>imageBlock(Uint8Array.from([1,2])),/PNG or JPEG/);
});
