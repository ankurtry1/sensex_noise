"""Offline research pipeline for tail-loss calibration analysis."""


def run_pipeline(*args, **kwargs):
    from .cli import run_pipeline as _run_pipeline

    return _run_pipeline(*args, **kwargs)


__all__ = ["run_pipeline"]
