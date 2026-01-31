import { useEffect, useState } from "react";
import { getCrawlStatus } from "../services/api";
import type { CrawlStatus } from "../types";
import { STEP_LABELS, STEP_ORDER } from "../types";

interface Props {
  jobId: string;
  url: string;
  onComplete: () => void;
}

const STATUS_ICON: Record<string, string> = {
  pending: "⏳",
  in_progress: "🔄",
  complete: "✅",
  failed: "❌",
};

export default function CrawlProgress({ jobId, url, onComplete }: Props) {
  const [status, setStatus] = useState<CrawlStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const s = await getCrawlStatus(jobId);
        if (!active) return;
        setStatus(s);
        if (s.status === "complete") {
          onComplete();
          return;
        }
        // Check if failed
        const completedStep = s.steps["complete"];
        if (completedStep?.status === "failed") {
          setError(completedStep.detail || "Crawl failed");
          return;
        }
        setTimeout(poll, 2000);
      } catch (err) {
        if (active) setError(String(err));
      }
    };
    poll();
    return () => {
      active = false;
    };
  }, [jobId, onComplete]);

  const completedCount = status
    ? STEP_ORDER.filter((s) => status.steps[s]?.status === "complete").length
    : 0;
  const progress = Math.round((completedCount / STEP_ORDER.length) * 100);

  return (
    <div className="max-w-lg mx-auto mt-12 bg-white rounded-xl shadow-lg p-8">
      <h2 className="text-xl font-semibold text-gray-800 mb-1">
        Crawling {new URL(url).hostname}...
      </h2>
      <p className="text-sm text-gray-500 mb-6">{url}</p>

      {error && (
        <div className="bg-red-50 text-red-700 rounded-lg p-3 mb-4 text-sm">
          {error}
        </div>
      )}

      <div className="space-y-3 mb-6">
        {STEP_ORDER.map((step) => {
          const info = status?.steps[step];
          const icon = STATUS_ICON[info?.status ?? "pending"];
          const detail = info?.detail ? ` (${info.detail})` : "";
          return (
            <div key={step} className="flex items-center gap-3">
              <span className="text-lg w-6 text-center">{icon}</span>
              <span
                className={`text-sm ${
                  info?.status === "complete"
                    ? "text-gray-700"
                    : info?.status === "in_progress"
                    ? "text-blue-700 font-medium"
                    : "text-gray-400"
                }`}
              >
                {STEP_LABELS[step]}
                {detail && (
                  <span className="text-gray-400 ml-1">{detail}</span>
                )}
              </span>
            </div>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="text-xs text-gray-400 mt-1 text-right">{progress}%</p>
    </div>
  );
}
