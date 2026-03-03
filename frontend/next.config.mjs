/** @type {import('next').NextConfig} */
const nextConfig = {
    // Proxy API calls to the FastAPI backend during development
    async rewrites() {
        return [
            {
                source: "/api/:path*",
                destination: "http://localhost:8000/:path*",
            },
        ];
    },
};

export default nextConfig;
