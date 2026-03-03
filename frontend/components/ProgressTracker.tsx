"use client";

import { useEffect, useState, useRef } from "react";
import { getProposalStatus, type ProposalStatus } from "@/lib/api";
import { Timer, CheckCircle2, Circle, AlertCircle, Loader2 } from "lucide-react";

interface Props {
    threadId: string;
    onComplete: () => void;
    onError: (error: string) => void;
}

interface Stage {
    id: string;
    name: string;
    icon: string;
    phases: string[];
}

const STAGES: Stage[] = [
    { id: "research", name: "Deep Research", icon: "🔬", phases: ["initialized", "research_complete", "research_failed"] },
    { id: "analysis", name: "Strategic Analysis", icon: "🔍", phases: ["analysis_complete", "analysis_failed"] },
    { id: "writing", name: "Proposal Writing", icon: "✍️", phases: ["writing_complete", "writing_failed", "revision_1", "revision_2", "revision_3"] },
    { id: "qa", name: "QA & Verification", icon: "🔎", phases: ["qa_passed", "qa_failed", "qa_needs_revision"] },
    { id: "review", name: "Final Review", icon: "👤", phases: ["awaiting_human_review"] },
    { id: "complete", name: "Generating Files", icon: "🎉", phases: ["completed"] },
];

function getStageStatus(
    stageIndex: number,
    currentPhase: string,
    jobStatus: string
): "pending" | "active" | "complete" | "failed" {
    if (jobStatus === "failed") {
        for (let i = 0; i < STAGES.length; i++) {
            const stage = STAGES[i];
            if (stage.phases.some(p => currentPhase.includes(p.replace("_complete", "_failed")) || currentPhase.includes("failed"))) {
                if (i === stageIndex) return "failed";
                if (i < stageIndex) return "pending";
                return "complete";
            }
        }
        return stageIndex === 0 ? "failed" : "pending";
    }

    if (jobStatus === "completed" || currentPhase === "completed") return "complete";

    let activeIdx = 0;
    for (let i = STAGES.length - 1; i >= 0; i--) {
        if (STAGES[i].phases.some((p) => currentPhase.includes(p) || currentPhase.startsWith(p.split("_")[0]))) {
            activeIdx = i;
            break;
        }
    }

    if (!currentPhase || currentPhase === "initialized") {
        return stageIndex === 0 ? "active" : "pending";
    }

    if (stageIndex < activeIdx) return "complete";
    if (stageIndex === activeIdx) return "active";
    return "pending";
}

export default function ProgressTracker({ threadId, onComplete, onError }: Props) {
    const [status, setStatus] = useState<ProposalStatus | null>(null);
    const [elapsed, setElapsed] = useState(0);
    const intervalRef = useRef<NodeJS.Timeout | null>(null);
    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const startTime = useRef(Date.now());

    useEffect(() => {
        async function poll() {
            try {
                const s = await getProposalStatus(threadId);
                setStatus(s);

                if (s.status === "completed") {
                    if (intervalRef.current) clearInterval(intervalRef.current);
                    if (timerRef.current) clearInterval(timerRef.current);
                    onComplete();
                } else if (s.status === "failed") {
                    if (intervalRef.current) clearInterval(intervalRef.current);
                    if (timerRef.current) clearInterval(timerRef.current);
                    onError(s.error || "Pipeline implementation error or LLM failure");
                }
            } catch (err) {
                console.warn("Poll connection error:", err);
            }
        }

        poll();
        intervalRef.current = setInterval(poll, 3000);
        timerRef.current = setInterval(() => {
            setElapsed(Math.floor((Date.now() - startTime.current) / 1000));
        }, 1000);

        return () => {
            if (intervalRef.current) clearInterval(intervalRef.current);
            if (timerRef.current) clearInterval(timerRef.current);
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
                        {status?.company_name ? `ID: ${threadId.slice(0, 8)} | ${status.company_name}` : "ACTIVE AGENTS RUNNING..."}
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

            <div className="space-y-4">
                {STAGES.map((stage, idx) => {
                    const stageStatus = getStageStatus(
                        idx,
                        status?.current_phase || "",
                        status?.status || "queued"
                    );

                    return (
                        <div key={stage.id} className="group relative flex items-start gap-5">
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
