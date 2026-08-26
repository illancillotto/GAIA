"use client";

import { Fragment } from "react";

import { NavItem } from "@/components/layout/nav-item";
import { type CurrentModuleKey, getModuleSections } from "@/components/layout/navigation";

type ModuleSidebarProps = {
  currentModuleKey: CurrentModuleKey;
  reviewBadge?: number;
  userBadge?: number;
  grantedSectionKeys?: string[];
  currentUserRole?: string;
};

export function ModuleSidebar({
  currentModuleKey,
  reviewBadge = 0,
  userBadge = 0,
  grantedSectionKeys = [],
  currentUserRole,
}: ModuleSidebarProps) {
  const sections = getModuleSections({
    currentModuleKey,
    reviewBadge,
    userBadge,
    grantedSectionKeys,
    currentUserRole,
  });

  return (
    <div className="space-y-0.5 px-2 pb-3">
      {sections.map((section) => (
        <Fragment key={section.label}>
          <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-600">{section.label}</p>
          {section.items.map((navItem) => (
            <NavItem key={navItem.href} {...navItem} />
          ))}
        </Fragment>
      ))}
    </div>
  );
}
