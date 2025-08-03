"""
Telemetry imports for Workflow Engine
统一的遥测组件导入 - 处理不同环境的导入路径
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Type

# 类型检查时导入真实类型
if TYPE_CHECKING:
    try:
        from shared.telemetry import TrackingMiddleware as _TrackingMiddleware
        from shared.telemetry import MetricsMiddleware as _MetricsMiddleware
        from shared.telemetry import setup_telemetry as _setup_telemetry
    except ImportError:
        # 如果导入失败，定义基本类型
        from typing import Protocol
        
        class _TrackingMiddleware(Protocol):
            def __init__(self, app: Any) -> None: ...
            async def __call__(self, request: Any, call_next: Any) -> Any: ...
        
        class _MetricsMiddleware(Protocol):
            def __init__(self, app: Any, **kwargs: Any) -> None: ...
            async def __call__(self, request: Any, call_next: Any) -> Any: ...
        
        def _setup_telemetry(*args: Any, **kwargs: Any) -> None: ...

# 运行时导入逻辑
_telemetry_imported = False
setup_telemetry: Callable[..., None]
TrackingMiddleware: Type[Any]
MetricsMiddleware: Type[Any]

try:
    # 尝试直接导入shared.telemetry（当PYTHONPATH设置正确时）
    from shared.telemetry import setup_telemetry, TrackingMiddleware, MetricsMiddleware
    _telemetry_imported = True
except ImportError:
    try:
        # 如果直接导入失败，尝试添加路径后导入
        # 添加backend目录到Python路径
        backend_dir = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(backend_dir))
        
        # 添加shared目录到路径
        shared_path = backend_dir / "shared"
        if str(shared_path) not in sys.path:
            sys.path.insert(0, str(shared_path))
        
        from shared.telemetry import setup_telemetry, TrackingMiddleware, MetricsMiddleware
        _telemetry_imported = True
    except ImportError:
        try:
            # 尝试直接从telemetry模块导入
            from telemetry import setup_telemetry, TrackingMiddleware, MetricsMiddleware  # type: ignore
            _telemetry_imported = True
        except ImportError:
            # 最后的fallback - 创建stub实现，确保服务可以启动
            print("Warning: Could not import telemetry components, using stubs")
            _telemetry_imported = False
            
            def setup_telemetry(*args: Any, **kwargs: Any) -> None:
                """Stub implementation for telemetry setup"""
                pass
            
            class TrackingMiddleware:  # type: ignore
                """Stub implementation for tracking middleware"""
                def __init__(self, app: Any) -> None:
                    pass
                
                async def __call__(self, request: Any, call_next: Any) -> Any:
                    return await call_next(request)
            
            class MetricsMiddleware:  # type: ignore
                """Stub implementation for metrics middleware"""
                def __init__(self, app: Any, **kwargs: Any) -> None:
                    pass
                
                async def __call__(self, request: Any, call_next: Any) -> Any:
                    return await call_next(request)

__all__ = [
    "setup_telemetry",
    "TrackingMiddleware", 
    "MetricsMiddleware"
]