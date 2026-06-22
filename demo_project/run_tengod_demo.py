"""
TenGod Demo Server
Main entry point for running the demo
"""
import os
import sys
import json
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tengod import create_app
from tengod.config import Config


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="TenGod Demo Server")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of workers (default: 1)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config file"
    )
    parser.add_argument(
        "--enable-cors",
        action="store_true",
        help="Enable CORS"
    )
    parser.add_argument(
        "--cors-origins",
        type=str,
        default="*",
        help="CORS allowed origins (comma-separated)"
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=8765,
        help="MCP server port (default: 8765)"
    )
    parser.add_argument(
        "--enable-mcp",
        action="store_true",
        help="Enable MCP server"
    )
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    # Load config if provided
    if args.config:
        config = Config.from_file(args.config)
    else:
        config = Config()
    
    # Override config with CLI args
    config.host = args.host
    config.port = args.port
    config.debug = args.debug
    config.log_level = args.log_level
    config.enable_cors = args.enable_cors
    config.cors_origins = args.cors_origins.split(",") if args.cors_origins != "*" else ["*"]
    config.mcp_port = args.mcp_port
    config.enable_mcp = args.enable_mcp
    
    print(f"Starting TenGod Demo Server v1.5.0")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Debug: {args.debug}")
    print(f"Log Level: {args.log_level}")
    
    # Create and run app
    app = create_app(config)
    
    if args.debug or args.reload:
        import uvicorn
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower(),
            reload=args.reload
        )
    else:
        import uvicorn
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level=args.log_level.lower(),
            workers=args.workers
        )


if __name__ == "__main__":
    main()
