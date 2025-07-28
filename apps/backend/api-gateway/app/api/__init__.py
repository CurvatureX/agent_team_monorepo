# API Routes Package - Three-layer Architecture
# 三层API路由

# This package contains three API layers:
# - public: Public endpoints (no auth required)
# - app: Application endpoints (Supabase JWT auth)
# - mcp: MCP endpoints (API key auth)

# Each layer is self-contained - import routers directly from submodules
