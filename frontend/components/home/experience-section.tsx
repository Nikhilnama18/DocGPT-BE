import { type ReactNode } from "react";

type ExperienceSectionProps = {
  children: ReactNode;
  description: string;
  eyebrow: string;
  title: string;
};

export function ExperienceSection({
  children,
  description,
  eyebrow,
  title,
}: ExperienceSectionProps) {
  return (
    <section className="grid gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(22rem,0.9fr)] lg:items-start">
      <div className="lg:col-span-2">
        <p className="text-xs uppercase tracking-[0.32em] text-[color:var(--accent)]">
          {eyebrow}
        </p>
        <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <h2 className="font-display text-3xl text-[color:var(--foreground)] sm:text-4xl">
            {title}
          </h2>
          <p className="max-w-2xl text-sm leading-6 text-[color:var(--muted)] sm:text-base">
            {description}
          </p>
        </div>
      </div>
      {children}
    </section>
  );
}
