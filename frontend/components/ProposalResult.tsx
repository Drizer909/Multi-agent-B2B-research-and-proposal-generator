"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ProposalResult as ProposalResultType } from "@/lib/api";
import { Briefcase, BarChart3, Hash, ShieldCheck, Clock } from "lucide-react";

interface Props {
    result: ProposalResultType;
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
                    <div key={stat.label} className="card relative min-w-0 overflow-hidden p-4 sm:p-6 group">
                        <div className={`absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity ${stat.color}`}>
                            <stat.icon className="w-16 h-16" />
                        </div>
                        <div className="relative flex flex-col items-center text-center">
                            <div className="text-[10px] uppercase font-black text-slate-500 tracking-widest mb-2">{stat.label}</div>
                            <div className={`w-full text-xl font-mono font-black [overflow-wrap:anywhere] sm:text-2xl ${stat.color}`}>{stat.value}</div>
                        </div>
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Column: Context & Pain Points */}
                <div className="min-w-0 space-y-6 lg:col-span-1">
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
                                <div key={i} className="flex items-start gap-3 rounded-lg border border-slate-700/50 bg-slate-900/50 p-3 text-xs font-medium leading-relaxed text-slate-300">
                                    <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
                                    <span className="min-w-0 [overflow-wrap:anywhere]">{pp}</span>
                                </div>
                            ))}
                            {!result.pain_points?.length && <div className="text-slate-500 text-xs italic">No specific pain points were flagged.</div>}
                        </div>
                    </div>

                    {/* Strategic Fit Card */}
                    <div className="card border-blue-500/10">
                        <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4">Strategic Summary</h3>
                        <div className="text-xs leading-relaxed text-slate-400 [overflow-wrap:anywhere]">
                            The proposal highlights <span className="text-blue-400 font-bold">{result.company_name}</span>'s potential for workflow optimization using our core solutions.
                            The Analysis Agent identified high alignment in the <span className="text-white font-bold">{result.industry}</span> sector.
                        </div>
                    </div>
                </div>

                {/* Right Column: Proposal Draft */}
                <div className="min-w-0 lg:col-span-2">
                    <div className="card bg-slate-950/40 p-4 sm:p-6 lg:p-10">
                        <div className="mb-4 flex items-center justify-end gap-2">
                            <span className="w-2 h-2 rounded-full bg-green-500" />
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Verified Content</span>
                        </div>
                        <article className="prose-proposal text-sm leading-relaxed [overflow-wrap:anywhere] sm:text-base">
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                skipHtml
                                components={{
                                    table: ({ children }) => (
                                        <div className="overflow-x-auto">
                                            <table>{children}</table>
                                        </div>
                                    ),
                                }}
                            >
                                {proposal}
                            </ReactMarkdown>
                        </article>
                    </div>
                </div>
            </div>
        </div>
    );
}
