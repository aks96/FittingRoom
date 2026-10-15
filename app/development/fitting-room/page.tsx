import {headers} from 'next/headers';
import {notFound} from 'next/navigation';
import YourFittingRoom from '@/components/YourFittingRoom';
// Preserve the full developer flow on this machine; omit it from website exports.
export default async function DeveloperFittingRoom(){
 const host=(await headers()).get('host');
 if(host!=='127.0.0.1:3000'&&host!=='localhost:3000')notFound();
 return <YourFittingRoom/>;
}
