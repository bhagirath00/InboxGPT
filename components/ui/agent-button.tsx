import * as React from "react";
import { LiquidMetalButton } from "@/components/ui/liquid-metal-button";

export interface AgentButtonProps {
  label?: string;
  onClick?: () => void;
  viewMode?: "text" | "icon";
}

/**
 * Agent Button using Liquid Metal Shader with zero outer frames or extra boxes.
 */
export const AgentButton: React.FC<AgentButtonProps> = ({
  label = "Agent",
  onClick,
  viewMode = "text",
}) => {
  return (
    <LiquidMetalButton
      label={label}
      onClick={onClick}
      viewMode={viewMode}
    />
  );
};

export default AgentButton;
