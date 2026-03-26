declare module "react-draggable" {
  import type { ComponentType, ReactNode } from "react";

  type Position = {
    x: number;
    y: number;
  };

  type DraggableProps = {
    children: ReactNode;
    defaultPosition?: Position;
    disabled?: boolean;
  };

  const Draggable: ComponentType<DraggableProps>;
  export default Draggable;
}
