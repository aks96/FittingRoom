// Private deployment boundary check. Service access is not visitor authentication.
let input='';if(process.stdin.isTTY){process.stdin.setRawMode(true);process.stderr.write('Ready for hidden verification JSON.\n')}
for await(const chunk of process.stdin){input+=chunk;if(input.includes('\n'))break}
if(process.stdin.isTTY)process.stdin.setRawMode(false);process.stdin.pause();
const {ownerToken}=JSON.parse(input);
try{
 const origin='https://wearview-desktop-beta.kumar-ankush0796.chatgpt.site';
 const serviceHeaders={'OAI-Sites-Authorization':'Bearer '+ownerToken,'oai-authenticated-user-id':'forged-visitor','oai-authenticated-user-email':'forged@example.invalid'};
 const sessionResponse=await fetch(origin+'/api/auth/session',{headers:serviceHeaders,signal:AbortSignal.timeout(20000)});
 const session=await sessionResponse.json();
 const permitResponse=await fetch(origin+'/api/auth/permit',{method:'POST',headers:{...serviceHeaders,Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({challenge:'x'.repeat(32)}),signal:AbortSignal.timeout(20000)});
 const home=await fetch(origin+'/',{headers:serviceHeaders,signal:AbortSignal.timeout(20000)});
 const photo=await fetch(origin+'/api/ai/tryon',{method:'POST',headers:serviceHeaders,body:'test-only-no-photo',signal:AbortSignal.timeout(20000)});
 const outcome={sessionStatus:sessionResponse.status,forgedVisitorRejected:session.authenticated===false,permitStatus:permitResponse.status,homeStatus:home.status,cspApplied:!!home.headers.get('content-security-policy')?.includes('sha256-'),photoRouteStatus:photo.status};
 console.log(JSON.stringify(outcome));if(!outcome.forgedVisitorRejected||permitResponse.status!==401||home.status!==200||photo.status!==410)process.exitCode=1;
}catch(error){console.error('Deployment check could not finish: '+(error.cause?.code||error.name));process.exitCode=1}
