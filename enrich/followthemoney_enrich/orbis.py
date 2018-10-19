import os
import re
import zeep
import json
import logging
from pprint import pprint  # noqa
from normality import stringify
from corpint.common import Enricher, Result
from banal import ensure_list, ensure_dict

log = logging.getLogger(__name__)
logging.getLogger('zeep').setLevel(logging.WARNING)


class OrbisEnricher(Enricher):
    WSDL = 'https://webservices.bvdep.com/orbis/remoteaccess.asmx?WSDL'
    key_prefix = 'bvd'

    def __init__(self):
        self.username = os.environ.get("CORPINT_ORBIS_USERNAME")
        self.password = os.environ.get("CORPINT_ORBIS_PASSWORD")
        self.credentials = self.username is not None
        self.credentials = self.credentials and self.password is not None
        if not self.credentials:
            log.warning("Orbis enricher has no credentials, will be disabled")

    @property
    def client(self):
        if not hasattr(self, '_client'):
            self._client = zeep.Client(wsdl=self.WSDL)
        return self._client

    def enrich_entity(self, entity):
        if not self.credentials:
            return
        schema = entity.schema.name
        if schema not in ['Company', 'Organization', 'LegalEntity']:
            return

        for company in self.match_company(entity):
            result = Result(self)
            result.principal = self.company_entity(result, company)
            yield result
            # if 'Shareholders' in res:
            #     aligned_dicts.append(self.align_bvd_shareholders(res))
            # if 'guo_names' in res:
            #     aligned_dicts.append(self.align_bvd_guo_group(res))

    def match_company(self, proxy):
        MatchCriteria = self.client.get_type('ns0:MatchCriteria')
        # SelectionResult = self.client.get_type('ns0:SelectionResult')
        countries = list(proxy.countries)
        if len(countries) == 1:
            ct = MatchCriteria(Name=proxy.caption, Country=countries[0])
        else:
            ct = MatchCriteria(Name=proxy.caption)

        data = self.cache.get(ct)
        if data is None:
            session = None
            try:
                session = self.client.service.Open(self.username,
                                                   self.password)
                res = self.client.service.Match(session, ct, ['None'])
                data = zeep.helpers.serialize_object(res)
                # pprint(data)
                data = json.loads(json.dumps(data))
                self.cache.store(ct, data)
            finally:
                if session is not None:
                    self.client.service.Close(session)
        return ensure_list(data)

    def join_address(self, data):
        parts = (data.get('Address'),
                 data.get('PostCode'),
                 data.get('City'),
                 data.get('Region'))
        parts = (stringify(p) for p in parts)
        parts = (p for p in parts if p is not None)
        return ', '.join(parts)

    def company_entity(self, result, data):
        data = ensure_dict(data.get('company', data))
        entity = result.make_entity('Company')
        entity.make_id(data.get('BvDID'))
        entity.add('name', data.get('Name'))
        entity.add('country', data.get('Country'))
        entity.add('alias', data.get('NameInLocalAlphabet'))
        entity.add('address', self.join_address(data))

        contact = str(data.get('EmailOrWebsite'))
        if re.match('[^@]+@[^@]+\.[^@]+', contact):
            entity.add('email', data.get('EmailOrWebsite'))
        elif re.match('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', contact):
            entity.add('website', data.get('EmailOrWebsite'))

        entity.add('phone', data.get('PhoneOrFax'))
        entity.add('status', data.get('Status'))
        entity.add('idNumber', data.get('NationalId'))
        entity.add('bvdId', data.get('BvDID'))
        return entity