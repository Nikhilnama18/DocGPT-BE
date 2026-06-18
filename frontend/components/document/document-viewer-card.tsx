type DocumentViewerCardProps = {
  title: string;
  variant: "default" | "upload";
};

export function DocumentViewerCard({
  title,
  variant,
}: DocumentViewerCardProps) {
  const isDefault = variant === "default";

  return (
    <div className="page-fade-in-delayed">
      <div className="rounded-[2rem] bg-[color:var(--surface-strong)] p-4 sm:p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-[color:var(--accent)]">
              {isDefault ? "Seeded document" : "Upload staging"}
            </p>
            <h3 className="font-display mt-2 text-2xl text-[color:var(--foreground)]">
              {title}
            </h3>
          </div>
          {/* <span className="rounded-full bg-[color:color-mix(in_srgb,var(--accent)_8%,transparent)] px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-[color:var(--muted)]">
            {isDefault ? "Ready" : "Waiting"}
          </span> */}
        </div>

        <div className="rounded-[1.6rem] bg-[color:color-mix(in_srgb,var(--foreground)_3%,var(--background))] p-4">
          {isDefault ? (
            <div className="grid gap-3">
              {["Overview", "Narrative context", "Retrieval chunks"].map((section) => (
                <article
                  key={section}
                  className="rounded-[1.2rem] bg-[color:var(--surface)] p-4"
                >
                  <p className="text-[11px] uppercase tracking-[0.28em] text-[color:var(--accent)]">
                    {section}
                  </p>
                  <div className="mt-4 h-20 rounded-2xl bg-[color:var(--accent-soft)]" />
                </article>
              ))}
            </div>
          ) : (
            <div className="flex min-h-[20rem] flex-col items-center justify-center rounded-[1.4rem] bg-[color:var(--surface)] px-6 py-10 text-center">
              <span className="rounded-full bg-[color:var(--accent-soft)] px-3 py-1 text-[11px] uppercase tracking-[0.28em] text-[color:var(--accent)]">
                PDF or DOC under 1 MB
              </span>
              <p className="font-display mt-5 text-3xl text-[color:var(--foreground)]">
                Drag, drop, or browse
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
