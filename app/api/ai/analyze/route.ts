import {localAI,limitedJson} from '@/lib/server/local-ai';
export const runtime='nodejs';
export async function POST(request:Request){try{return localAI('/analyze','POST',await limitedJson(request))}catch(e){return Response.json({detail:e instanceof Error?e.message:'Invalid image.'},{status:400})}}
