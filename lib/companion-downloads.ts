import manifest from '../security/companion-downloads.json' with {type:'json'};
export type CompanionPlatform='mac'|'windows';
export const companionDownloads=manifest.packages;
export const downloadBuild=manifest.build;
export function downloadHref(platform:CompanionPlatform){return '/'+companionDownloads[platform].filename}
export function downloadSize(bytes:number){return `${(bytes/1024/1024).toFixed(1)} MB`}
export function detectCompanionPlatform(userAgent:string):CompanionPlatform{return /Windows/i.test(userAgent)?'windows':'mac'}
