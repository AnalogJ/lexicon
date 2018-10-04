from __future__ import absolute_import
from __future__ import print_function
import logging

from requests import Session, Response
from bs4 import BeautifulSoup, Tag
from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)

def ProviderParser(subparser):
    subparser.description = """A provider for Easyname DNS."""
    subparser.add_argument(
        '--auth-username',
        help='Specify username used to authenticate'
    )
    subparser.add_argument(
        '--auth-password',
        help='Specify password used to authenticate',
    )



class Provider(BaseProvider):
    """
        easyname provider
    """

    URLS = {
        'login': 'https://my.easyname.com/en/login',
        'domain_list': 'https://my.easyname.com/domains',
        'overview': 'https://my.easyname.com/hosting/view-user.php'
    }


    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.session = Session()
        self.domain_id = None


    def authenticate(self):
        """
        Authenticates against Easyname website and try to find out the domain
        id.
        Easyname uses a CSRF token in its login form, so two requests are
        neccessary to actually login.

        Returns:
          bool: True if domain id was found.

        Raises:
          AssertionError: When a request returns unexpected or unknown data.
          ValueError: When login data is wrong or the domain does not exist.
        """
        csrf_token = self._get_csrf_token()
        self._login(csrf_token)

        domain_text_element = self._get_domain_text_of_authoritative_zone()
        self.domain_id = self._get_domain_id(domain_text_element)
        logger.debug('Easyname domain ID: {}'.format(self.domain_id))

        return True


    def _get_csrf_token(self):
        """Return the CSRF Token of easyname login form."""
        home_response = self.session.get(self.URLS['login'])
        self._log('Home', home_response)
        assert home_response.status_code == 200, \
               'Could not load Easyname login page.'

        html = BeautifulSoup(home_response.content, 'html.parser')
        self._log('Home', html)
        csrf_token_field = html.find('input', {'id': 'loginxtoken'})
        assert csrf_token_field is not None, 'Could not find login token.'
        return csrf_token_field['value']


    def _login(self, csrf_token):
        """Attempt to login session on easyname."""
        login_response = self.session.post(
           self.URLS['login'],
            data={
                'username':     self.options.get('auth_username',''),
                'password':     self.options.get('auth_password',''),
                'submit':       '',
                'loginxtoken':  csrf_token,
            }
        )
        self._log('Login', login_response)
        assert login_response.status_code == 200, \
               'Could not login due to a network error.'
        assert login_response.url == self.URLS['overview'], \
               'Easyname login failed, bad EASYNAME_USER or EASYNAME_PASS.'


    def _get_domain_text_of_authoritative_zone(self):
        """Get the authoritative name zone."""
        # We are logged in, so get the domain list
        zones_response = self.session.get(self.URLS['domain_list'])
        self._log('Zone', zones_response)
        assert zones_response.status_code == 200, \
               'Could not retrieve domain list due to a network error.'

        html = BeautifulSoup(zones_response.content, 'html.parser')
        self._log('Zone', html)
        domain_table = html.find('table', {'id': 'cp_domain_table'})
        assert domain_table is not None, 'Could not find domain table'

        # (Sub)domains can either be managed in their own zones or by the
        # zones of their parent (sub)domains. Iterate over all subdomains
        # (starting with the deepest one) and see if there is an own zone
        # for it.
        domain = self.options.get('domain','')
        domain_text = None
        subdomains = domain.split('.')
        while True:
            domain = '.'.join(subdomains)
            logger.debug('Check if {} has own zone'.format(domain))
            domain_text = domain_table.find(string=domain)
            if domain_text is not None or len(subdomains) < 3:
                break;
            subdomains.pop(0)

        assert domain_text is not None, \
               'The domain does not exist on Easyname.'
        return domain_text


    def _get_domain_id(self, domain_text_element):
        """Return the easyname id of the domain."""
        try:
            # Hierarchy: TR > TD > SPAN > Domain Text
            tr = domain_text_element.parent.parent.parent
            td = tr.find('td', {'class': 'td_2'})
            link = td.find('a')['href']
            domain_id = link.rsplit('/',1)[-1]
        except Exception, e:
            errmsg = ('Cannot get the domain id even though the domain seems '
                      'to exist ({}).'.format(e))
            logger.warning(errmsg)
            raise AssertionError(errmsg)


    def _log(self, name, element):
        """
        Log Response and Tag elements. Do nothing if elements is none of them.
        """
        if isinstance(element, Response):
            logger.debug('{} response: URL={} Code={}'.format(name,
                         element.url, element.status_code))

        elif isinstance(element, Tag) or isinstance(element, BeautifulSoup):
            logger.debug('{} HTML:\n{}'.format(name, element))