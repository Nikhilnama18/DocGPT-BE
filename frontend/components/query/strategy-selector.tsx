import { QUERY_STRATEGIES, type QueryStrategy } from "@/lib/constants";

type StrategySelectorProps = {
  disabled?: boolean;
  onSelect: (strategy: QueryStrategy) => void;
  selectedStrategy: QueryStrategy;
};

export function StrategySelector({
  disabled = false,
  onSelect,
  selectedStrategy,
}: StrategySelectorProps) {
  return (
    <div className="grid gap-2">
      {QUERY_STRATEGIES.map((strategy) => {
        const isSelected = strategy.id === selectedStrategy;

        return (
          <button
            key={strategy.id}
            type="button"
            onClick={() => onSelect(strategy.id)}
            disabled={disabled}
            className={`rounded-2xl px-4 py-3 text-left transition ${
              isSelected
                ? "bg-[color:var(--accent-soft)] text-[color:var(--foreground)] shadow-[inset_0_0_0_1px_color-mix(in_srgb,var(--accent)_55%,transparent)]"
                : "bg-[color:color-mix(in_srgb,var(--foreground)_3%,var(--background))] text-[color:var(--muted)]"
            } ${
              disabled
                ? "cursor-not-allowed opacity-55"
                : isSelected
                  ? "hover:bg-[color:color-mix(in_srgb,var(--accent)_18%,var(--background))] hover:text-[color:var(--foreground)]"
                  : "hover:bg-[color:color-mix(in_srgb,var(--foreground)_4%,var(--background))] hover:text-[color:var(--foreground)]"
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-display text-xl leading-none">
                  {strategy.label}
                </p>
                <p className="mt-2 text-sm leading-6">{strategy.description}</p>
              </div>
              <span
                className={`mt-1 h-3 w-3 rounded-full ${
                  isSelected
                    ? "bg-[color:var(--accent)]"
                    : "bg-[color:color-mix(in_srgb,var(--foreground)_16%,transparent)]"
                }`}
              />
            </div>
          </button>
        );
      })}
    </div>
  );
}
