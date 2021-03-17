Providers available
-------------------

The following Lexicon providers are available:

+-----------------+-----------------+-----------------+-----------------+
| aliyun_         | aurora_         | azure_          | cloudflare_     |
+-----------------+-----------------+-----------------+-----------------+
| cloudns_        | cloudxns_       | conoha_         | constellix_     |
+-----------------+-----------------+-----------------+-----------------+
| digitalocean_   | dinahosting_    | directadmin_    | dnsimple_       |
+-----------------+-----------------+-----------------+-----------------+
| dnsmadeeasy_    | dnspark_        | dnspod_         | dreamhost_      |
+-----------------+-----------------+-----------------+-----------------+
| dynu_           | easydns_        | easyname_       | euserv_         |
+-----------------+-----------------+-----------------+-----------------+
| exoscale_       | gandi_          | gehirn_         | glesys_         |
+-----------------+-----------------+-----------------+-----------------+
| godaddy_        | googleclouddns_ | gransy_         | gratisdns_      |
+-----------------+-----------------+-----------------+-----------------+
| henet_          | hetzner_        | hostingde_      | hover_          |
+-----------------+-----------------+-----------------+-----------------+
| infoblox_       | internetbs_     | inwx_           | joker_          |
+-----------------+-----------------+-----------------+-----------------+
| linode_         | linode4_        | localzone_      | luadns_         |
+-----------------+-----------------+-----------------+-----------------+
| memset_         | namecheap_      | namesilo_       | netcup_         |
+-----------------+-----------------+-----------------+-----------------+
| nfsn_           | njalla_         | nsone_          | onapp_          |
+-----------------+-----------------+-----------------+-----------------+
| online_         | ovh_            | plesk_          | pointhq_        |
+-----------------+-----------------+-----------------+-----------------+
| powerdns_       | rackspace_      | rage4_          | rcodezero_      |
+-----------------+-----------------+-----------------+-----------------+
| route53_        | safedns_        | sakuracloud_    | softlayer_      |
+-----------------+-----------------+-----------------+-----------------+
| transip_        | ultradns_       | vultr_          | yandex_         |
+-----------------+-----------------+-----------------+-----------------+
| zeit_           | zilore_         | zonomi_         |                 |
+-----------------+-----------------+-----------------+-----------------+

List of options
---------------

.. _aliyun:

aliyun
    * ``auth_key_id`` Specify access key id for authentication
    * ``auth_secret`` Specify access secret for authentication

.. _aurora:

aurora
    * ``auth_api_key`` Specify api key for authentication
    * ``auth_secret_key`` Specify the secret key for authentication

.. _azure:

azure
    * ``auth_client_id`` Specify the client id (aka application id) of the app registration
    * ``auth_client_secret`` Specify the client secret of the app registration
    * ``auth_tenant_id`` Specify the tenant id (aka directory id) of the app registration
    * ``auth_subscription_id`` Specify the subscription id attached to the resource group
    * ``resource_group`` Specify the resource group hosting the dns zone to edit

.. _cloudflare:

cloudflare
    * ``auth_username`` Specify email address for authentication (for global api key only)
    * ``auth_token`` Specify token for authentication (global api key or api token)
    * ``zone_id`` Specify the zone id (if set, api token can be scoped to the target zone)

.. _cloudns:

cloudns
    * ``auth_id`` Specify user id for authentication
    * ``auth_subid`` Specify subuser id for authentication
    * ``auth_subuser`` Specify subuser name for authentication
    * ``auth_password`` Specify password for authentication
    * ``weight`` Specify the srv record weight
    * ``port`` Specify the srv record port

.. _cloudxns:

cloudxns
    * ``auth_username`` Specify api-key for authentication
    * ``auth_token`` Specify secret-key for authentication

.. _conoha:

conoha
    * ``auth_region`` Specify region. if empty, region 'tyo1' will be used.
    * ``auth_token`` Specify token for authentication. if empty, the username and password will be used to create a token.
    * ``auth_username`` Specify api username for authentication. only used if --auth-token is empty.
    * ``auth_password`` Specify api user password for authentication. only used if --auth-token is empty.
    * ``auth_tenant_id`` Specify tenand id for authentication. only used if --auth-token is empty.

.. _constellix:

constellix
    * ``auth_username`` Specify the api key username for authentication
    * ``auth_token`` Specify secret key for authenticate=

.. _digitalocean:

