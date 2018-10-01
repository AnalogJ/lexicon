from __future__ import absolute_import
from __future__ import print_function
import logging

from requests import Session
from bs4 import BeautifulSoup
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
        'login': 'https://my.easyname.com/en/login'
    }


    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.session = Session()


    def authenticate(self):
        """
        Authenticates against Easyname website and try to find out the domain
        id.

        Returns:
          bool: True if domain id was found.

        Raises:
          RuntimeError: When a request returns unexpected or unknown data.
          ValueError: When login data is wrong or the domain does not exist.
        """
        # Create the session GET the login page to retrieve the loginxtoken
        home_response = self.session.get(self.URLS['login'])

        if not home_response.ok:
            errmsg = ('Could not load Easyname. '
                      'Please try again or open an issue on GitHub.')
            logger.warning(errmsg)
            raise RuntimeError(errmsg)

        html = BeautifulSoup(home_response.content, 'html.parser')
        loginxtoken_field = html.find('input', {'id': 'loginxtoken'})
        if loginxtoken_field is None:
            errmsg = ('Could not find loginxtoken.'
                      'Provider needs revisioning most probably')
            logger.warning(errmsg)
            raise RuntimeError(errmsg)


        loginxtoken = loginxtoken_field['value']
