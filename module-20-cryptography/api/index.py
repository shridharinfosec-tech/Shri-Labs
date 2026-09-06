"""
Vercel serverless entrypoint for the Module 20 Cryptography lab portal.

Vercel's Python runtime accepts a `handler` that subclasses BaseHTTPRequestHandler,
so we reuse the portal's existing request handler unchanged. Every route is sent
here by vercel.json's catch-all rewrite.

Required environment variables on Vercel:
  SUPABASE_URL          https://<project>.supabase.co
  SUPABASE_SERVICE_KEY  the project's service_role key (server-side only)
  SESSION_SECRET        a long random string used to sign session cookies
"""
import os
import sys

# Make Cryptography.py, store.py, .lab/, challenges/ and assets/ importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Cryptography import Handler as handler  # noqa: E402,F401
