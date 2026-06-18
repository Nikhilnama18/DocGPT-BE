import { StrategySelector } from "@/components/query/strategy-selector";
import { type QueryStrategy } from "@/lib/constants";

type QueryPanelProps = {
  description: string;
  disabled?: boolean;
  onQuestionChange: (question: string) => void;
  onStrategySelect: (strategy: QueryStrategy) => void;
  placeholder: string;
  question: string;
  selectedStrategy: QueryStrategy;
  title: string;
};

export function QueryPanel({
  description,
  disabled = false,
  onQuestionChange,
  onStrategySelect,
  placeholder,
  question,
  selectedStrategy,
  title,
}: QueryPanelProps) {
  return (
    <div className="rounded-[2rem] bg-[color:var(--surface-strong)] p-5 page-fade-in-delayed">
      <div className="mb-6">
        <p className="text-xs uppercase tracking-[0.28em] text-[color:var(--accent)]">
          Query translation Strategies
        </p>
        <h3 className="font-display mt-2 text-3xl text-[color:var(--foreground)]">
          {title}
        </h3>
        <p className="mt-3 text-sm leading-6 text-[color:var(--muted)]">
          {description}
        </p>
      </div>

      <StrategySelector
        disabled={disabled}
        onSelect={onStrategySelect}
        selectedStrategy={selectedStrategy}
      />

      <div className="mt-6 space-y-4">
        <label className="block">
          <span className="mb-2 block text-xs uppercase tracking-[0.28em] text-[color:var(--muted)]">
            Ask a question
          </span>
          <textarea
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            rows={5}
            className="min-h-[9rem] w-full rounded-[1.5rem] bg-[color:color-mix(in_srgb,var(--foreground)_3%,var(--background))] px-4 py-4 text-base text-[color:var(--foreground)] outline-none transition placeholder:text-[color:var(--muted)] focus:bg-[color:color-mix(in_srgb,var(--foreground)_4%,var(--background))] disabled:cursor-not-allowed disabled:opacity-55"
          />
        </label>

        <button
          type="button"
          disabled={disabled}
          className="w-full rounded-full bg-[color:var(--accent)] px-5 py-3 font-medium text-black transition hover:brightness-105 disabled:cursor-not-allowed disabled:bg-[color:color-mix(in_srgb,var(--foreground)_6%,var(--background))] disabled:text-[color:var(--muted)]"
        >
          Submit question
        </button>
      </div>

      {/* <div className="mt-6 rounded-[1.4rem] bg-[color:color-mix(in_srgb,var(--foreground)_3%,var(--background))] px-4 py-4">
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm font-medium text-[color:var(--foreground)]">
            {statusLabel ?? "Ready for API wiring"}
          </p>
          {statusLabel ? (
            <span className="text-xs uppercase tracking-[0.28em] text-[color:var(--accent)]">
              Processing
            </span>
          ) : null}
        </div>
        {statusLabel ? (
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-[color:var(--accent-soft)]">
            <div
              className="h-full rounded-full bg-[color:var(--accent)] transition-all"
              style={{ width: `${Math.min(Math.max(statusProgress, 0), 100)}%` }}
            />
          </div>
        ) : null}
        <p className="mt-3 text-sm leading-6 text-[color:var(--muted)]">
          {helperText}
        </p>
      </div> */}
    </div>
  );
}