digitalocean
    * ``auth_token`` Specify token for authentication

.. _dinahosting:

dinahosting
    * ``auth_username`` Specify username for authentication
    * ``auth_password`` Specify password for authentication

.. _directadmin:

directadmin
    * ``auth_password`` Specify password for authentication (or login key for two-factor authentication)
    * ``auth_username`` Specify username for authentication
    * ``endpoint`` Specify the directadmin endpoint

.. _dnsimple:

dnsimple
    * ``auth_token`` Specify api token for authentication
    * ``auth_username`` Specify email address for authentication
    * ``auth_password`` Specify password for authentication
    * ``auth_2fa`` Specify two-factor auth token (otp) to use with email/password authentication

.. _dnsmadeeasy:

dnsmadeeasy
    * ``auth_username`` Specify username for authentication
    * ``auth_token`` Specify token for authentication

.. _dnspark:

dnspark
    * ``auth_username`` Specify api key for authentication
    * ``auth_token`` Specify token for authentication

.. _dnspod:

dnspod
    * ``auth_username`` Specify api id for authentication
    * ``auth_token`` Specify token for authentication

.. _dreamhost:

dreamhost
    * ``auth_token`` Specify api key for authentication

.. _dynu:

dynu
    * ``auth_token`` Specify api key for authentication

.. _easydns:

easydns
    * ``auth_username`` Specify username for authentication
    * ``auth_token`` Specify token for authentication

.. _easyname:

easyname
    * ``auth_username`` Specify username used to authenticate
    * ``auth_password`` Specify password used to authenticate

.. _euserv:

euserv
    * ``auth_username`` Specify email address for authentication
    * ``auth_password`` Specify password for authentication

.. _exoscale:

exoscale
    * ``auth_key`` Specify api key for authentication
    * ``auth_secret`` Specify api secret for authentication

.. _gandi:

gandi
    * ``auth_token`` Specify gandi api key
    * ``api_protocol`` (optional) specify gandi api protocol to use: rpc (default) or rest

.. _gehirn:

gehirn
    * ``auth_token`` Specify access token for authentication
    * ``auth_secret`` Specify access secret for authentication

.. _glesys:

glesys
    * ``auth_username`` Specify username (cl12345)
    * ``auth_token`` Specify api key

.. _godaddy:

godaddy
    * ``auth_key`` Specify the key to access the api
    * ``auth_secret`` Specify the secret to access the api

.. _googleclouddns:

googleclouddns
    * ``auth_service_account_info`` 
        specify the service account info in the google json format:
        can be either the path of a file prefixed by 'file::' (eg. file::/tmp/service_account_info.json)
        or the base64 encoded content of this file prefixed by 'base64::'
        (eg. base64::eyjhbgcioyj...)

.. _gransy:

gransy
    * ``auth_username`` Specify username for authentication
    * ``auth_password`` Specify password for authentication

.. _gratisdns:

gratisdns
    * ``auth_username`` Specify email address for authentication
    * ``auth_password`` Specify password for authentication

.. _henet:

henet
    * ``auth_username`` Specify username for authentication
    * ``auth_password`` Specify password for authentication

.. _hetzner:

hetzner
    * ``auth_token`` Specify hetzner dns api token

.. _hostingde:

hostingde
    * ``auth_token`` Specify api key for authentication

.. _hover:

hover
    * ``auth_username`` Specify username for authentication
    * ``auth_password`` Specify password for authentication

.. _infoblox:

infoblox
    * ``auth_user`` Specify the user to access the infoblox wapi
    * ``auth_psw`` Specify the password to access the infoblox wapi
    * ``ib_view`` Specify dns view to manage at the infoblox
    * ``ib_host`` Specify infoblox host exposing the wapi

.. _internetbs:

internetbs
    * ``auth_key`` Specify api key for authentication
    * ``auth_password`` Specify password for authentication

.. _inwx:

inwx
    * ``auth_username`` Specify username for authentication
    * ``auth_password`` Specify password for authentication

.. _joker:

joker
    * ``auth_token`` Specify the api key to connect to the joker.com api

.. _linode:

linode
    * ``auth_token`` Specify api key for authentication

.. _linode4:

linode4
    * ``auth_token`` Specify api key for authentication

.. _localzone:

localzone
    * ``filename`` Specify location of zone master file

.. _luadns:

luadns
    * ``auth_username`` Specify email address for authentication
    * ``auth_token`` Specify token for authentication

