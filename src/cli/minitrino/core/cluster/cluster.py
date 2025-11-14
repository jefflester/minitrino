"""Cluster interface and operations for Minitrino clusters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from minitrino.core.cluster.ops import ClusterOperations
from minitrino.core.cluster.ports import ClusterPortManager
from minitrino.core.cluster.resource import ClusterResourceManager
from minitrino.core.cluster.validator import ClusterValidator

if TYPE_CHECKING:
    from minitrino.core.context import MinitrinoContext


class Cluster:
    """Exposes various cluster operations.

    Parameters
    ----------
    ctx : MinitrinoContext
        An instantiated MinitrinoContext object with user input and
        context.

    Attributes
    ----------
    ops : ClusterOperations
        A cluster operations manager for the current cluster.
    ports : ClusterPortManager
        A cluster port manager for the current cluster.
    resource : ClusterResourceManager
        A cluster resource manager for the current cluster.
    validator : ClusterValidator
        A validator for the current cluster.
    """

    def __init__(self, ctx: MinitrinoContext):
        self._ctx = ctx
        self.ops = ClusterOperations(ctx, self)
        self.ports = ClusterPortManager(ctx, self)
        self.resource = ClusterResourceManager(ctx)
        self.validator = ClusterValidator(ctx, self)
