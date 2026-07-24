/** @type {import('next').NextConfig} */
const nextConfig = process.env.STATIC_EXPORT === "true"
    ? {
        // The root Docker image serves this static UI from FastAPI.
        output: "export",
    }
    : {
        // A separately deployed Next.js service proxies /api to FastAPI.
        async rewrites() {
            const apiUrl = (process.env.API_URL || "http://localhost:8000").replace(/\/$/, "");
            return [
                {
                    source: "/api/:path*",
                    destination: `${apiUrl}/:path*`,
                },
            ];
        },
    };

export default nextConfig;
