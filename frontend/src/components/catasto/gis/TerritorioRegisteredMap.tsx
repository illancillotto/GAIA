"use client";

import dynamic from "next/dynamic";
import type { ComponentProps } from "react";
import type MapContainerType from "./MapContainer";

import "./territorio-map-registry";

const MapContainer = dynamic(() => import("./MapContainer"), { ssr: false });

export type TerritorioRegisteredMapProps = ComponentProps<typeof MapContainerType>;

export default function TerritorioRegisteredMap(props: TerritorioRegisteredMapProps) {
  return <MapContainer {...props} />;
}
