"""Shared CPU inference budget for detector and embedder."""

import torch

from app.config import TORCH_THREADS


def configure_cpu_threads() -> None:
    # Ultralytics device initialization can overwrite this process-wide setting.
    if torch.get_num_threads() != TORCH_THREADS:
        torch.set_num_threads(TORCH_THREADS)
