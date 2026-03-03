import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { LayoutDashboard, Sparkles, BookOpen } from "lucide-react";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "B2B Proposal Architect — AI Squad",
    description: "Autonomous multi-agent system for generating high-performance B2B proposals.",
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en" className="dark scroll-smooth">
            <body className={`${inter.className} min-h-screen bg-[#020617] selection:bg-blue-500/30`}>
                {/* Background Gradients */}
                <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
                    <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/10 blur-[120px] rounded-full" />
                    <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-600/10 blur-[120px] rounded-full" />
                </div>

                {/* Header */}
                <header className="fixed top-0 left-0 right-0 z-50 border-b border-slate-800/60 bg-[#020617]/80 backdrop-blur-md">
                    <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl shadow-lg shadow-blue-500/20 flex items-center justify-center">
                                <Sparkles className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h1 className="text-base font-black text-white tracking-tight uppercase">
                                    Architect <span className="text-blue-500">B2B</span>
                                </h1>
                                <div className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">
                                        4-Agent AI Engine Online
                                    </span>
                                </div>
                            </div>
                        </div>

                        <nav className="hidden md:flex items-center gap-8">
                            <a href="#" className="text-xs font-bold text-slate-400 hover:text-white transition-colors flex items-center gap-2">
                                <LayoutDashboard className="w-4 h-4" />
                                DASHBOARD
                            </a>
                            <a href="#" className="text-xs font-bold text-slate-400 hover:text-white transition-colors flex items-center gap-2">
                                <BookOpen className="w-4 h-4" />
                                DOCUMENTATION
                            </a>
                        </nav>

                        <div className="flex items-center gap-4">
                            <div className="hidden lg:block h-8 w-[1px] bg-slate-800" />
                            <div className="text-[10px] font-mono font-bold text-slate-500 text-right leading-tight">
                                v1.0.4-BETA<br />
                                CHROMA · LANGGRAPH
                            </div>
                        </div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="max-w-7xl mx-auto px-6 pt-24 pb-20">
                    {children}
                </main>

                <footer className="border-t border-slate-900/50 bg-[#020617]/50 py-10">
                    <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
                        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                            © 2026 Architect B2B Proposal Generator
                        </div>
                        <div className="flex gap-6">
                            <div className="text-[10px] font-bold text-slate-600">PRIVARY STACK: LOCAL EMBEDDINGS</div>
                            <div className="text-[10px] font-bold text-slate-600">PROVIDER: OPENROUTER / LLAMA 3</div>
                        </div>
                    </div>
                </footer>
            </body>
        </html>
    );
}
