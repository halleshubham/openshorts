import React from 'react';
import { Layers, Loader2, Check, AlertCircle, Pause, Clock, X } from 'lucide-react';

const STATUS = {
    queued: { label: 'queued', Icon: Clock, tone: 'text-muted' },
    processing: { label: 'processing', Icon: Loader2, tone: 'text-brass', spin: true },
    done: { label: 'done', Icon: Check, tone: 'text-ok' },
    failed: { label: 'failed', Icon: AlertCircle, tone: 'text-danger' },
    cancelled: { label: 'cancelled', Icon: X, tone: 'text-muted' },
    paused: { label: 'paused', Icon: Pause, tone: 'text-brass' },
};

/**
 * The batch's videos, one row each. The batch runs them one after another
 * through the normal single-video flow, so only the video being processed shows
 * live progress; finished ones can be reopened to review their clips.
 */
export default function BatchQueue({ jobs, active, paused, canOpen, onOpen, onResume, onCancel, onClear }) {
    if (!jobs || jobs.length === 0) return null;
    const doneCount = jobs.filter((j) => j.status === 'done').length;

    return (
        <div className="card p-4 sm:p-5 animate-fade" data-testid="batch-queue">
            <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 mb-3">
                <h2 className="text-sm font-medium text-ink lowercase flex items-center gap-2">
                    <Layers size={16} className="text-brass" />
                    Batch
                    <span className="readout whitespace-nowrap">{doneCount}/{jobs.length} done</span>
                </h2>
                <div className="flex items-center gap-2">
                    {paused && (
                        <button type="button" onClick={onResume} className="btn-primary text-xs px-3 py-1.5">
                            Resume
                        </button>
                    )}
                    {active && (
                        <button type="button" onClick={onCancel} className="btn-ghost text-xs px-3 py-1.5">
                            Cancel rest
                        </button>
                    )}
                    {!active && (
                        <button type="button" onClick={onClear} className="btn-ghost text-xs px-3 py-1.5">
                            Dismiss
                        </button>
                    )}
                </div>
            </div>
            <ul className="divide-y divide-rule">
                {jobs.map((j, i) => {
                    const s = STATUS[j.status] || STATUS.queued;
                    const reviewable = j.status === 'done' && j.jobId;
                    return (
                        <li key={j.id} className="flex items-center gap-3 py-2 min-w-0">
                            <span className="readout w-5 shrink-0 text-right">{i + 1}</span>
                            <span className="truncate text-sm text-ink2 min-w-0 flex-1" title={j.label}>{j.label}</span>
                            <span className={`flex items-center gap-1.5 text-xs lowercase shrink-0 ${s.tone}`}>
                                <s.Icon size={14} className={s.spin ? 'animate-spin' : ''} />
                                {s.label}
                            </span>
                            {reviewable && (
                                <button
                                    type="button"
                                    disabled={!canOpen}
                                    title={canOpen ? 'Review these clips' : 'Available when the current video finishes'}
                                    onClick={() => onOpen(j)}
                                    className="btn-ghost text-xs px-3 py-1.5 shrink-0 disabled:opacity-45 disabled:cursor-not-allowed"
                                >
                                    Open
                                </button>
                            )}
                        </li>
                    );
                })}
            </ul>
            {jobs.some((j) => j.status === 'failed' && j.error) && (
                <p className="text-xs text-danger mt-3">
                    {jobs.filter((j) => j.status === 'failed' && j.error).map((j) => j.error)[0]}
                </p>
            )}
        </div>
    );
}
