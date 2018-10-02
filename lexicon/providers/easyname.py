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
        Easyname uses a CSRF token in its login form, so two requests are
        neccessary to actually login.

        Returns:
          bool: True if domain id was found.

        Raises:
          AssertionError: When a request returns unexpected or unknown data.
          ValueError: When login data is wrong or the domain does not exist.
        """
        home_response = self.session.get(self.URLS['login'])
        logger.debug(home_response)
        assert home_response.status_code == 200, \
               'Could not load Easyname login page.'

        html = BeautifulSoup(home_response.content, 'html.parser')
        logger.debug(html)
        csrf_token_field = html.find('input', {'id': 'loginxtoken'})
        assert csrf_token_field is not None, 'Could not find login token.'

        csrf_token = csrf_token_field['value']
        login_response = self.session.post(
           self.URLS['login'],
            data={
                'username':     self.options.get('auth_username',''),
                'password':     self.options.get('auth_password',''),
                'submit':       '',
                'loginxtoken':  csrf_token,
            }
        )
        logger.debug(login_response)
        assert login_response.status_code == 200, \
               'Could not login due to a network error.'

        # Error if the p containing the error message is found
        html = BeautifulSoup(login_response.content, 'html.parser')
        if html.find('p', {'class': 'feedback-message__text'}) is not None:
            errmsg = ('Easyname login failed, check EASYNAME_USER '
                      'and EASYNAME_PASS.')
            logger.warning(errmsg)
            raise ValueError(errmsg)
