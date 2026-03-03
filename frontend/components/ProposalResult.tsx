"use client";

import type { ProposalResult as ProposalResultType } from "@/lib/api";
import { Briefcase, BarChart3, Hash, ShieldCheck, Clock } from "lucide-react";

interface Props {
    result: ProposalResultType;
}

function renderMarkdown(md: string): string {
    // Enhanced micro-parser for proposal rendering
    let html = md
        .replace(/^### (.+)$/gm, '<h3 class="text-lg font-bold text-slate-200 mt-6 mb-3">$1</h3>')
        .replace(/^## (.+)$/gm, '<h2 class="text-xl font-bold text-blue-400 mt-8 mb-4 border-l-4 border-blue-600 pl-4">$1</h2>')
        .replace(/^# (.+)$/gm, '<h1 class="text-3xl font-black text-white mt-12 mb-8 pb-4 border-b-2 border-slate-800">$1</h1>')
        .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white font-bold bg-blue-500/10 px-1 rounded">$1</strong>')
        .replace(/\*(.+?)\*/g, '<em class="italic text-slate-400">$1</em>')
        .replace(/^- (.+)$/gm, '<li class="flex items-baseline gap-3 text-slate-300 mb-2"><span class="w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0" />$1</li>')
        .replace(/^---$/gm, '<hr class="border-slate-800 my-10">')
        .replace(/\n\n/g, "</p><p class='text-slate-300 mb-5 leading-relaxed'>")
        .replace(/\n/g, "<br>");

    return `<div class='space-y-4'><p class='text-slate-300 mb-5 leading-relaxed'>${html}</p></div>`;
}

export default function ProposalResult({ result }: Props) {
    const proposal = result.final_proposal || result.proposal_draft;

    const stats = [
        { label: "Industry", value: result.industry || "General", icon: Briefcase, color: "text-blue-400" },
        { label: "QA Score", value: `${(result.qa_score * 100).toFixed(0)}%`, icon: ShieldCheck, color: result.qa_score >= 0.9 ? "text-green-400" : "text-yellow-400" },
        { label: "Revisions", value: result.revision_count, icon: Hash, color: "text-indigo-400" },
        { label: "Pipeline Time", value: result.started_at ? `${Math.floor((new Date(result.completed_at).getTime() - new Date(result.started_at).getTime()) / 1000)}s` : "N/A", icon: Clock, color: "text-cyan-400" },
    ];

    return (
        <div className="space-y-8 animate-in fade-in duration-1000 slide-in-from-bottom-5">
            {/* Stats Dashboard */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {stats.map((stat) => (
                    <div key={stat.label} className="card py-6 relative overflow-hidden group">
                        <div className={`absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity ${stat.color}`}>
                            <stat.icon className="w-16 h-16" />
                        </div>
                        <div className="flex flex-col items-center">
                            <div className="text-[10px] uppercase font-black text-slate-500 tracking-widest mb-2">{stat.label}</div>
                            <div className={`text-2xl font-mono font-black ${stat.color}`}>{stat.value}</div>
                        </div>
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Column: Context & Pain Points */}
                <div className="lg:col-span-1 space-y-6">
                    {/* Pain Points Card */}
                    <div className="card border-red-500/10 h-fit">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="p-2 rounded-lg bg-red-400/10 text-red-400">
                                <BarChart3 className="w-5 h-5" />
                            </div>
                            <h3 className="text-sm font-black text-white uppercase tracking-wider">Identified Pain Points</h3>
                        </div>
                        <div className="space-y-3">
                            {result.pain_points?.map((pp, i) => (
                                <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-slate-900/50 border border-slate-700/50 text-xs text-slate-300 font-medium">
                                    <div className="w-1.5 h-1.5 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
                                    {pp}
                                </div>
                            ))}
                            {!result.pain_points?.length && <div className="text-slate-500 text-xs italic">No specific pain points were flagged.</div>}
                        </div>
                    </div>

                    {/* Strategic Fit Card */}
                    <div className="card border-blue-500/10">
                        <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4">Strategic Summary</h3>
                        <div className="text-xs leading-relaxed text-slate-400">
                            The proposal highlights <span className="text-blue-400 font-bold">{result.company_name}</span>'s potential for workflow optimization using our core solutions.
                            The Analysis Agent identified high alignment in the <span className="text-white font-bold">{result.industry}</span> sector.
                        </div>
                    </div>
                </div>

                {/* Right Column: Proposal Draft */}
                <div className="lg:col-span-2">
                    <div className="card bg-slate-950/40 p-10 relative">
                        <div className="absolute top-6 right-6 flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-green-500" />
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Verified Content</span>
                        </div>
                        <div
                            className="prose-proposal prose-invert max-w-none scroll-smooth"
                            dangerouslySetInnerHTML={{ __html: renderMarkdown(proposal) }}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
