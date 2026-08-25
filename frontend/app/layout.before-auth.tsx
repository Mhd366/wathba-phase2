import type { Metadata } from "next";
import "./globals.css";
import "./batch.css";
export const metadata:Metadata={title:"WATHBA Performance Intelligence",description:"Auditable sprint biomechanics, stage benchmarking and evidence-grounded athlete development.",icons:{icon:"/favicon.svg",shortcut:"/favicon.svg"}};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en" dir="ltr"><body>{children}</body></html>}
