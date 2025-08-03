"""
Telemetry imports for Workflow Agent  
统一的遥测组件导入 - 处理不同环境的导入路径
"""

# 尝试导入遥测组件，提供多种fallback策略
try:
    # 尝试直接导入shared.telemetry（当PYTHONPATH设置正确时）
    from shared.telemetry import setup_telemetry, TrackingMiddleware, MetricsMiddleware
except ImportError:
    try:
        # 如果直接导入失败，尝试添加路径后导入
        import sys
        from pathlib import Path
        
        # 添加backend目录到Python路径
        backend_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(backend_dir))
        
        # 添加shared目录到路径
        shared_path = backend_dir / "shared"
        if str(shared_path) not in sys.path:
            sys.path.insert(0, str(shared_path))
        
        from shared.telemetry import setup_telemetry, TrackingMiddleware, MetricsMiddleware
    except ImportError:
        try:
            # 尝试直接从telemetry模块导入
            from telemetry import setup_telemetry, TrackingMiddleware, MetricsMiddleware
        except ImportError:
            # 最后的fallback - 创建stub实现，确保服务可以启动
            print("Warning: Could not import telemetry components, using stubs")
            
            def setup_telemetry(*args, **kwargs):
                """Stub implementation for telemetry setup"""
                pass
            
            class TrackingMiddleware:
                """Stub implementation for tracking middleware"""
                def __init__(self, app):
                    pass
                
                async def __call__(self, request, call_next):
                    return await call_next(request)
            
            class MetricsMiddleware:
                """Stub implementation for metrics middleware"""
                def __init__(self, app, **kwargs):
                    pass
                
                async def __call__(self, request, call_next):
                    return await call_next(request)

__all__ = [
    "setup_telemetry",
    "TrackingMiddleware", 
    "MetricsMiddleware"
]