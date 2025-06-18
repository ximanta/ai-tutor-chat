import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/client/ThemeProvider";
import { Header } from "@/components/server/Header";

export const metadata: Metadata = {
  title: {
    default: "COO AI Tutor",
    template: "%s | COO AI Tutor",
  },
  description: "Class of One AI Tutor",
};
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>        
      <body suppressHydrationWarning>     
         <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange>
         <Header />
        <div>{children}</div>       
      </ThemeProvider>
       </body>
    </html>
  );
}
