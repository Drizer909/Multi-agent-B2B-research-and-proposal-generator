"use client";

import { useEffect, useState } from "react";
import { ApiError, getProposalStatus, type ProposalStatus } from "@/lib/api";
import { getStageStatus, STAGES } from "@/lib/progress";
import { Timer, CheckCircle2, Circle, AlertCircle, Loader2 } from "lucide-react";

interface Props {
    threadId: string;
    onComplete: () => void;
    onError: (error: string) => void;
}

export default function ProgressTracker({ threadId, onComplete, onError }: Props) {
    const [status, setStatus] = useState<ProposalStatus | null>(null);
    const [elapsed, setElapsed] = useState(0);
    const [connectionLost, setConnectionLost] = useState(false);

    useEffect(() => {
        const controller = new AbortController();
        const startTime = Date.now();
        let nextPoll: ReturnType<typeof setTimeout>;
        const timer = setInterval(() => {
            setElapsed(Math.floor((Date.now() - startTime) / 1000));
        }, 1000);

        async function poll() {
            try {
                const snapshot = await getProposalStatus(threadId, controller.signal);
                if (controller.signal.aborted) return;

                setStatus(snapshot);
                setConnectionLost(false);
                if (snapshot.status === "completed") {
                    clearInterval(timer);
                    onComplete();
                    return;
                }
                if (snapshot.status === "failed") {
                    clearInterval(timer);
                    onError(snapshot.error || "Proposal generation failed.");
                    return;
                }
            } catch (err) {
                if (controller.signal.aborted) return;
                if (err instanceof ApiError && err.status === 404) {
                    clearInterval(timer);
                    onError(err.message);
                    return;
                }
                setConnectionLost(true);
            }
            nextPoll = setTimeout(poll, 1000);
        }

        void poll();
        return () => {
            controller.abort();
            clearTimeout(nextPoll);
            clearInterval(timer);
        };
    }, [threadId, onComplete, onError]);

    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;

    return (
        <div className="card max-w-2xl mx-auto border-blue-500/20">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h2 className="text-2xl font-bold text-white mb-1">Processing Pipeline</h2>
                    <p className="text-xs text-blue-400 font-mono tracking-wider items-center flex gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                        {status?.company_name ? `ID: ${threadId.slice(-8)} | ${status.company_name}` : "Waiting for the pipeline"}
                    </p>
                </div>
                <div className="flex flex-col items-end">
                    <div className="text-3xl font-mono text-white flex items-center gap-2">
                        <Timer className="w-5 h-5 text-slate-400" />
                        {minutes}:{seconds.toString().padStart(2, "0")}
                    </div>
                    <div className="text-[10px] uppercase font-bold text-slate-500 tracking-tighter">ELAPSED TIME</div>
                </div>
            </div>

            {connectionLost && (
                <p role="status" className="mb-4 text-sm text-amber-400">
                    Progress connection interrupted. Reconnecting…
                </p>
            )}

            <div className="space-y-4">
                {STAGES.map((stage, idx) => {
                    const stageStatus = getStageStatus(
                        idx,
                        status?.current_phase || "",
                        status?.status || "queued"
                    );

                    return (
                        <div
                            key={stage.id}
                            aria-current={stageStatus === "active" ? "step" : undefined}
                            className="group relative flex items-start gap-5"
                        >
                            {/* Vertical Line */}
                            {idx !== STAGES.length - 1 && (
                                <div className={`absolute left-[19px] top-10 w-0.5 h-6 transition-colors duration-500 ${stageStatus === "complete" ? "bg-green-600" : "bg-slate-700"
                                    }`} />
                            )}

                            {/* Status Circle */}
                            <div className={`relative z-10 w-10 h-10 rounded-full flex items-center justify-center transition-all duration-500 ${stageStatus === "complete" ? "bg-green-600/20 ring-2 ring-green-600" :
                                    stageStatus === "active" ? "bg-blue-600/20 ring-2 ring-blue-600" :
                                        stageStatus === "failed" ? "bg-red-600/20 ring-2 ring-red-600" :
                                            "bg-slate-800 ring-1 ring-slate-700"
                                }`}>
                                {stageStatus === "complete" ? <CheckCircle2 className="w-6 h-6 text-green-500" /> :
                                    stageStatus === "active" ? <Loader2 className="w-6 h-6 text-blue-500 animate-spin" /> :
                                        stageStatus === "failed" ? <AlertCircle className="w-6 h-6 text-red-500" /> :
                                            <Circle className="w-5 h-5 text-slate-600" />}
                            </div>

                            {/* Text Info */}
                            <div className="flex-1 pt-0.5">
                                <h4 className={`text-base font-bold transition-colors ${stageStatus === "active" ? "text-blue-400" :
                                        stageStatus === "complete" ? "text-white" :
                                            stageStatus === "failed" ? "text-red-400" : "text-slate-500"
                                    }`}>
                                    {stage.name}
                                </h4>
                                <p className="text-xs text-slate-500 mt-0.5">
                                    {stageStatus === "active" ? "Agent is currently processing data..." :
                                        stageStatus === "complete" ? "Task successfully finalized." :
                                            stageStatus === "failed" ? "Process encountered a critical error." :
                                                "Awaiting previous task completion."}
                                </p>
                            </div>

                            {/* QA Detail overlay during active loop */}
                            {stage.id === "writing" && stageStatus === "active" && status?.revision_count && status.revision_count > 0 ? (
                                <div className="absolute -right-4 top-0 bg-yellow-500/10 border border-yellow-500/20 px-3 py-1 rounded text-[10px] text-yellow-500 font-bold uppercase">
                                    Revision #{status.revision_count}
                                </div>
                            ) : null}
                        </div>
                    );
                })}
            </div>

            {status?.qa_score !== undefined && status.qa_score > 0 && (
                <div className="mt-8 pt-6 border-t border-slate-700/50 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="bg-slate-700/50 p-3 rounded-lg">
                            <div className="text-[10px] uppercase font-bold text-slate-500 mb-1">QA Score</div>
                            <div className={`text-xl font-mono font-bold ${status.qa_score >= 0.9 ? "text-green-500" : status.qa_score >= 0.6 ? "text-yellow-500" : "text-red-500"}`}>
                                {(status.qa_score * 100).toFixed(0)}%
                            </div>
                        </div>
                        {status.revision_count > 0 && (
                            <div className="bg-slate-700/50 p-3 rounded-lg">
                                <div className="text-[10px] uppercase font-bold text-slate-500 mb-1">Revisions</div>
                                <div className="text-xl font-mono font-bold text-slate-300">{status.revision_count}</div>
                            </div>
                        )}
                    </div>
                    <div className="text-right">
                        <div className="text-[10px] uppercase font-bold text-slate-500 mb-1">Current State</div>
                        <div className="text-xs font-semibold text-slate-300">{(status.current_phase || "RUNNING").replace(/_/g, " ")}</div>
                    </div>
                </div>
            )}
        </div>
    );
}
