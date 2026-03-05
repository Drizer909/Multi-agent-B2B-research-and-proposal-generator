/**
 * API Client — All fetch functions that call the FastAPI backend.
 *
 * Uses Next.js rewrite proxy (/api/* → localhost:8000/*)
 * OR direct calls via NEXT_PUBLIC_API_URL env var.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ───────────────────────────────────────

export interface ProposalRequest {
    company_name: string;
    user_request: string;
    requestor_name?: string;
}

export interface AsyncJobResponse {
    thread_id: string;
    status: string;
    message: string;
}

export interface ProposalStatus {
    thread_id: string;
    status: "queued" | "running" | "completed" | "failed";
    current_phase: string;
    company_name: string;
    qa_score: number;
    revision_count: number;
    approved: boolean;
    error: string;
}

export interface ProposalResult {
    company_name: string;
    industry: string;
    pain_points: string[];
    solution_mapping: Record<string, any>;
    proposal_draft: string;
    qa_score: number;
    revision_count: number;
    approved: boolean;
    current_phase: string;
    final_proposal: string;
    started_at: string;
    completed_at: string;
}

export interface HealthCheck {
    status: string;
    version: string;
    api_keys: Record<string, boolean>;
    requests_remaining: number;
    components: Record<string, any>;
}

// ─── API Functions ───────────────────────────────

export async function checkHealth(): Promise<HealthCheck> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
    return res.json();
}

export async function startProposal(
    request: ProposalRequest
): Promise<AsyncJobResponse> {
    const res = await fetch(`${API_BASE}/proposal/generate/async`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            company_name: request.company_name,
            user_request: request.user_request,
            requestor_name: request.requestor_name || "Sales Team",
        }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Failed to start proposal generation");
    }
    return res.json();
}

export async function getProposalStatus(
    threadId: string
): Promise<ProposalStatus> {
    const res = await fetch(`${API_BASE}/proposal/status/${threadId}`);
    if (!res.ok) throw new Error(`Status check failed: ${res.status}`);
    return res.json();
}

export async function getProposalResult(
    threadId: string
): Promise<ProposalResult> {
    const res = await fetch(`${API_BASE}/proposal/result/${threadId}`);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Failed to get result");
    }
    return res.json();
}

export async function exportProposal(
    format: "pdf" | "html" | "markdown",
    proposalMarkdown: string,
    companyName: string
): Promise<Blob> {
    const res = await fetch(`${API_BASE}/proposal/export/${format}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            proposal_markdown: proposalMarkdown,
            company_name: companyName,
        }),
    });
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    return res.blob();
}

export async function getExportFormats(): Promise<Record<string, boolean>> {
    const res = await fetch(`${API_BASE}/proposal/export/formats`);
    if (!res.ok) return { pdf: false, html: true, markdown: true };
    const data = await res.json();
    return data.formats;
}
