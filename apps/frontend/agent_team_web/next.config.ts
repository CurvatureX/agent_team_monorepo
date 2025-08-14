import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/proxy/:path*',
        destination: 'http://agent-prod-alb-352817645.us-east-1.elb.amazonaws.com/api/:path*',
      },
    ];
  },
};

export default nextConfig;
