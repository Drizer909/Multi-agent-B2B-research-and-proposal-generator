"use client";

import { useState, useEffect } from "react";
import { exportProposal, getExportFormats } from "@/lib/api";
import { FileText, Globe, FileJson, Download, Check, AlertTriangle } from "lucide-react";

interface Props {
    proposalMarkdown: string;
    companyName: string;
}

export default function ExportPanel({ proposalMarkdown, companyName }: Props) {
    const [formats, setFormats] = useState<Record<string, boolean>>({ pdf: false, html: true, markdown: true });
    const [exporting, setExporting] = useState<string | null>(null);
    const [recentExport, setRecentExport] = useState<string | null>(null);

    useEffect(() => {
        getExportFormats().then(setFormats).catch(() => { });
    }, []);

    async function handleExport(format: "pdf" | "html" | "markdown") {
        setExporting(format);
        try {
            const blob = await exportProposal(format, proposalMarkdown, companyName);

            const ext = format === "markdown" ? "md" : format;
            const safeName = companyName.toLowerCase().replace(/[^a-z0-9]/g, "_");
            const filename = `${safeName}_proposal.${ext}`;

            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            setRecentExport(format);
            setTimeout(() => setRecentExport(null), 3000);
        } catch (err) {
            console.error(err);
        } finally {
            setExporting(null);
        }
    }

    const options = [
        { format: "pdf" as const, icon: FileText, label: "PDF Document", color: "text-red-400", bg: "hover:bg-red-400/5", border: "hover:border-red-400/30" },
        { format: "html" as const, icon: Globe, label: "Interactive HTML", color: "text-blue-400", bg: "hover:bg-blue-400/5", border: "hover:border-blue-400/30" },
        { format: "markdown" as const, icon: FileJson, label: "Markdown Source", color: "text-slate-400", bg: "hover:bg-slate-400/5", border: "hover:border-slate-400/30" },
    ];

    return (
        <div className="card border-slate-700/30 bg-slate-900/50">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        <Download className="w-5 h-5 text-blue-500" />
                        Export & Deliver
                    </h3>
                    <p className="text-xs text-slate-500 mt-1">Select your preferred format for client delivery.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {options.map((opt) => {
                    const isPdf = opt.format === "pdf";
                    const isAvailable = !isPdf || formats.pdf;
                    const isLoading = exporting === opt.format;
                    const isSuccess = recentExport === opt.format;

                    return (
                        <button
                            key={opt.format}
                            onClick={() => handleExport(opt.format)}
                            disabled={!isAvailable || isLoading}
                            className={`flex items-center gap-4 p-4 rounded-xl border border-slate-700/50 bg-slate-800/40 transition-all duration-300 group ${opt.bg} ${opt.border} ${!isAvailable ? "opacity-50 cursor-not-allowed grayscale" : "active:scale-95"
                                }`}
                        >
                            <div className={`p-3 rounded-lg bg-slate-700/50 group-hover:scale-110 transition-transform ${opt.color}`}>
                                <opt.icon className="w-6 h-6" />
                            </div>
                            <div className="text-left flex-1">
                                <div className="text-sm font-bold text-white flex items-center gap-2">
                                    {opt.label}
                                    {isSuccess && <Check className="w-4 h-4 text-green-500 animate-in fade-in zoom-in" />}
                                </div>
                                {!isAvailable && (
                                    <div className="text-[10px] text-yellow-500 font-bold flex items-center gap-1 mt-0.5 uppercase tracking-tighter">
                                        <AlertTriangle className="w-3 h-3" />
                                        Lib Missing {"->"} fallback used
                                    </div>
                                )}
                                {isAvailable && (
                                    <div className="text-[10px] text-slate-500 font-medium uppercase tracking-tighter">
                                        {isLoading ? "Generating..." : opt.format === "pdf" ? "Premium Layout" : "Clean Source"}
                                    </div>
                                )}
                            </div>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
