"use client";

import { useState } from "react";
import { Send, Building2, User } from "lucide-react";

interface Props {
    onSubmit: (companyName: string, userRequest: string, requestorName: string) => void;
    isLoading: boolean;
}

export default function ProposalForm({ onSubmit, isLoading }: Props) {
    const [companyName, setCompanyName] = useState("");
    const [userRequest, setUserRequest] = useState("");
    const [requestorName, setRequestorName] = useState("");
    const [errors, setErrors] = useState<Record<string, string>>({});

    function validate(): boolean {
        const newErrors: Record<string, string> = {};
        if (!companyName.trim()) newErrors.company = "Company name is required";
        if (userRequest.trim().length < 5)
            newErrors.request = "Please describe what the proposal should cover (min 5 characters)";
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    }

    function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!validate()) return;
        onSubmit(companyName.trim(), userRequest.trim(), requestorName.trim() || "Sales Team");
    }

    return (
        <div className="card max-w-2xl mx-auto border-slate-700/50">
            <div className="mb-8">
                <h2 className="text-3xl font-bold text-white mb-2 bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                    Create New Proposal
                </h2>
                <p className="text-slate-400 text-sm">
                    Enter company details and our 4-agent AI squad will handle the research,
                    strategy, writing, and QA for your customized proposal.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
                {/* Company Name */}
                <div>
                    <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-2">
                        <Building2 className="w-4 h-4 text-blue-400" />
                        Target Company <span className="text-red-400">*</span>
                    </label>
                    <input
                        type="text"
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        placeholder="e.g., Stripe, Shopify, Tesla"
                        className={`input-field ${errors.company ? "border-red-500 focus:ring-red-500" : ""}`}
                        disabled={isLoading}
                    />
                    {errors.company && (
                        <p className="text-red-400 text-xs mt-2">{errors.company}</p>
                    )}
                </div>

                {/* User Request */}
                <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                        What should we propose? <span className="text-red-400">*</span>
                    </label>
                    <textarea
                        value={userRequest}
                        onChange={(e) => setUserRequest(e.target.value)}
                        placeholder="e.g., Optimization of payment workflows and integration of high-risk fraud detection modules..."
                        rows={4}
                        className={`input-field resize-none ${errors.request ? "border-red-500 focus:ring-red-500" : ""}`}
                        disabled={isLoading}
                    />
                    {errors.request && (
                        <p className="text-red-400 text-xs mt-2">{errors.request}</p>
                    )}
                </div>

                {/* Requestor Name */}
                <div>
                    <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-2">
                        <User className="w-4 h-4 text-slate-400" />
                        Your Name <span className="text-slate-500">(optional)</span>
                    </label>
                    <input
                        type="text"
                        value={requestorName}
                        onChange={(e) => setRequestorName(e.target.value)}
                        placeholder="Sales Team"
                        className="input-field"
                        disabled={isLoading}
                    />
                </div>

                {/* Submit */}
                <button type="submit" disabled={isLoading} className="btn-primary w-full text-lg flex items-center justify-center gap-2 group">
                    {isLoading ? (
                        <>
                            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                            Initializing Pipeline...
                        </>
                    ) : (
                        <>
                            Generate Proposal
                            <Send className="w-5 h-5 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
                        </>
                    )}
                </button>

                <p className="text-center text-xs text-slate-500">
                    Estimated completion: 2-5 minutes · Deep search enabled
                </p>
            </form>
        </div>
    );
}
