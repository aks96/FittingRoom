import {localAI} from '@/lib/server/local-ai';
export const runtime='nodejs';
export async function GET(){return localAI('/health')}
