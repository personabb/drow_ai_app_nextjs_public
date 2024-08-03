import './globals.css';
import { ReactNode } from 'react';

export const metadata = {
  title: 'Drawing App',
  description: 'A simple drawing app using Next.js and Python backend',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}
