import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {title: 'yourFittingRoom — Your local AI fitting room', description: 'Upload your person and garment photos for an offline AI virtual try-on. Review visible details and compare style previews.'};
export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {return <html lang="en"><body>{children}</body></html>}
