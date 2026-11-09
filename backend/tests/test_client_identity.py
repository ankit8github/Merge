"""Socket/proxy trust unit checks; no database or actual proxy evidence."""
from dataclasses import FrozenInstanceError

import pytest

from app.security.client_identity import (ClientIdentity, ClientIdentityError,
                                          get_client_identity)


def scope(peer='192.0.2.10', scheme='https', headers=()):
    return {'client': (peer, 50000), 'scheme': scheme, 'headers': list(headers)}


FORWARDED = ((b'x-forwarded-for', b'198.51.100.20'),
             (b'x-forwarded-proto', b'https'))


@pytest.mark.parametrize('peer, canonical', [
    ('192.0.2.10', '192.0.2.10'),
    ('2001:0db8:0:0:0:0:0:1', '2001:db8::1'),
    ('::ffff:192.0.2.10', '192.0.2.10'),
    ('::ffff:c000:20a', '192.0.2.10'),
])
def test_direct_actual_peer_is_canonicalized(peer, canonical):
    assert get_client_identity(scope(peer), ()) == ClientIdentity(canonical, 'https')


def test_identity_is_frozen_and_repr_omits_ip():
    identity = get_client_identity(scope(), ())
    assert '192.0.2.10' not in repr(identity)
    assert 'https' in repr(identity)
    with pytest.raises(FrozenInstanceError):
        identity.ip = '203.0.113.1'


@pytest.mark.parametrize('peer', [None, '', 'testclient', 'localhost', '192.0.2.10:8000',
                                 '[2001:db8::1]', 'fe80::1%eth0', ' 192.0.2.10',
                                 '192.0.2.10 ', '192.0.002.10', 123])
def test_invalid_actual_peer_fails_closed(peer):
    with pytest.raises(ClientIdentityError, match='^invalid_client_identity$'):
        get_client_identity(scope(peer), ())


@pytest.mark.parametrize('connection', [None, (), ('192.0.2.10',),
                                        ('192.0.2.10', '50000'), ('192.0.2.10', -1),
                                        ('192.0.2.10', 65536), ('192.0.2.10', True)])
def test_absent_or_malformed_connection_fails_closed(connection):
    selected = scope()
    selected['client'] = connection
    with pytest.raises(ClientIdentityError):
        get_client_identity(selected, ())


@pytest.mark.parametrize('scheme', [None, '', 'HTTPS', 'ftp', 1])
def test_invalid_actual_scheme_fails_closed(scheme):
    with pytest.raises(ClientIdentityError):
        get_client_identity(scope(scheme=scheme), ())


@pytest.mark.parametrize('headers', [FORWARDED, FORWARDED[:1], FORWARDED[1:],
                                   ((b'X-Forwarded-For', b'198.51.100.20'),),
                                   ((b'x-forwarded-for', b''),)])
def test_untrusted_actual_peer_cannot_supply_forwarded_identity(headers):
    with pytest.raises(ClientIdentityError):
        get_client_identity(scope(headers=headers), ('203.0.113.1',))


@pytest.mark.parametrize('trust', [('192.0.2.10',), ('192.0.2.0/24',),
                                  ('192.0.2.10/32',), ('::ffff:192.0.2.10/128',)])
def test_only_explicit_trusted_immediate_proxy_can_supply_identity(trust):
    assert get_client_identity(scope(scheme='http', headers=FORWARDED), trust) == ClientIdentity(
        '198.51.100.20', 'https')


def test_ipv6_trusted_peer_and_forwarded_client_normalization():
    selected = scope('2001:db8::a', scheme='http', headers=(
        (b'x-forwarded-for', b'::ffff:198.51.100.20'),
        (b'x-forwarded-proto', b'http')))
    assert get_client_identity(selected, ('2001:db8::/64',)) == ClientIdentity('198.51.100.20', 'http')


@pytest.mark.parametrize('headers', [(), FORWARDED[:1], FORWARDED[1:],
                                   FORWARDED + FORWARDED[:1],
                                   FORWARDED + FORWARDED[1:]])
def test_trusted_peer_requires_exactly_one_of_both_headers(headers):
    with pytest.raises(ClientIdentityError):
        get_client_identity(scope(headers=headers), ('192.0.2.10',))


@pytest.mark.parametrize('client', [b'', b'unknown', b'198.51.100.20, 203.0.113.1',
                                   b'198.51.100.20:50000', b'[2001:db8::1]',
                                   b'fe80::1%eth0', b' 198.51.100.20', b'198.51.100.20 ',
                                   b'\xff', b'a' * 1000])
def test_forwarded_client_must_be_one_bounded_literal(client):
    with pytest.raises(ClientIdentityError):
        get_client_identity(scope(headers=((b'x-forwarded-for', client), FORWARDED[1])),
                            ('192.0.2.10',))


@pytest.mark.parametrize('scheme', [b'', b'HTTPS', b'https,http', b' https', b'ftp', b'\xff'])
def test_forwarded_scheme_is_exact_and_single(scheme):
    with pytest.raises(ClientIdentityError):
        get_client_identity(scope(headers=(FORWARDED[0], (b'x-forwarded-proto', scheme))),
                            ('192.0.2.10',))


@pytest.mark.parametrize('name', [b'forwarded', b'Forwarded', b'x-real-ip', b'X-Real-IP'])
@pytest.mark.parametrize('trust', [(), ('192.0.2.10',)])
def test_alternative_forwarding_headers_always_rejected(name, trust):
    with pytest.raises(ClientIdentityError):
        get_client_identity(scope(headers=FORWARDED + ((name, b'198.51.100.20'),)), trust)


@pytest.mark.parametrize('trusted', [('*',), ('0.0.0.0/0',), ('::/0',),
                                    ('localhost',), ('192.0.2.10%eth0',),
                                    (' 192.0.2.10',), ('',), ['192.0.2.10'],
                                    tuple('192.0.2.10' for _ in range(17)),
                                    ('::ffff:0.0.0.0/96',)])
def test_invalid_or_unbounded_trust_configuration_fails_closed(trusted):
    with pytest.raises(ClientIdentityError):
        get_client_identity(scope(headers=FORWARDED), trusted)


@pytest.mark.parametrize('headers', [None, 'x-forwarded-for', [(b'x-forwarded-for',)],
                                   [('x-forwarded-for', b'198.51.100.20')],
                                   [(b'x-forwarded-for', '198.51.100.20')]])
def test_malformed_asgi_headers_fail_closed(headers):
    selected = scope()
    selected['headers'] = headers
    with pytest.raises(ClientIdentityError):
        get_client_identity(selected, ())


def test_failures_expose_only_fixed_text_without_raw_input_or_chained_error():
    supplied = 'sensitive-invalid-client-example'
    for selected in (scope(supplied), scope(headers=((b'x-forwarded-for', supplied.encode()),
                                                   FORWARDED[1]))):
        with pytest.raises(ClientIdentityError) as captured:
            get_client_identity(selected, ('192.0.2.10',))
        assert str(captured.value) == 'invalid_client_identity'
        assert supplied not in repr(captured.value)
        assert captured.value.__context__ is None
        assert captured.value.__cause__ is None


def test_unrelated_headers_do_not_change_the_actual_identity():
    selected = scope(headers=((b'host', b'public.example'), (b'user-agent', b'unit-example')))
    assert get_client_identity(selected, ()) == ClientIdentity('192.0.2.10', 'https')
