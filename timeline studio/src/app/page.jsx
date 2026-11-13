"use client";

import dynamic from "next/dynamic";
import React from "react";

const EditorRoot = dynamic(() => import("../EditorRoot.jsx"), {
  ssr: false,
});

export default function Page() {
  return <EditorRoot />;
}
