"""Opt-in stdio entrypoint for approved authenticated GAIA live tools."""

import os

import anyio

from .cli import serve

anyio.run(serve, os.environ)
