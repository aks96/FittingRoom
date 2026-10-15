import YourFittingRoom from '@/components/YourFittingRoom';
import DownloadLanding from '@/components/DownloadLanding';
export default function Page(){return process.env.NEXT_PUBLIC_BUNDLED_WORKSPACE==='1'?<YourFittingRoom/>:<DownloadLanding/>}
