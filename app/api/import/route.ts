import {NextResponse} from 'next/server';
import {fetchPublic,parseProduct,ImportFailure} from '@/lib/server/product-import';
export const runtime='nodejs';
export async function POST(request:Request){
 try{if(request.headers.get('origin')&&new URL(request.headers.get('origin')!).host!==request.headers.get('host'))return NextResponse.json({error:'Invalid request origin.'},{status:403});const input=await request.json();if(typeof input.url!=='string'||input.url.length>4096)return NextResponse.json({error:'Enter a product link.'},{status:400});
 const fetched=await fetchPublic(input.url,10*1024*1024);let product;
 if(['image/jpeg','image/png','image/webp'].includes(fetched.type))product={name:'Imported clothing image',category:'Top',images:[fetched.url],originalUrl:input.url,colour:'Not specified'};
 else if(['text/html','application/xhtml+xml'].includes(fetched.type))product=parseProduct(fetched.body.toString('utf8'),fetched.url);
 else throw new ImportFailure('This URL does not provide a clothing page or supported image.');
 return NextResponse.json({product},{headers:{'Cache-Control':'no-store'}});
 }catch(e){return NextResponse.json({error:e instanceof ImportFailure?e.message:'Could not read this retailer. Upload a clothing image or screenshot instead.'},{status:e instanceof ImportFailure?e.status:422})}
}
