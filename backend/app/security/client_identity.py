"""Client identity from an actual ASGI peer and an explicit single-hop proxy.

The server must disable its own forwarded-header middleware. This module cannot
recover the socket peer after another middleware has overwritten scope['client'].
No header value, IP address or trust-network configuration belongs in logs.
"""
from dataclasses import dataclass, field
from ipaddress import IPv4Address, IPv4Network, IPv6Address, ip_address, ip_network


class ClientIdentityError(Exception):
    """A fixed public-independent failure without a submitted value attached."""

    def __init__(self):
        super().__init__('invalid_client_identity')


@dataclass(frozen=True, slots=True)
class ClientIdentity:
    ip: str = field(repr=False)
    scheme: str


def _literal_ip(value) -> IPv4Address | IPv6Address:
    if (not isinstance(value, str) or not 1 <= len(value) <= 45
            or value != value.strip() or '%' in value):
        raise ClientIdentityError()
    try:
        result = ip_address(value)
    except ValueError:
        pass
    else:
        # The same socket address must not acquire a second throttle partition.
        if isinstance(result, IPv6Address) and result.ipv4_mapped is not None:
            return result.ipv4_mapped
        return result
    raise ClientIdentityError()


def _trusted(peer: IPv4Address | IPv6Address, configured: tuple[str, ...]) -> bool:
    if not isinstance(configured, tuple) or len(configured) > 16:
        raise ClientIdentityError()
    matched = False
    for value in configured:
        if (not isinstance(value, str) or not value or value != value.strip()
                or '%' in value or '*' in value):
            raise ClientIdentityError()
        try:
            network = ip_network(value, strict=False)
        except ValueError:
            failure = True
        else:
            failure = network.prefixlen == 0
            if isinstance(network.network_address, IPv6Address) and network.prefixlen >= 96:
                mapped = network.network_address.ipv4_mapped
                if mapped is not None:
                    network = IPv4Network((mapped, network.prefixlen - 96))
                    failure = network.prefixlen == 0
            if not failure and peer in network:
                matched = True
        if failure:
            raise ClientIdentityError()
    return matched


def get_client_identity(scope: dict, trusted_proxies: tuple[str, ...]) -> ClientIdentity:
    """Reject ambiguous identity; configured proxies must send one XFF and XFP.

    Only a single immediate proxy is supported. Forwarded chains and alternative
    header conventions require a separate reviewed deployment policy.
    """
    if not isinstance(scope, dict):
        raise ClientIdentityError()
    connection = scope.get('client')
    if (not isinstance(connection, (tuple, list)) or len(connection) != 2
            or type(connection[1]) is not int or not 0 <= connection[1] <= 65535):
        raise ClientIdentityError()
    peer = _literal_ip(connection[0])
    scheme = scope.get('scheme')
    if scheme not in ('http', 'https'):
        raise ClientIdentityError()
    forwarded = {b'x-forwarded-for': [], b'x-forwarded-proto': []}
    headers = scope.get('headers', [])
    if not isinstance(headers, (tuple, list)):
        raise ClientIdentityError()
    for item in headers:
        if (not isinstance(item, (tuple, list)) or len(item) != 2
                or not isinstance(item[0], bytes) or not isinstance(item[1], bytes)):
            raise ClientIdentityError()
        name, value = item[0].lower(), item[1]
        if name in (b'forwarded', b'x-real-ip'):
            raise ClientIdentityError()
        if name in forwarded:
            forwarded[name].append(value)
    trusted = _trusted(peer, trusted_proxies)
    if not trusted:
        if any(forwarded.values()):
            raise ClientIdentityError()
        return ClientIdentity(str(peer), scheme)
    if any(len(values) != 1 for values in forwarded.values()):
        raise ClientIdentityError()
    try:
        client = forwarded[b'x-forwarded-for'][0].decode('ascii')
        public_scheme = forwarded[b'x-forwarded-proto'][0].decode('ascii')
    except UnicodeDecodeError:
        pass
    else:
        if public_scheme in ('http', 'https'):
            return ClientIdentity(str(_literal_ip(client)), public_scheme)
    raise ClientIdentityError()
