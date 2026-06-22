"""Vercel serverless entry point.

Vercel's Python runtime discovers the ASGI ``app`` object exported here. The
GraphRAG engine lives in the repo-root ``graphrag`` package; we add the project
root to ``sys.path`` so the import resolves regardless of how the function is
invoked.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graphrag import create_app  # noqa: E402

app = create_app()
