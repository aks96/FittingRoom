import {NextResponse} from 'next/server';
import {fetchPublic,ImportFailure} from '@/lib/server/product-import';
export const runtime='nodejs';
export async function GET(request:Request){try{const url=new URL(request.url).searchParams.get('url');if(!url)throw new ImportFailure('Image URL required.',400);const image=await fetchPublic(url,10*1024*1024);if(!['image/jpeg','image/png','image/webp'].includes(image.type))throw new ImportFailure('The retailer did not return a JPG, PNG or WebP image.');return new Response(new Uint8Array(image.body),{headers:{'Content-Type':image.type,'Cache-Control':'private, max-age=300','X-Content-Type-Options':'nosniff'}})}catch(e){return NextResponse.json({error:e instanceof Error?e.message:'Could not load image.'},{status:422})}}
