import type { Metadata } from "next";
import { Bodoni_Moda, Hanken_Grotesk } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const display = Bodoni_Moda({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600", "700", "800"],
  style: ["normal", "italic"],
});

const body = Hanken_Grotesk({
  subsets: ["latin"],
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "O Guarda-Roupa · Muri",
  description: "Closet digital — acervo, looks e busca.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body
        className={`${display.variable} ${body.variable} min-h-full antialiased`}
      >
        {children}
        <Toaster position="top-center" />
      </body>
    </html>
  );
}
