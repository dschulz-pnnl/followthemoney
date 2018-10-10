from unittest import TestCase
from nose.tools import assert_raises
from followthemoney.exc import InvalidData


from followthemoney import model
from followthemoney.proxy import EntityProxy


ENTITY = {
    'id': 'test',
    'schema': 'Person',
    'properties': {
        'name': 'Ralph Tester',
        'birthDate': '1972-05-01',
        'idNumber': ['9177171', '8e839023'],
        'website': 'https://ralphtester.me',
        'phone': '+12025557612',
        'email': 'info@ralphtester.me',
        'passport': 'passportEntityId'
    }
}


class ProxyTestCase(TestCase):

    def test_base_functions(self):
        proxy = EntityProxy.from_dict(model, ENTITY)
        assert 'test' in repr(proxy), repr(proxy)
        assert hash(proxy) == hash(proxy.id)
        assert proxy.get('name') == ['Ralph Tester']
        prop = model.get_qname('Thing:name')
        assert proxy.get(prop) == ['Ralph Tester']
        assert proxy.caption == 'Ralph Tester'

        name = 'Ralph the Great'
        proxy.add('name', name)
        assert len(proxy.get('name')) == 2
        proxy.add('name', None)
        assert len(proxy.get('name')) == 2
        assert name in proxy.get('name')
        assert name in proxy.names, proxy.names

        assert len(proxy.get('nationality')) == 0

        double = EntityProxy.from_dict(model, proxy)
        assert double == proxy

        with assert_raises(InvalidData):
            proxy.add('banana', name)

        with assert_raises(InvalidData):
            EntityProxy.from_dict(model, {})

    def test_dict_passthrough(self):
        proxy = EntityProxy.from_dict(model, ENTITY)
        data = proxy.to_dict()
        assert data['id'] == ENTITY['id']
        assert data['schema'] == ENTITY['schema']
        assert 'idNumber' in data['properties']

        data = proxy.to_full_dict()
        assert ENTITY['schema'] in data['schemata']
        assert 'Ralph Tester' in data['names']

    def test_inverted_props(self):
        proxy = EntityProxy.from_dict(model, ENTITY)
        data = proxy.get_type_inverted()
        assert 'names' in data
        assert '1972-05-01' in data['dates']
        assert 'countries' not in data
        proxy.add('nationality', ['vg'])
        assert 'vg' in proxy.countries
        data = proxy.get_type_inverted()
        assert 'countries'in data

    def test_make_id(self):
        proxy = model.make_entity('Thing')
        assert not proxy.make_id(None)
        assert proxy.make_id('banana')
        assert proxy.make_id('banana') == proxy.make_id('banana')
        ff = proxy.make_id(44)
        assert ff is not None
        proxy = model.make_entity('Thing', key_prefix='foo')
        assert proxy.make_id(44)
        assert proxy.make_id(44) != ff, proxy.make_id(44)

    def test_clone(self):
        proxy = EntityProxy.from_dict(model, ENTITY)
        other = proxy.clone()
        assert other == proxy
        other.id = 'banana'
        assert proxy.id == 'test'
        assert other != proxy

    def test_merge(self):
        proxy = EntityProxy.from_dict(model, ENTITY)
        other = {
            'schema': 'LegalEntity',
            'properties': {
                'country': 'gb'
            }
        }
        other = EntityProxy.from_dict(model, other)
        proxy.merge(other)
        assert 'Ralph Tester' in proxy.names, proxy.names
        assert 'gb' in proxy.countries, proxy.countries