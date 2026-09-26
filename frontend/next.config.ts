import type { NextConfig } from "next";

<<<<<<< HEAD
const isDev = process.env.NODE_ENV === "development";
// Backend used by `npm run dev` only. Production builds are a static export served by
// FastAPI on the same origin, so the app always calls relative `/api/*` paths.
const DEV_BACKEND = process.env.DEV_BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  images: { unoptimized: true },
  reactStrictMode: true,
  ...(isDev
    ? {
        async rewrites() {
          return [{ source: "/api/:path*", destination: `${DEV_BACKEND}/api/:path*` }];
        },
      }
    : { output: "export" as const }),
=======
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
>>>>>>> 4e94a35bae4b2c154c3398af2e05b336f98fdbde
};

export default nextConfig;
