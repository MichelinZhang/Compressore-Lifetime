import { Terminal } from "lucide-react";

type Props = {
  message: string;
  simulation: boolean;
};

export function SystemTicker({ message, simulation }: Props) {
  return (
    <div className="pointer-events-none fixed bottom-6 left-1/2 z-50 flex h-12 w-[760px] max-w-[92vw] -translate-x-1/2 items-center overflow-hidden rounded-full border border-white/10 bg-black/60 px-4 shadow-2xl backdrop-blur-2xl">
      <Terminal className="mr-3 h-4 w-4 shrink-0 text-white/40" />
      <div className="flex-1 truncate font-mono text-[11px] text-white/70">{message}</div>
      <div className={`ml-3 h-2 w-2 shrink-0 animate-pulse rounded-full ${simulation ? "bg-orange-500" : "bg-emerald-500"}`} />
    </div>
  );
}

