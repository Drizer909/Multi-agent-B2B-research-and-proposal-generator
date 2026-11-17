"use client";

import { useState, useCallback } from "react";
import ProposalForm from "@/components/ProposalForm";
import ProgressTracker from "@/components/ProgressTracker";
import ProposalResult from "@/components/ProposalResult";
import ExportPanel from "@/components/ExportPanel";
import { startProposal, getProposalResult, type ProposalResult as ProposalResultType } from "@/lib/api";
import { RefreshCw, ArrowLeft, Terminal } from "lucide-react";

type PageState = "form" | "generating" | "result" | "error";

export default function Home() {
    const [pageState, setPageState] = useState<PageState>("form");
    const [threadId, setThreadId] = useState("");
    const [result, setResult] = useState<ProposalResultType | null>(null);
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    async function handleSubmit(companyName: string, userRequest: string, requestorName: string) {
        setIsSubmitting(true);
        setError("");

        try {
            const job = await startProposal({
                company_name: companyName,
                user_request: userRequest,
                requestor_name: requestorName,
            });
            setThreadId(job.thread_id);
            setPageState("generating");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to start generation sequence");
            setPageState("error");
        } finally {
            setIsSubmitting(false);
        }
    }

    const handleComplete = useCallback(async () => {
        try {
            const data = await getProposalResult(threadId);
            setResult(data);
            setPageState("result");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to ingest final result");
            setPageState("error");
        }
    }, [threadId]);

    const handleError = useCallback((errMsg: string) => {
        setError(errMsg);
        setPageState("error");
    }, []);

    function handleReset() {
        setPageState("form");
        setThreadId("");
        setResult(null);
        setError("");
    }

    return (
        <div className="max-w-6xl mx-auto">
            {/* ─── FORM State ─── */}
            {pageState === "form" && (
                <div className="animate-in fade-in duration-700">
                    <ProposalForm onSubmit={handleSubmit} isLoading={isSubmitting} />
                </div>
            )}

            {/* ─── GENERATING State ─── */}
            {(pageState === "generating" || pageState === "error") && threadId && (
                <div className="animate-in zoom-in-95 duration-500">
                    <ProgressTracker
                        threadId={threadId}
                        onComplete={handleComplete}
                        onError={handleError}
                    />
                </div>
            )}

            {/* ─── RESULT State ─── */}
            {pageState === "result" && result && (
                <div className="space-y-10">
                    <div className="flex flex-col md:flex-row items-center justify-between gap-6 mb-4">
                        <div className="min-w-0 text-center md:text-left">
                            <h2 className="text-4xl font-black text-white mb-2 tracking-tight">
                                Proposal Ready
                            </h2>
                            <div className="flex flex-wrap items-center justify-center gap-3 md:justify-start">
                                <span className="max-w-full rounded border border-blue-500/20 bg-blue-500/10 px-3 py-1 text-xs font-bold uppercase tracking-widest text-blue-400 [overflow-wrap:anywhere]">
                                    {result.company_name}
                                </span>
                                <span className="text-slate-500 text-xs font-medium">
                                    Authored by Writing Agent & QA Squad
                                </span>
                            </div>
                        </div>
                        <button
                            onClick={handleReset}
                            className="flex items-center gap-2 text-xs font-bold text-slate-400 hover:text-white px-5 py-3 rounded-xl border border-slate-800 bg-slate-900/50 hover:bg-slate-800 transition-all hover:scale-105 active:scale-95"
                        >
                            <RefreshCw className="w-4 h-4" />
                            CREATE NEW
                        </button>
                    </div>

                    <ProposalResult result={result} />

                    <ExportPanel
                        proposalMarkdown={result.final_proposal || result.proposal_draft}
                        companyName={result.company_name}
                    />
                </div>
            )}

            {/* ─── ERROR State ─── */}
            {pageState === "error" && (
                <div className="card max-w-2xl mx-auto text-center border-red-500/20 bg-red-500/5 py-12">
                    <div className="w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                        <Terminal className="w-10 h-10 text-red-500" />
                    </div>
                    <h2 className="text-2xl font-black text-white mb-3 tracking-tight">System Termination</h2>
                    <div className="bg-slate-950/80 p-4 rounded-lg font-mono text-xs text-red-400/80 border border-red-500/10 mb-8 max-w-md mx-auto overflow-hidden whitespace-pre-wrap">
                        {error || "CRITICAL_PIPELINE_ERROR: TERMINATED_UNEXPECTEDLY"}
                    </div>

                    <div className="flex flex-col items-center gap-4">
                        <button onClick={handleReset} className="btn-primary px-10 flex items-center gap-2">
                            <RefreshCw className="w-4 h-4" />
                            Re-initialize System
                        </button>
                        <a
                            href={`data:text/plain;charset=utf-8,${encodeURIComponent(error)}`}
                            download="proposal-error.txt"
                            className="text-slate-500 text-[10px] font-bold uppercase tracking-widest hover:text-slate-300"
                        >
                            Download Error Details
                        </a>
                    </div>

                    {(error.includes("429") || error.toLowerCase().includes("rate limit")) && (
                        <div className="mt-10 p-6 bg-slate-900/80 border border-slate-800 rounded-xl text-left max-w-lg mx-auto">
                            <div className="flex items-center gap-3 mb-3">
                                <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
                                <p className="text-yellow-500 text-[10px] font-black uppercase tracking-widest">
                                    Provider Alert: Rate Limit Exceeded
                                </p>
                            </div>
                            <p className="text-slate-400 text-xs leading-relaxed">
                                The model provider is limiting requests. Try again shortly. If the limit persists,
                                check usage in your provider dashboard.
                            </p>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
