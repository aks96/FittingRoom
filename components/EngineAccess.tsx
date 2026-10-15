
'use client';
import CompanionAccess from './CompanionAccess';
import type {LocalHealth} from '@/lib/services';
export default function EngineAccess({onHealth}:{onHealth:(health:LocalHealth|null)=>void}){return <CompanionAccess onHealth={onHealth}/>}
