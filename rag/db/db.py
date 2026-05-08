from __future__ import annotations

import asyncio
import logging
import os
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse

import asyncpg
from dotenv import load_dotenv

from .halfvec import register_halfvec_codec

_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_REPO_ROOT / ".env")

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None
_pool_lock = asyncio.Lock()


async def _init_connection(conn: asyncpg.Connection) -> None:
    await register_halfvec_codec(conn)


def _dsn() -> str:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        raise RuntimeError(
            "DATABASE_URL is not set. Add it to the repository root .env file."
        )
    url = raw.strip().strip('"').strip("'").lstrip("\ufeff")
    # .env typo: DATABASE_URL=DATABASE_URL=postgresql://...
    dup = "DATABASE_URL="
    while url.startswith(dup):
        url = url[len(dup) :].lstrip()
    if not url.startswith(("postgresql://", "postgres://")):
        raise RuntimeError(
            "DATABASE_URL must start with postgresql:// or postgres:// after parsing. "
            "Check .env has exactly one DATABASE_URL=key (no duplicated DATABASE_URL=)."
        )
    return url


def _canonical_dsn_scheme(dsn: str) -> str:
    """Use postgresql scheme for urlparse (asyncpg only accepts postgres schemes)."""
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://"):
        if dsn.startswith(prefix):
            rest = dsn[len(prefix) :]
            return "postgresql://" + rest
    return dsn


def _dsn_hostname(dsn: str) -> str | None:
    return urlparse(_canonical_dsn_scheme(dsn)).hostname


def _prepare_dsn_for_asyncpg(dsn: str) -> str:
    """Supabase expects TLS; pooler URIs from the dashboard usually include sslmode — add if missing."""
    if "supabase" not in dsn.lower():
        return dsn
    parsed = urlparse(_canonical_dsn_scheme(dsn))
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "sslmode" in q or "ssl" in q:
        return dsn
    q["sslmode"] = "require"
    return urlunparse(parsed._replace(query=urlencode(q)))


def _uses_supabase_pooler(dsn: str) -> bool:
    host = (_dsn_hostname(dsn) or "").lower()
    if "pooler.supabase" in host:
        return True
    p = urlparse(_canonical_dsn_scheme(dsn))
    return bool(p.port == 6543 and "supabase" in host)


def _host_literal_for_netloc(ip: str) -> str:
    """IPv6 addresses must be bracketed in URL netlocs; IPv4 stays plain."""
    return f"[{ip}]" if ":" in ip else ip


def _dsn_replace_netloc_host(dsn: str, ip: str) -> str:
    """
    Substitute literal IP (v4 or v6) for hostname in DATABASE_URL TCP netloc.

    Keeps credentials and port unchanged. Used when OS DNS breaks but public
    resolvers succeed. Supabase direct DB hosts are often IPv6-only (AAAA);
    Windows may fail getaddrinfo even when the name is valid.
    """
    lit = _host_literal_for_netloc(ip)
    canon = _canonical_dsn_scheme(dsn)
    parsed = urlparse(canon)
    if not parsed.netloc:
        return dsn

    nl = parsed.netloc
    if "@" in nl:
        auth, _, host_spec = nl.partition("@")
    else:
        auth, host_spec = "", nl

    if host_spec.startswith("["):
        return dsn

    if ":" in host_spec and not host_spec.startswith("["):
        _, _, port = host_spec.rpartition(":")
        host_spec_new = f"{lit}:{port}"
    else:
        host_spec_new = lit

    new_netloc = f"{auth}@{host_spec_new}" if auth else host_spec_new
    return urlunparse(parsed._replace(netloc=new_netloc))


def _resolve_ip_via_public_dns(hostname: str | None) -> str | None:
    """Resolve A record, else AAAA — Supabase DB hosts may be IPv6-only."""
    if not hostname:
        return None
    try:
        import dns.resolver
    except ImportError:
        logger.warning(
            "dnspython is not installed; cannot retry DNS via public servers. "
            "Install dnspython (see requirements.txt) or fix system DNS."
        )
        return None

    res = dns.resolver.Resolver(configure=False)
    res.nameservers = ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
    res.timeout = 2.5
    res.lifetime = 8.0

    last_exc: BaseException | None = None
    for rrtype in ("A", "AAAA"):
        try:
            answers = res.resolve(hostname, rrtype)
            addr = getattr(answers[0], "address", None) or str(answers[0])
            addr = addr.rstrip(".")
            return addr
        except dns.resolver.NoAnswer:
            continue
        except dns.resolver.NXDOMAIN:
            logger.warning(
                "Public DNS: NXDOMAIN for %r (check project ref / hostname).",
                hostname,
            )
            return None
        except Exception as ex:
            last_exc = ex
            continue

    if last_exc is not None:
        logger.warning(
            "Public DNS could not resolve %r (tried A and AAAA): %s",
            hostname,
            last_exc,
        )
    else:
        logger.warning(
            "Public DNS had no A/AAAA answers for %r (name ok but empty RRset).",
            hostname,
        )
    return None


def _looks_like_dns_failure(exc: BaseException) -> bool:
    errno = getattr(exc, "errno", None)
    if isinstance(exc, socket.gaierror):
        return True
    if errno == socket.EAI_NONAME:
        return True
    if errno == socket.EHOSTUNREACH:
        return True
    return bool(errno == 11003 and os.name == "nt")


