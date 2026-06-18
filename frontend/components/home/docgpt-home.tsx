"use client";

import { useState } from "react";
import { DocumentViewerCard } from "@/components/document/document-viewer-card";
import { ExperienceSection } from "@/components/home/experience-section";
import { HeroSection } from "@/components/home/hero-section";
import { QueryPanel } from "@/components/query/query-panel";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { type QueryStrategy } from "@/lib/constants";

export function DocGptHome() {
  const [defaultStrategy, setDefaultStrategy] =
    useState<QueryStrategy>("standard");
  const [uploadStrategy, setUploadStrategy] =
    useState<QueryStrategy>("standard");
  const [defaultQuestion, setDefaultQuestion] = useState("");
  const [uploadQuestion, setUploadQuestion] = useState("");

  return (
    <main className="min-h-screen bg-[color:var(--background)] px-4 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-7xl px-5 py-6 sm:px-8 sm:py-8 lg:px-10 lg:py-10">
        <div className="flex justify-end">
          <ThemeToggle />
        </div>

        <HeroSection />

        <div className="mt-16 space-y-20">
          <ExperienceSection
            eyebrow=""
            title=""
            description=""
          >
            <DocumentViewerCard
              variant="default"
              title="Default document viewer"
            />
            <QueryPanel
              title="Compare retrieval strategies"
              description="Choose how DocGPT should transform the question before retrieval, then submit it against the default document."
              selectedStrategy={defaultStrategy}
              onStrategySelect={setDefaultStrategy}
              question={defaultQuestion}
              onQuestionChange={setDefaultQuestion}
              placeholder="Ask about the seeded document, its themes, or any specific section..."
            />
          </ExperienceSection>

          <ExperienceSection
            eyebrow=""
            title=""
            description=""
          >
            <DocumentViewerCard
              variant="upload"
              title="Upload your document"
            />
            <QueryPanel
              title="Wait for READY status"
              description="The same strategy options stay visible here for continuity, but the textarea and submit button remain disabled until processing finishes."
              selectedStrategy={uploadStrategy}
              onStrategySelect={setUploadStrategy}
              question={uploadQuestion}
              onQuestionChange={setUploadQuestion}
              placeholder="This input unlocks automatically when the backend reports READY."
              disabled
            />
          </ExperienceSection>
        </div>
      </div>
    </main>
  );
}
