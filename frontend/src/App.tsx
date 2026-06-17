import { useState } from "react";
import { useEmails, useProcessEmail } from "./hooks/useEmails";
import { InboxTable } from "./components/InboxTable";
import { SidePanel } from "./components/SidePanel";
import { ChatTab } from "./components/ChatTab";
import { VoiceTab } from "./components/VoiceTab";

type Tab = "inbox" | "voice" | "chat";

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("inbox");
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);
  const { data: emails } = useEmails();
  const processEmail = useProcessEmail();

  const pendingCount = emails?.filter((e) => e.processing_status === "pending").length ?? 0;

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-md bg-indigo-600 flex items-center justify-center">
              <span className="text-white text-sm font-bold">G</span>
            </div>
            <div>
              <h1 className="text-base font-semibold text-gray-900">Goodlane Inbox</h1>
              <p className="text-xs text-gray-400">Freight Broker Assistant</p>
            </div>
          </div>

          {/* Tab switcher */}
          <nav className="flex items-center gap-1 ml-4 bg-gray-100 rounded-lg p-0.5">
            {(["inbox", "voice", "chat"] as Tab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => {
                  setActiveTab(tab);
                  if (tab !== "inbox") setSelectedEmailId(null);
                }}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  activeTab === tab
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {tab === "inbox" ? "Inbox" : tab === "voice" ? "Voice Calls" : "Agent Test"}
              </button>
            ))}
          </nav>
        </div>

        {/* Process button — only shown on inbox tab */}
        {activeTab === "inbox" && (
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

      {/* Tab content */}
      {activeTab === "inbox" ? (
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
      ) : activeTab === "voice" ? (
        <div className="flex flex-1 overflow-hidden">
          <VoiceTab />
        </div>
      ) : (
        <div className="flex-1 overflow-hidden">
          <ChatTab />
        </div>
      )}
    </div>
  );
}
