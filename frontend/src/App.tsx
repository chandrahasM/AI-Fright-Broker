import { useState } from "react";
import { Routes, Route, NavLink, useNavigate, Navigate } from "react-router-dom";
import { useEmails, useProcessEmail } from "./hooks/useEmails";
import { InboxTable } from "./components/InboxTable";
import { SidePanel } from "./components/SidePanel";
import { ChatTab } from "./components/ChatTab";
import { VoiceTab } from "./components/VoiceTab";

// ---------------------------------------------------------------------------
// Inbox page (owns selected-email state locally)
// ---------------------------------------------------------------------------
function InboxPage() {
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);
  const { data: emails } = useEmails();

  return (
    <div className="flex flex-1 overflow-hidden">
      <main
        className={`flex-1 overflow-y-auto transition-all duration-200 ${
          selectedEmailId ? "max-w-[60%]" : "w-full"
        }`}
      >
        <div className="px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-700">
              Inbox
              {emails && (
                <span className="ml-2 text-gray-400 font-normal">
                  ({emails.length} emails)
                </span>
              )}
            </h2>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <InboxTable
              selectedEmailId={selectedEmailId}
              onSelectEmail={setSelectedEmailId}
            />
          </div>
        </div>
      </main>

      {selectedEmailId && (
        <aside className="w-[480px] shrink-0 overflow-hidden flex flex-col">
          <SidePanel
            emailId={selectedEmailId}
            onClose={() => setSelectedEmailId(null)}
          />
        </aside>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// App shell
// ---------------------------------------------------------------------------
const TABS = [
  { path: "/inbox", label: "Inbox" },
  { path: "/voice", label: "Voice Calls" },
  { path: "/qna",   label: "QnA" },
] as const;

export default function App() {
  const { data: emails } = useEmails();
  const processEmail = useProcessEmail();
  const navigate = useNavigate();

  const pendingCount = emails?.filter((e) => e.processing_status === "pending").length ?? 0;
  const isInbox = location.pathname === "/inbox" || location.pathname === "/";

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          {/* Logo */}
          <button
            onClick={() => navigate("/inbox")}
            className="flex items-center gap-3 focus:outline-none"
          >
            <div className="w-8 h-8 rounded-md bg-indigo-600 flex items-center justify-center">
              <span className="text-white text-sm font-bold">G</span>
            </div>
            <div className="text-left">
              <h1 className="text-base font-semibold text-gray-900">Goodlane Inbox</h1>
              <p className="text-xs text-gray-400">Freight Broker Assistant</p>
            </div>
          </button>

          {/* Tab switcher */}
          <nav className="flex items-center gap-1 ml-4 bg-gray-100 rounded-lg p-0.5">
            {TABS.map(({ path, label }) => (
              <NavLink
                key={path}
                to={path}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-500 hover:text-gray-700"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Process Next — only on inbox */}
        {isInbox && (
          <div className="flex items-center gap-3">
            {pendingCount > 0 && (
              <span className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-full px-2.5 py-0.5">
                {pendingCount} pending
              </span>
            )}
            <button
              onClick={() => {
                const pending = emails?.find((e) => e.processing_status === "pending");
                if (pending) processEmail.mutate(pending.email_id);
              }}
              disabled={!pendingCount || processEmail.isPending}
              className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {processEmail.isPending ? "Processing…" : "Process Next"}
            </button>
          </div>
        )}
      </header>

      {/* Route content */}
      <Routes>
        <Route path="/" element={<Navigate to="/inbox" replace />} />
        <Route path="/inbox" element={<InboxPage />} />
        <Route
          path="/voice"
          element={
            <div className="flex flex-1 overflow-hidden">
              <VoiceTab />
            </div>
          }
        />
        <Route
          path="/qna"
          element={
            <div className="flex-1 overflow-hidden">
              <ChatTab />
            </div>
          }
        />
        {/* Fallback — redirect unknown paths to inbox */}
        <Route path="*" element={<Navigate to="/inbox" replace />} />
      </Routes>
    </div>
  );
}
