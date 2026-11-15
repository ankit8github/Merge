"""Reuse reviewed Railway runtime identity guard with a Render private target."""
from ipaddress import ip_address
import socket
from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool
from app.railway.database import Guard, NETWORKS, ready, server
from app.render.config import REVISION, RenderConfig, RenderSetupTarget


def private_addresses(target):
    target.url()
    addresses = {str(ip_address(item[4][0])) for item in
                 socket.getaddrinfo(target.db_host, 5432, type=socket.SOCK_STREAM)}
    if not addresses or any(not any(ip_address(a) in n for n in NETWORKS) for a in addresses):
        raise ValueError('Private Render DNS addresses required')
    return tuple(sorted(addresses))


def engine(target):
    if not isinstance(target, RenderConfig) or target.role != 'runtime':
        raise ValueError('Only the restricted Render runtime target may serve')
    addresses = private_addresses(target)
    guard = Guard(target, addresses, REVISION)
    resource = create_engine(target.url(), hide_parameters=True, echo=False,
        isolation_level='READ COMMITTED', pool_size=2, max_overflow=0, pool_timeout=5,
        pool_recycle=900, execution_options={'schema_translate_map': {None: 'public'}},
        connect_args=connect_args(addresses))
    event.listen(resource, 'engine_connect', guard)
    return resource


def connect_args(addresses):
    return {'hostaddr': addresses[0], 'sslmode': 'require', 'connect_timeout': 5,
            'options': '-c statement_timeout=15000 -c lock_timeout=5000 -c search_path=public'}


def setup_engine(target, addresses):
    if not isinstance(target, RenderSetupTarget) or target.role != 'migrator':
        raise ValueError('Explicit Render setup target required')
    return create_engine(target.url(), hide_parameters=True, echo=False,
        isolation_level='READ COMMITTED', poolclass=NullPool,
        execution_options={'schema_translate_map': {None: 'public'}}, connect_args=connect_args(addresses))
