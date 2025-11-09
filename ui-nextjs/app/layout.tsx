import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { ApiProvider } from '@/contexts/ApiContext';
import 'leaflet/dist/leaflet.css';


const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Singapore Haze Prediction Dashboard',
  description: 'Real-time haze forecasting system for Singapore government dashboard',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ApiProvider>{children}</ApiProvider>
      </body>
    </html>
  );
}

