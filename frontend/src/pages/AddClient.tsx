import { useCallback, useState } from "react";
import CrawlProgress from "../components/CrawlProgress";
import ResultsView from "../components/ResultsView";
import { getCrawlResult, startCrawl } from "../services/api";
import type { CrawlResult } from "../types";

const INDUSTRIES = [
  "E-commerce",
  "SaaS",
  "Healthcare",
  "Finance",
  "Education",
  "Food & Beverage",
  "Travel",
  "Real Estate",
  "Media",
  "Other",
];

type View = "form" | "progress" | "results";

export default function AddClient() {
  const [clientName, setClientName] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [industry, setIndustry] = useState("");
  const [view, setView] = useState<View>("form");
  const [jobId, setJobId] = useState("");
  const [result, setResult] = useState<CrawlResult | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    let url = websiteUrl.trim();
    if (!url.startsWith("http")) url = "https://" + url;

    try {
      const { job_id } = await startCrawl({
        url,
        client_name: clientName.trim(),
        industry,
      });
      setJobId(job_id);
      setWebsiteUrl(url);
      setView("progress");
    } catch (err) {
      setError(String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCrawlComplete = useCallback(async () => {
    try {
      const r = await getCrawlResult(jobId);
      if (r) {
        setResult(r);
        setView("results");
      }
    } catch (err) {
      setError(String(err));
    }
  }, [jobId]);

  const handleReset = () => {
    setView("form");
    setJobId("");
    setResult(null);
    setClientName("");
    setWebsiteUrl("");
    setIndustry("");
    setError("");
  };

  if (view === "progress") {
    return (
      <CrawlProgress
        jobId={jobId}
        url={websiteUrl}
        onComplete={handleCrawlComplete}
      />
    );
  }

  if (view === "results" && result) {
    return <ResultsView result={result} onReset={handleReset} />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <h1 className="text-2xl font-bold text-gray-900 text-center mb-2">
            Add Your First Client
          </h1>
          <p className="text-gray-500 text-center text-sm mb-8">
            We'll crawl their website to extract brand details automatically.
          </p>

          {error && (
            <div className="bg-red-50 text-red-700 rounded-lg p-3 mb-4 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Client Name
              </label>
              <input
                type="text"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                placeholder="e.g. FreshBasket"
                required
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Website URL
              </label>
              <input
                type="text"
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                placeholder="e.g. https://freshbasket.in"
                required
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Industry
              </label>
              <select
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm bg-white"
              >
                <option value="">Select industry...</option>
                {INDUSTRIES.map((ind) => (
                  <option key={ind} value={ind}>
                    {ind}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={submitting || !clientName.trim() || !websiteUrl.trim()}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-lg font-medium text-sm transition-colors"
            >
              {submitting ? "Starting..." : "Continue"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
