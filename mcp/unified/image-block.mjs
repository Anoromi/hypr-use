// Screenshot bytes can be PNG or JPEG; the MIME type must follow the bytes.
export function imageBlock(value) {
  const source = value?.bytes ?? value;
  if (!ArrayBuffer.isView(source)) throw Error('emitImage expects image bytes');
  const bytes = Buffer.from(source.buffer, source.byteOffset, source.byteLength);
  let mimeType;
  if (bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) mimeType='image/png';
  else if (bytes[0]===255 && bytes[1]===216 && bytes[2]===255) mimeType='image/jpeg';
  else throw Error('emitImage supports PNG or JPEG image bytes');
  if (value?.mimeType && value.mimeType!==mimeType) throw Error('Image MIME type does not match its bytes');
  return {type:'image',mimeType,data:bytes.toString('base64')};
}
