"""REST API server commands for Minitrino CLI."""

import click
import logging

from minitrino import utils
from minitrino.core.context import MinitrinoContext
from minitrino.server.api import create_app


@click.command(
    "server",
    help="Start the Minitrino REST API server.",
)
@click.option(
    "--host",
    default="127.0.0.1",
    type=str,
    help="Host to bind the server to (default: 127.0.0.1).",
)
@click.option(
    "--port",
    default=8000,
    type=int,
    help="Port to bind the server to (default: 8000).",
)
@click.option(
    "--reload",
    is_flag=True,
    default=False,
    help="Enable auto-reload for development.",
)
@utils.exception_handler
@utils.pass_environment()
def cli(
    ctx: MinitrinoContext,
    host: str,
    port: int,
    reload: bool,
) -> None:
    """
    Start the Minitrino REST API server.

    Parameters
    ----------
    host : str
        Host to bind the server to.
    port : int
        Port to bind the server to.
    reload : bool
        If True, enables auto-reload for development.

    Notes
    -----
    Starts a FastAPI server that exposes REST endpoints for Minitrino
    cluster operations. The server provides the same functionality as
    the CLI commands but through HTTP API calls.
    """
    ctx.initialize()
    
    try:
        import uvicorn
    except ImportError:
        raise click.ClickException(
            "uvicorn is required to run the server. "
            "Install it with: pip install uvicorn[standard]"
        )
    
    app = create_app(ctx)
    
    ctx.logger.info(f"Starting Minitrino API server at http://{host}:{port}")
    ctx.logger.info(f"API documentation available at http://{host}:{port}/docs")
    
    # Reset logger class to avoid conflicts with Minitrino's custom logging
    original_logger_class = logging.getLoggerClass()
    logging.setLoggerClass(logging.Logger)
    
    try:
        # Disable uvicorn's access log to avoid conflicts
        log_config = uvicorn.config.LOGGING_CONFIG.copy()
        log_config["loggers"]["uvicorn.access"]["handlers"] = []
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level="info" if ctx.user_log_level.name == "DEBUG" else "warning",
            log_config=log_config,
        )
    finally:
        # Restore the original logger class
        logging.setLoggerClass(original_logger_class)
