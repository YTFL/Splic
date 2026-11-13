import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const projectRoot = fileURLToPath(new URL(".", import.meta.url));

const agentDiscoveryLinkHeader = [
  '</agent-guide.md>; rel="service-doc"; type="text/markdown"; title="Timeline Studio agent guide"',
  '</.well-known/agent-skills/index.json>; rel="https://agentskills.io/discovery"; type="application/json"',
  '</llms.txt>; rel="describedby"; type="text/plain"',
].join(", ");

const isolationHeaders = [
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Cross-Origin-Embedder-Policy", value: "require-corp" },
  { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
  { key: "Link", value: agentDiscoveryLinkHeader },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: isolationHeaders,
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
      {
        source: "/dynamic_stickers/:path*",
        destination: "http://localhost:8000/dynamic_stickers/:path*",
      },
    ];
  },
  webpack: (config, { webpack, isServer }) => {
    config.experiments = {
      ...config.experiments,
      asyncWebAssembly: true,
      layers: true,
    };

    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        path: false,
        url: false,
        module: false,
      };
    }

    // Polyfill import.meta.env for Next.js/Webpack
    config.plugins.push(
      new webpack.DefinePlugin({
        "import.meta.env": JSON.stringify({
          ...Object.fromEntries(
            Object.entries(process.env).filter(([k]) => k.startsWith("VITE_") || k.startsWith("NEXT_PUBLIC_"))
          ),
          DEV: process.env.NODE_ENV !== "production",
          PROD: process.env.NODE_ENV === "production",
          MODE: process.env.NODE_ENV || "development",
          VITE_PEXELS_API_KEY: process.env.VITE_PEXELS_API_KEY || "",
        }),
      })
    );

    // Alias package subpaths directly to files to bypass package.json "exports" restrictions on query strings
    config.resolve.alias = {
      ...config.resolve.alias,
      "@ffmpeg/core$": resolve(projectRoot, "node_modules/@ffmpeg/core/dist/esm/ffmpeg-core.js"),
      "@ffmpeg/core/wasm$": resolve(projectRoot, "node_modules/@ffmpeg/core/dist/esm/ffmpeg-core.wasm"),
      "@ffmpeg/ffmpeg/worker$": resolve(projectRoot, "node_modules/@ffmpeg/ffmpeg/dist/esm/worker.js"),
      "onnxruntime-web/ort-wasm-simd-threaded.asyncify.mjs$": resolve(projectRoot, "node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.asyncify.mjs"),
      "onnxruntime-web/ort-wasm-simd-threaded.asyncify.wasm$": resolve(projectRoot, "node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.asyncify.wasm"),
      "onnxruntime-web/ort-wasm-simd-threaded.mjs$": resolve(projectRoot, "node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.mjs"),
      "onnxruntime-web/ort-wasm-simd-threaded.wasm$": resolve(projectRoot, "node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.wasm"),
      "@mediapipe/tasks-vision/vision_wasm_module_internal.js$": resolve(projectRoot, "node_modules/@mediapipe/tasks-vision/wasm/vision_wasm_module_internal.js"),
      "@mediapipe/tasks-vision/vision_wasm_module_internal.wasm$": resolve(projectRoot, "node_modules/@mediapipe/tasks-vision/wasm/vision_wasm_module_internal.wasm"),
    };

    // Treat ?url queries and WASM binaries as asset/resource
    config.module.rules.push({
      resourceQuery: /url/,
      type: "asset/resource",
    });

    config.module.rules.push({
      test: /\.wasm$/,
      type: "asset/resource",
    });

    return config;
  },
};

export default nextConfig;