.. _memset:

memset
    * ``auth_token`` Specify api key for authentication

.. _namecheap:

namecheap
    * ``auth_token`` Specify api token for authentication
    * ``auth_username`` Specify username for authentication
    * ``auth_client_ip`` Client ip address to send to namecheap api calls
    * ``auth_sandbox`` Whether to use the sandbox server

.. _namesilo:

namesilo
    * ``auth_token`` Specify key for authentication

.. _netcup:

netcup
    * ``auth_customer_id`` Specify customer number for authentication
    * ``auth_api_key`` Specify api key for authentication
    * ``auth_api_password`` Specify api password for authentication

.. _nfsn:

nfsn
    * ``auth_username`` Specify username used to authenticate
    * ``auth_token`` Specify token used to authenticate

.. _njalla:

njalla
    * ``auth_token`` Specify api token for authentication

.. _nsone:

nsone
    * ``auth_token`` Specify token for authentication

.. _onapp:

onapp
    * ``auth_username`` Specify email address of the onapp account
    * ``auth_token`` Specify api key for the onapp account
    * ``auth_server`` Specify url to the onapp control panel server

.. _online:

online
    * ``auth_token`` Specify private api token

.. _ovh:

ovh
    * ``auth_entrypoint`` Specify the ovh entrypoint
    * ``auth_application_key`` Specify the application key
    * ``auth_application_secret`` Specify the application secret
    * ``auth_consumer_key`` Specify the consumer key

.. _plesk:

plesk
    * ``auth_username`` Specify username for authentication
    * ``auth_password`` Specify password for authentication
    * ``plesk_server`` Specify url to the plesk web ui, including the port

.. _pointhq:

pointhq
    * ``auth_username`` Specify email address for authentication
    * ``auth_token`` Specify token for authentication

.. _powerdns:

powerdns
    * ``auth_token`` Specify token for authentication
    * ``pdns_server`` Uri for powerdns server
    * ``pdns_server_id`` Server id to interact with
    * ``pdns_disable_notify`` Disable slave notifications from master

.. _rackspace:

rackspace
    * ``auth_account`` Specify account number for authentication
    * ``auth_username`` Specify username for authentication. only used if --auth-token is empty.
    * ``auth_api_key`` Specify api key for authentication. only used if --auth-token is empty.
    * ``auth_token`` Specify token for authentication. if empty, the username and api key will be used to create a token.
    * ``sleep_time`` Number of seconds to wait between update requests.

.. _rage4:

rage4
    * ``auth_username`` Specify email address for authentication
    * ``auth_token`` Specify token for authentication

.. _rcodezero:

rcodezero
    * ``auth_token`` Specify token for authentication

.. _route53:

route53
    * ``auth_access_key`` Specify access_key for authentication
    * ``auth_access_secret`` Specify access_secret for authentication
    * ``private_zone`` Indicates what kind of hosted zone to use. if true, use only private zones. if false, use only public zones
    * ``auth_username`` Alternative way to specify the access_key for authentication
    * ``auth_token`` Alternative way to specify the access_secret for authentication

.. _safedns:

safedns
    * ``auth_token`` Specify the api key to authenticate with

.. _sakuracloud:

sakuracloud
    * ``auth_token`` Specify access token for authentication
    * ``auth_secret`` Specify access secret for authentication

.. _softlayer:

softlayer
    * ``auth_username`` Specify username for authentication
    * ``auth_api_key`` Specify api private key for authentication

.. _transip:

transip
    * ``auth_username`` Specify username for authentication
    * ``auth_api_key`` Specify api private key for authentication

.. _ultradns:

ultradns
    * ``auth_token`` Specify token for authentication; if not set --auth-token, --auth-password are used
    * ``auth_username`` Specify username for authentication
    * ``auth_password`` Specify password for authentication

.. _vultr:

vultr
    * ``auth_token`` Specify token for authentication

.. _yandex:

yandex
    * ``auth_token`` Specify pdd token (https://tech.yandex.com/domain/doc/concepts/access-docpage/)

.. _zeit:

zeit
    * ``auth_token`` Specify your api token

.. _zilore:

zilore
    * ``auth_key`` Specify the zilore api key to use

.. _zonomi:

zonomi
    * ``auth_token`` Specify token for authentication
    * ``auth_entrypoint`` Use zonomi or rimuhosting api

