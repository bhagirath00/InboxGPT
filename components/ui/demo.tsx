import { LiquidMetalButton } from "@/components/ui/liquid-metal-button";
import { OutlineButton } from "@/components/ui/outline-button";
import { AgentButton } from "@/components/ui/agent-button";

export default function ButtonShowcaseDemo() {
  return (
    <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center gap-10 p-8">
      {/* Agent Section: Liquid Metal Button */}
      <div className="flex flex-col items-center gap-3">
        <span className="text-xs uppercase tracking-widest text-zinc-500 font-mono">
          Agent Button (Liquid Metal Shader)
        </span>
        <div className="flex items-center gap-6">
          <AgentButton label="Agent" />
          <LiquidMetalButton label="Get Started" />
          <LiquidMetalButton viewMode="icon" />
        </div>
      </div>

      {/* Rest All Buttons: Clean Outline Style (Image 2 - No icons, No download keyword) */}
      <div className="flex flex-col items-center gap-3">
        <span className="text-xs uppercase tracking-widest text-zinc-500 font-mono">
          All Other Buttons (Clean Single Outline - Image 2)
        </span>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <OutlineButton label="Sync" />
          <OutlineButton label="Switch Account" />
          <OutlineButton label="Help" />
          <OutlineButton label="Priority" />
          <OutlineButton label="Newsletters" />
          <OutlineButton label="Archive" />
          <OutlineButton label="Cancel" />
        </div>
      </div>
    </div>
  );
}
