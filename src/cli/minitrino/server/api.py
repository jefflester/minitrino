"""FastAPI application and routes for Minitrino REST API."""

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from minitrino.core.context import MinitrinoContext
from minitrino.core.errors import MinitrinoError, UserError


class ProvisionRequest(BaseModel):
    """Request model for cluster provisioning."""
    
    modules: list[str] = Field(
        default=[],
        description="List of modules to provision in the cluster",
        example=["postgres", "mysql"]
    )
    image: str = Field(
        default="trino",
        description="Cluster image type (trino or starburst)",
        example="trino"
    )
    workers: int = Field(
        default=0,
        ge=0,
        description="Number of cluster workers to provision",
        example=2
    )
    no_rollback: bool = Field(
        default=False,
        description="Disable cluster rollback if provisioning fails",
        example=False
    )
    cluster_name: Optional[str] = Field(
        default=None,
        description="Name for the cluster (defaults to 'default')",
        example="my-cluster"
    )


class ProvisionResponse(BaseModel):
    """Response model for cluster provisioning."""
    
    success: bool = Field(description="Whether the provisioning was successful")
    message: str = Field(description="Status message")
    cluster_name: str = Field(description="Name of the provisioned cluster")
    modules: list[str] = Field(description="List of provisioned modules")
    image: str = Field(description="Cluster image type used")
    workers: int = Field(description="Number of workers provisioned")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(description="Error message")
    details: Optional[str] = Field(default=None, description="Additional error details")


def create_app(base_ctx: MinitrinoContext) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Parameters
    ----------
    base_ctx : MinitrinoContext
        The base Minitrino context to use for operations.
        
    Returns
    -------
    FastAPI
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Minitrino API",
        description="REST API for Minitrino cluster management",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    @app.get("/")
    async def root():
        """Root endpoint providing API information."""
        return {
            "name": "Minitrino API",
            "version": "1.0.0",
            "description": "REST API for Minitrino cluster management",
            "documentation": "/docs"
        }
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "service": "minitrino-api"}
    
    @app.post(
        "/provision",
        response_model=ProvisionResponse,
        responses={
            400: {"model": ErrorResponse, "description": "Bad Request"},
            500: {"model": ErrorResponse, "description": "Internal Server Error"}
        }
    )
    async def provision_cluster(request: ProvisionRequest):
        """
        Provision a Minitrino cluster with optional modules.
        
        This endpoint provides the same functionality as the 
        `minitrino provision` CLI command.
        """
        try:
            # Create a new context for this request to avoid state pollution
            ctx = MinitrinoContext()
            
            # Copy relevant settings from base context
            ctx._user_env_args = base_ctx._user_env_args
            ctx.user_log_level = base_ctx.user_log_level
            ctx.logger = base_ctx.logger
            
            # Set cluster name if provided
            if request.cluster_name:
                ctx.cluster_name = request.cluster_name
            
            # Initialize the context
            ctx.initialize()
            
            # Validate request parameters
            if request.image not in ["trino", "starburst"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid image type '{request.image}'. Must be 'trino' or 'starburst'."
                )
            
            # Provision the cluster using the same logic as CLI
            modules_list = list(request.modules)
            ctx.cluster.ops.provision(
                modules_list,
                request.image,
                request.workers,
                request.no_rollback
            )
            
            return ProvisionResponse(
                success=True,
                message=f"Successfully provisioned cluster '{ctx.cluster_name}'",
                cluster_name=ctx.cluster_name,
                modules=modules_list,
                image=request.image,
                workers=request.workers
            )
            
        except UserError as e:
            # User errors are client-side issues (400)
            ctx.logger.error(f"User error during provisioning: {e}")
            raise HTTPException(
                status_code=400,
                detail={"success": False, "error": str(e), "details": e.hint if hasattr(e, 'hint') else None}
            )
            
        except MinitrinoError as e:
            # Minitrino errors are server-side issues (500)
            ctx.logger.error(f"Minitrino error during provisioning: {e}")
            raise HTTPException(
                status_code=500,
                detail={"success": False, "error": str(e)}
            )
            
        except Exception as e:
            # Unexpected errors
            ctx.logger.error(f"Unexpected error during provisioning: {e}")
            raise HTTPException(
                status_code=500,
                detail={"success": False, "error": "Internal server error", "details": str(e)}
            )
    
    return app
