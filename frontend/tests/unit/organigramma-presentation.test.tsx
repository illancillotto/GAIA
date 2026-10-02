import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { AssignmentInboxPanel, SchemaNodeCard, TreeNode } from "@/features/organigramma/organigramma-workspace";
import type { ApplicationUser, OrgUnitTreeNode } from "@/types/api";

const node: OrgUnitTreeNode = { id: "node", nome: "Settore", tipo: "settore", parent_id: null, children: [], source: "manuale", is_active: true, wc_area_id: null, legacy_team_id: null, sort_order: 0, person_count: 3, child_count: 0, canvas_x: 0, canvas_y: 0 };

function cardProps(): React.ComponentProps<typeof SchemaNodeCard> {
  return { node, displayPosition: { x: 0, y: 0 }, offsetX: 120, offsetY: 120, selectedId: null, isMultiSelected: false,
    collapsed: false, collapsedChildNames: null, onToggleCollapse: vi.fn(), onSelect: vi.fn(), onOpenPerson: vi.fn(),
    draggingUserId: null, userDropMode: "member", linkDraft: null, draggingNodeId: null, onCardPointerDown: vi.fn(),
    onCardContextMenu: vi.fn(), onConnectNode: vi.fn(), onDetachParent: vi.fn(), onBeginLink: vi.fn(), onAssignUser: vi.fn(),
    meta: new Map(), canManage: false, animated: false };
}

describe("schema card presentation contract", () => {
  test("uses the node's people count when enrichment is absent", () => {
    render(<SchemaNodeCard {...cardProps()} />);
    expect(screen.getByText("diretti 3")).toBeInTheDocument();
    expect(screen.getAllByText("Settore")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "Apri scheda responsabile" })).not.toBeInTheDocument();
  });

  test.each([null, []])("renders a collapsed card without an available child-name preview (%j)", collapsedChildNames => {
    const props = { ...cardProps(), collapsed: true, collapsedChildNames };
    render(<SchemaNodeCard {...props} />);
    expect(screen.getByText("Gruppo compresso")).toBeInTheDocument();
    expect(screen.queryByText(/altre$/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Esplodi (+1)" }));
    expect(props.onToggleCollapse).toHaveBeenCalledWith("node");
  });

  test("does not treat a drop without an operator drag as an assignment", () => {
    const props = cardProps();
    render(<SchemaNodeCard {...props} />);
    const card = screen.getByTestId("schema-node-node");
    expect(fireEvent.dragOver(card)).toBe(true);
    fireEvent.drop(card);
    expect(props.onAssignUser).not.toHaveBeenCalled();
  });

  test("keeps selection unchanged when clicking a card during a link gesture", () => {
    const props = { ...cardProps(), linkDraft: { sourceId: "node", mode: "above" as const } };
    render(<SchemaNodeCard {...props} />);
    fireEvent.click(screen.getByTestId("schema-node-node"));
    expect(props.onSelect).not.toHaveBeenCalled();
    expect(props.onConnectNode).not.toHaveBeenCalled();
  });
});

describe("recursive tree presentation contract", () => {
  test("hides provenance and cannot expand a leaf", () => {
    const props: React.ComponentProps<typeof TreeNode> = { node, depth: 0, expanded: new Set(), selectedId: null,
      showProvenance: false, includeIds: new Set(), matchIds: new Set(), draggingNodeId: null, draggingUserId: null,
      canManage: false, canAssignPeople: false, userDropMode: "member", onToggle: vi.fn(), onSelect: vi.fn(),
      onDragStart: vi.fn(), onDragEnd: vi.fn(), onMove: vi.fn(), onAssignUser: vi.fn() };
    render(<ul><TreeNode {...props} /></ul>);
    expect(screen.queryByText("Manuale")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Espandi" }));
    fireEvent.keyDown(screen.getByRole("treeitem"), { key: "ArrowRight" });
    expect(props.onToggle).not.toHaveBeenCalled();
    expect(props.onSelect).not.toHaveBeenCalled();
    expect(screen.queryByRole("group")).not.toBeInTheDocument();
  });
});

describe("assignment inbox data enrichment", () => {
  test("supports a selected node before its assignment summary and searches unnamed operators by username", () => {
    const operator = { id: 1, username: "operatore", full_name: null, is_active: true } as ApplicationUser;
    const props: React.ComponentProps<typeof AssignmentInboxPanel> = { selectedNode: node, selectedSummary: null, linkableNodes: [],
      operatorUsers: [operator], assignedUserIds: new Set(), unassignedCount: 1, canModifyStructure: false, editEnabled: false,
      assignMode: "member", onAssignModeChange: vi.fn(), showOnlyUnassignedOperators: false, onToggleShowOnlyUnassignedOperators: vi.fn(),
      emphasizeUnassignedFilter: false, onToggleEdit: vi.fn(), onSelectNode: vi.fn(), onConnectSelectedToNode: vi.fn(),
      onCreateUnit: vi.fn(), onCreateGenericUnit: vi.fn(), onStartDragUser: vi.fn(), onEndDragUser: vi.fn() };
    render(<AssignmentInboxPanel {...props} />);
    expect(screen.getByText("diretti 0")).toBeInTheDocument();
    expect(screen.getByText("sotto-albero 0")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Cerca operatore…"), { target: { value: "operatore" } });
    expect(screen.getByText("operatore")).toBeInTheDocument();
    expect(within(screen.getByText("operatore").closest("[draggable]")!).queryByText("Mario Sanna")).not.toBeInTheDocument();
    expect(props.onStartDragUser).not.toHaveBeenCalled();
  });
});
