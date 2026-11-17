export const STAGES = [
    { id: "research", name: "Deep Research" },
    { id: "analysis", name: "Strategic Analysis" },
    { id: "writing", name: "Proposal Writing" },
    { id: "qa", name: "QA & Verification" },
    { id: "complete", name: "Finalizing Proposal" },
];

type StageStatus = "pending" | "active" | "complete" | "failed";

export function getStageStatus(stageIndex: number, phase: string, jobStatus: string): StageStatus {
    if (jobStatus === "completed") return "complete";
    if (jobStatus === "queued") return "pending";

    // Completion phases mean the next agent is working. Explicit start phases
    // also let revisions move the tracker back to writing without guessing.
    const phases: Record<string, number> = {
        initialized: 0, research: 0, research_failed: 0,
        research_complete: 1, analysis: 1, analysis_failed: 1,
        analysis_complete: 2, writing: 2, writing_failed: 2,
        writing_complete: 3, qa: 3, qa_failed: 3, qa_needs_revision: 2,
        qa_passed: 4, awaiting_human_review: 4, finalizing: 4, finalize_failed: 4, completed: 4,
    };
    const activeIndex = phase.startsWith("revision_") ? 2 : (phases[phase] ?? 0);
    if (stageIndex < activeIndex) return "complete";
    if (stageIndex > activeIndex) return "pending";
    return jobStatus === "failed" ? "failed" : "active";
}
