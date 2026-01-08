"""
HTTP Monitoring Server
Provides health check, metrics, and status endpoints for production monitoring
"""
import asyncio
import json
import logging
from aiohttp import web, web_response
from core.monitoring import (
    health_endpoint, metrics_endpoint, status_endpoint,
    ready_endpoint, live_endpoint, setup_monitoring
)

logger = logging.getLogger(__name__)

class MonitoringServer:
    """HTTP server for monitoring endpoints"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.app = None

    def create_app(self) -> web.Application:
        """Create aiohttp application with monitoring routes"""
        app = web.Application()

        # Health check routes
        app.router.add_get('/health', self.handle_health)
        app.router.add_get('/health/ready', self.handle_ready)
        app.router.add_get('/health/live', self.handle_live)

        # Metrics and status
        app.router.add_get('/metrics', self.handle_metrics)
        app.router.add_get('/status', self.handle_status)

        # Root endpoint
        app.router.add_get('/', self.handle_root)

        self.app = app
        return app

    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        try:
            health_data = await health_endpoint()
            status_code = 200 if health_data["status"] == "healthy" else 503

            return web.json_response(health_data, status=status_code)

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.json_response({
                "status": "unhealthy",
                "error": str(e)
            }, status=500)

    async def handle_ready(self, request: web.Request) -> web.Response:
        """Kubernetes readiness probe"""
        try:
            ready_data = await ready_endpoint()
            status_code = 200 if ready_data["ready"] else 503

            return web.json_response(ready_data, status=status_code)

        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return web.json_response({
                "ready": False,
                "error": str(e)
            }, status=500)

    async def handle_live(self, request: web.Request) -> web.Response:
        """Kubernetes liveness probe"""
        try:
            live_data = await live_endpoint()
            return web.json_response(live_data, status=200)

        except Exception as e:
            logger.error(f"Liveness check failed: {e}")
            return web.json_response({
                "alive": False,
                "error": str(e)
            }, status=500)

    async def handle_metrics(self, request: web.Request) -> web.Response:
        """Prometheus metrics endpoint"""
        try:
            from prometheus_client import CONTENT_TYPE_LATEST
            metrics_data = await metrics_endpoint()

            return web.Response(
                text=metrics_data,
                content_type=CONTENT_TYPE_LATEST,
                status=200
            )

        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            return web.Response(
                text=f"# Error collecting metrics: {e}",
                content_type="text/plain",
                status=500
            )

    async def handle_status(self, request: web.Request) -> web.Response:
        """Detailed system status endpoint"""
        try:
            status_data = await status_endpoint()
            return web.json_response(status_data, status=200)

        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return web.json_response({
                "error": str(e)
            }, status=500)

    async def handle_root(self, request: web.Request) -> web.Response:
        """Root endpoint with available routes"""
        return web.json_response({
            "service": "DepegAlert Monitoring",
            "version": "2.0.0",
            "endpoints": {
                "/health": "Comprehensive health check",
                "/health/ready": "Kubernetes readiness probe",
                "/health/live": "Kubernetes liveness probe",
                "/metrics": "Prometheus metrics",
                "/status": "Detailed system status"
            }
        })

    async def start(self):
        """Start the monitoring server"""
        setup_monitoring()

        if not self.app:
            self.create_app()

        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"Monitoring server started on {self.host}:{self.port}")
        logger.info("Available endpoints:")
        logger.info(f"  Health: http://{self.host}:{self.port}/health")
        logger.info(f"  Metrics: http://{self.host}:{self.port}/metrics")
        logger.info(f"  Status: http://{self.host}:{self.port}/status")

        return runner

async def run_monitoring_server():
    """Run the monitoring server as a standalone service"""
    import os

    # Configuration from environment
    host = os.getenv("MONITORING_HOST", "0.0.0.0")
    port = int(os.getenv("MONITORING_PORT", "8080"))

    server = MonitoringServer(host=host, port=port)
    runner = await server.start()

    try:
        # Keep the server running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down monitoring server...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run the monitoring server
    asyncio.run(run_monitoring_server())