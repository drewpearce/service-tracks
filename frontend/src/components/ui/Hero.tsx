import { type ReactNode } from "react";

interface HeroProps {
  children: ReactNode;
  className?: string;
}

export default function Hero({ children, className = "" }: HeroProps) {
  return (
    <section
      className={`text-white relative overflow-hidden ${className}`}
      style={{
        background:
          "radial-gradient(60% 60% at 0% 0%, rgba(20,184,166,0.18) 0%, transparent 60%), radial-gradient(40% 50% at 100% 0%, rgba(244,63,94,0.14) 0%, transparent 60%), #0F172A",
      }}
    >
      <div className="relative px-10 pt-10 pb-14 max-w-5xl">{children}</div>
    </section>
  );
}
