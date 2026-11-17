/** Browser calls use the same-origin Next.js proxy unless explicitly configured. */
export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "/api").replace(/\/$/, "");

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
    started_at?: string;
    completed_at?: string;
}

export interface ProposalResult {
    company_name: string;
    industry: string;
    pain_points: string[];
    solution_mapping: Record<string, unknown>;
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
    components: Record<string, unknown>;
}

export class ApiError extends Error {
    constructor(message: string, public status: number) {
        super(message);
        this.name = "ApiError";
    }
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
    const controller = new AbortController();
    const abort = () => controller.abort();
    init.signal?.addEventListener("abort", abort, { once: true });
    if (init.signal?.aborted) controller.abort();
    const timeout = setTimeout(abort, 30_000);
    try {
        const response = await fetch(`${API_BASE}${path}`, {
            ...init,
            cache: "no-store",
            signal: controller.signal,
        });
        if (!response.ok || response.status === 202) {
            const body = await response.json().catch(() => null);
            const detail = body?.detail;
            const message = typeof detail === "string" ? detail
                : Array.isArray(detail) ? detail.map((item: { msg?: string }) => item.msg || "Invalid input").join("; ")
                : `Request failed (${response.status})`;
            throw new ApiError(message, response.status);
        }
        return response;
    } finally {
        clearTimeout(timeout);
        init.signal?.removeEventListener("abort", abort);
    }
}

function jsonPost(body: unknown): RequestInit {
    return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

export async function checkHealth(): Promise<HealthCheck> {
    return (await request("/health")).json();
}

export async function startProposal(input: ProposalRequest): Promise<AsyncJobResponse> {
    return (await request("/proposal/generate/async", jsonPost({
        ...input, requestor_name: input.requestor_name || "Sales Team",
    }))).json();
}

export async function getProposalStatus(threadId: string, signal?: AbortSignal): Promise<ProposalStatus> {
    return (await request(`/proposal/status/${encodeURIComponent(threadId)}`, { signal })).json();
}

export async function getProposalResult(threadId: string): Promise<ProposalResult> {
    return (await request(`/proposal/result/${encodeURIComponent(threadId)}`)).json();
}

export async function exportProposal(
    format: "pdf" | "html" | "markdown", proposalMarkdown: string, companyName: string
): Promise<Blob> {
    return (await request(`/proposal/export/${format}`, jsonPost({
        proposal_markdown: proposalMarkdown, company_name: companyName,
    }))).blob();
}

export async function getExportFormats(): Promise<Record<string, boolean>> {
    return (await (await request("/proposal/export/formats")).json()).formats;
}
