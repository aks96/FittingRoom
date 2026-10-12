import {localAI,sameOrigin} from '@/lib/server/local-ai';
export const runtime='nodejs';
type Context={params:Promise<{id:string}>};
export async function GET(_request:Request,context:Context){const {id}=await context.params;if(!/^[a-f0-9]{32}$/.test(id))return Response.json({detail:'Invalid job ID'},{status:400});return localAI('/jobs/'+id)}
export async function POST(request:Request,context:Context){if(!sameOrigin(request))return Response.json({detail:'Invalid request origin'},{status:403});const {id}=await context.params;if(!/^[a-f0-9]{32}$/.test(id))return Response.json({detail:'Invalid job ID'},{status:400});return localAI('/jobs/'+id,'POST',{})}