def _postgres_password_help() -> str:
    """Non-secret checklist when PG returns password authentication failed."""
    return (
        "PostgreSQL rejected DATABASE_URL credentials (wrong password/username, "
        "or userinfo mangled when parsing the URI). "
        "For Supabase: Project Settings → Database → Database password — click "
        "Reset, then copy the **new** connection URI (old passwords stop working). "
        "Anon/service_role keys are not the DB password. "
        "Pooler errors sometimes say user \"postgres\" even when the URI uses "
        "`postgres.<project-ref>`. "
        "If your password contains @ or :, percent-encode it in the URI as %40 / %3A."
    )


def _dsn_auth_error_appendix(dsn: str) -> str:
    """
    Parsed-DNS-style hints appended to InvalidPassword failures.
    Username/host/port/count of password chars only — password never echoed.
    """
    p = urlparse(_canonical_dsn_scheme(dsn))
    host = (p.hostname or "").lower()
    db = ((p.path or "").lstrip("/").split("/", 1)[0]) or "(none)"
    user = unquote((p.username or "").strip())

    pwd_len = 0
    if p.password is not None:
        pwd_len = len(unquote(p.password))
    if p.password is None:
        pwd_status = "absent"
    elif pwd_len == 0:
        pwd_status = "empty"
    else:
        pwd_status = "present"

    hints: list[str] = [
        f"fingerprint(no secrets): user={user!r} host={p.hostname!r} "
        f"port={p.port!s} db={db!r} password_field={pwd_status}(len={pwd_len})."
    ]

    if ("db." in host and ".supabase.co" in host and p.port == 6543) or (
        "pooler" in host and p.port == 5432
    ):
        hints.append(
            "Host/port look mismatched: `db.<ref>.supabase.co` is normally port 5432 (direct); "
            "Transaction pooling is usually *.pooler.supabase.* on port 6543. "
            "Use the dashboard's URI for your chosen mode, not a mix."
        )

    if p.port == 6543:
        if user == "postgres":
            hints.append(
                "Bare user `postgres` on port 6543 is commonly rejected — "
                'Supabase pooled URIs use `postgres.<project-ref>`. Paste the Transaction pooler URI verbatim.'
            )
        if "pooler" not in host:
            hints.append(
                "Port 6543 without `pooler` in the hostname — confirm you copied the pooled connection string."
            )

    if "pooler" in host and user.startswith("postgres."):
        hints.append(
            "If the password was reset in Supabase, replace DATABASE_URL with the "
            "fresh URI from the dashboard (do not keep the old password)."
        )

    return " ".join(hints)


async def _connect_pool(dsn: str) -> asyncpg.Pool:
    pool_kw: dict = dict(
        dsn=dsn,
        min_size=1,
        max_size=10,
        init=_init_connection,
    )
    if _uses_supabase_pooler(dsn):
        # Transaction pooler (PgBouncer / Supavisor): prepared statements break across backends
        pool_kw["statement_cache_size"] = 0
    try:
        return await asyncpg.create_pool(**pool_kw)
    except asyncpg.InvalidPasswordError as exc:
        appendix = _dsn_auth_error_appendix(dsn)
        raise RuntimeError(_postgres_password_help() + " " + appendix) from exc


async def _create_pool_maybe_dns_fallback(initial_dsn: str) -> asyncpg.Pool:
    try:
        return await _connect_pool(initial_dsn)
    except OSError as exc:
        if not _looks_like_dns_failure(exc):
            raise

        hostname = _dsn_hostname(initial_dsn)
        ip = _resolve_ip_via_public_dns(hostname)

        if not ip:
            raise RuntimeError(_dns_help_message(initial_dsn)) from exc

        retried_dsn = _dsn_replace_netloc_host(initial_dsn, ip)
        logger.warning(
            "Primary DNS lookup failed (%s); connecting to %s@%s "
            "(resolved via Google/Cloudflare DNS — literal IP in DSN). "
            "Fix OS IPv6/DNS when you can; many Supabase DB hosts are IPv6-only.",
            exc.__class__.__name__,
            hostname,
            ip,
        )
        try:
            return await _connect_pool(retried_dsn)
        except OSError as exc2:
            logger.exception(
                "Second connection attempt failed after public-DNS workaround."
            )
            raise RuntimeError(_dns_help_message(initial_dsn)) from exc2


def _dns_help_message(dsn: str) -> str:
    host = _dsn_hostname(dsn)
    return (
        "Could not resolve DATABASE_URL host "
        f"{host!r}: DNS lookup failed (Windows often reports errno 11003 / "
        "getaddrinfo failed — Supabase DB hostnames may be IPv6-only (AAAA) "
        "with no IPv4 record; Windows resolver issues are common.) CogniCare "
        "can retry lookup via Google/Cloudflare if `dnspython` is installed "
        "(see requirements.txt); ensure IPv6 works or apply OS DNS fixes. "
        "Also try: PowerShell nslookup "
        f"{host} 8.8.8.8; then set NIC DNS / flushdns); disable VPN; try WSL "
        "or another network; for Supabase pooled mode use Transaction pool "
        "host/port from Database settings."
    )


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool
    async with _pool_lock:
        if _pool is None:
            dsn = _prepare_dsn_for_asyncpg(_dsn())
            _pool = await _create_pool_maybe_dns_fallback(dsn)
    return _pool


@asynccontextmanager
async def get_connection() -> AsyncIterator[asyncpg.Connection]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def verify_database_connection() -> None:
    """
    Open the pool if needed and run a trivial query.

    Prefer calling this before expensive steps (e.g. OpenAI embeddings) so DB
    auth / connectivity fails fast before paid API usage.
    """
    async with get_connection() as conn:
        await conn.fetchval("SELECT 1")


async def close_pool() -> None:
    global _pool
    async with _pool_lock:
        if _pool is not None:
            await _pool.close()
            _pool = None
