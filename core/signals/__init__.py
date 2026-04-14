"""Trend signal helpers live in ``google_trends`` and ``reddit`` submodules.

Avoid aggregating imports here: ``from core.signals.reddit import …`` loads this
file first; eager re-exports would create a circular import with ``core.topics``.
"""
