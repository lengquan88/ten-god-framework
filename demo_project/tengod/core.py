"""
TenGod Core Module
Provides core functionality for the Chinese fortune telling system
"""
import os
import uuid
from typing import Any, Dict, Optional
from datetime import datetime


def generate_request_id() -> str:
    """Generate a unique request ID"""
    return f"tgd_{uuid.uuid4().hex[:12]}"


class Core:
    """TenGod Core Engine"""
    
    VERSION = "1.5.0"
    BUILD = "20250622"
    AUTHOR = "TenGod Team"
    
    def __init__(self):
        """Initialize the core engine"""
        self._initialized = False
        self._request_count = 0
        self._modules = {}
    
    def initialize(self) -> None:
        """Initialize the core engine and all modules"""
        if self._initialized:
            return
        
        self._initialized = True
        print(f"[TenGod Core v{self.VERSION}] Initialized")
    
    def run(self) -> Dict[str, Any]:
        """Run the core engine and return initialization status"""
        self.initialize()
        
        return {
            "version": self.VERSION,
            "build": self.BUILD,
            "author": self.AUTHOR,
            "status": "running" if self._initialized else "not_initialized",
            "request_count": self._request_count,
            "init_steps": [
                "core_initialized",
                "modules_loaded",
                "api_ready"
            ]
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Get core information"""
        return {
            "version": self.VERSION,
            "build": self.BUILD,
            "author": self.AUTHOR,
            "initialized": self._initialized,
            "request_count": self._request_count
        }
    
    def process(self, request_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request"""
        self._request_count += 1
        
        return {
            "request_id": request_id,
            "status": "processed",
            "timestamp": datetime.now().isoformat(),
            "data": data
        }


# Global core instance
_core_instance: Optional[Core] = None


def get_core() -> Core:
    """Get or create the global core instance"""
    global _core_instance
    if _core_instance is None:
        _core_instance = Core()
    return _core_instance


def create_app(config: Any = None):
    """Create the FastAPI application"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(
        title="TenGod API",
        description="Chinese Fortune Telling System API",
        version="1.5.0"
    )
    
    # CORS middleware
    if config and hasattr(config, 'enable_cors') and config.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins if hasattr(config, 'cors_origins') else ["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "version": "1.5.0",
            "timestamp": datetime.now().isoformat()
        }
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "TenGod API",
            "version": "1.5.0",
            "status": "running"
        }
    
    @app.get("/api/v1/version")
    async def get_version():
        """Get API version"""
        return {
            "version": "1.5.0",
            "build": "20250622",
            "author": "TenGod Team"
        }
    
    return app


# ============================================================================
# 兼容性别名（v2.16.1 —— 向后兼容旧版模块引用）
# ============================================================================
TenGodCore = Core
