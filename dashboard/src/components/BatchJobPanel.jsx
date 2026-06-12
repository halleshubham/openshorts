import React, { useState, useEffect, useRef } from 'react';
import { ChevronDown, Loader2, CheckCircle2, AlertCircle, Clock, FileVideo, Youtube, Sparkles, Terminal } from 'lucide-react';
import ResultCard from './ResultCard';

function StatusBadge({ status }) {
    const map = {
        queued:     'bg-zinc-500/10 border-zinc-500/20 text-zinc-400',
        submitting: 'bg-blue-500/10  border-blue-500/20  text-blue-400',
        processing: 'bg-primary/10   border-primary/20   text-primary',
        complete:   'bg-green-500/10 border-green-500/20 text-green-400',
        error:      'bg-red-500/10   border-red-500/20   text-red-400',
    };
    const icons = {
        queued:     <Clock size={11} />,
        submitting: <Loader2 size={11} className="animate-spin" />,
        processing: <Loader2 size={11} className="animate-spin" />,
        complete:   <CheckCircle2 size={11} />,
        error:      <AlertCircle size={11} />,
    };
    return (
        <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wide ${map[status] || map.queued}`}>
            {icons[status]}
            {status}
        </span>
    );
}

export default function BatchJobPanel({ job, uploadPostKey, uploadUserId, geminiApiKey, elevenLabsKey, onDeleteClip }) {
    const [clipsExpanded, setClipsExpanded] = useState(false);
    // Logs open by default while processing, collapsed once done
    const [logsOpen, setLogsOpen] = useState(job.status === 'processing' || job.status === 'submitting');
    const logsEndRef = useRef(null);
    const prevStatusRef = useRef(job.status);

    const clipCount = job.results?.clips?.length ?? 0;
    const mediaIcon = job.media?.type === 'url'
        ? <Youtube size={14} className="text-red-400 shrink-0" />
        : <FileVideo size={14} className="text-blue-400 shrink-0" />;

    // Auto-open logs when job starts processing
    useEffect(() => {
        if (prevStatusRef.current !== job.status) {
            if (job.status === 'processing') setLogsOpen(true);
            prevStatusRef.current = job.status;
        }
    }, [job.status]);

    // Auto-scroll to bottom whenever new logs arrive
    useEffect(() => {
        if (logsOpen && logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [job.logs, logsOpen]);

    const isActive = job.status === 'processing' || job.status === 'submitting';

    return (
        <div className="bg-surface border border-white/5 rounded-2xl overflow-hidden animate-[fadeIn_0.4s_ease-out]">
            {/* ── Header row ── */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-white/5">
                {mediaIcon}
                <p className="flex-1 text-sm font-medium text-white truncate min-w-0" title={job.media?.name}>
                    {job.media?.name || 'Video'}
                </p>

                <StatusBadge status={job.status} />

                {job.status === 'complete' && clipCount > 0 && (
                    <button
                        onClick={() => setClipsExpanded(e => !e)}
                        className="inline-flex items-center gap-1.5 text-[10px] bg-white/10 hover:bg-white/15 text-white px-2 py-0.5 rounded-full transition-colors"
                    >
                        {clipCount} clips
                        <ChevronDown size={10} className={`transition-transform duration-200 ${clipsExpanded ? 'rotate-180' : ''}`} />
                    </button>
                )}
            </div>

            {/* ── Log terminal ── */}
            {(isActive || job.logs?.length > 0 || job.error) && (
                <div className={`bg-[#0c0c0e] border-b border-white/5 overflow-hidden flex flex-col transition-all duration-500
                    ${isActive ? 'min-h-[160px] max-h-64' : 'max-h-32 opacity-60 hover:opacity-100'}`}>

                    {/* Terminal header */}
                    <div className="px-3 py-1.5 border-b border-white/5 bg-white/5 flex items-center justify-between shrink-0">
                        <span className="text-[10px] font-mono text-zinc-400 flex items-center gap-1.5">
                            <Terminal size={10} />
                            {job.media?.name
                                ? job.media.name.length > 40
                                    ? job.media.name.slice(0, 40) + '…'
                                    : job.media.name
                                : 'Logs'}
                        </span>
                        <button
                            onClick={() => setLogsOpen(o => !o)}
                            className="text-zinc-600 hover:text-zinc-300 transition-colors"
                            title={logsOpen ? 'Collapse logs' : 'Expand logs'}
                        >
                            <ChevronDown size={12} className={`transition-transform duration-200 ${logsOpen ? '' : 'rotate-180'}`} />
                        </button>
                    </div>

                    {/* Log lines */}
                    {logsOpen && (
                        <div className="flex-1 p-3 overflow-y-auto font-mono text-[11px] space-y-1 custom-scrollbar">
                            {job.logs?.map((log, i) => (
                                <div
                                    key={i}
                                    className={`flex gap-2 leading-relaxed ${
                                        log.toLowerCase().includes('error') || log.toLowerCase().includes('❌')
                                            ? 'text-red-400'
                                            : log.toLowerCase().includes('✅') || log.toLowerCase().includes('complete')
                                                ? 'text-green-400'
                                                : 'text-zinc-400'
                                    }`}
                                >
                                    <span className="text-zinc-700 shrink-0 select-none">›</span>
                                    <span className="break-all">{log}</span>
                                </div>
                            ))}

                            {job.error && (
                                <div className="flex gap-2 text-red-400">
                                    <span className="text-red-700 shrink-0 select-none">›</span>
                                    <span className="break-all">{job.error}</span>
                                </div>
                            )}

                            {isActive && (
                                <div className="animate-pulse text-primary/70 select-none">_</div>
                            )}

                            {/* Scroll anchor */}
                            <div ref={logsEndRef} />
                        </div>
                    )}
                </div>
            )}

            {/* ── Clips grid (expandable) ── */}
            {clipsExpanded && job.status === 'complete' && clipCount > 0 && (
                <div className="p-4 animate-[fadeIn_0.25s_ease-out]">
                    <div className="flex items-center gap-2 mb-4">
                        <Sparkles size={14} className="text-yellow-400" />
                        <span className="text-xs font-bold text-white">Generated Clips</span>
                    </div>
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                        {job.results.clips.map((clip, i) => (
                            <ResultCard
                                key={i}
                                clip={clip}
                                index={i}
                                jobId={job.jobId}
                                uploadPostKey={uploadPostKey}
                                uploadUserId={uploadUserId}
                                geminiApiKey={geminiApiKey}
                                elevenLabsKey={elevenLabsKey}
                                onDelete={(deletedIndex) => onDeleteClip(job.id, deletedIndex)}
                            />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
