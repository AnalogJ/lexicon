googleclouddns
    * ``auth_service_account_info`` 
        specify the service account info in the google json format:
        can be either the path of a file prefixed by 'file::' (eg. file::/tmp/service_account_info.json)
        or the base64 encoded content of this file prefixed by 'base64::'
        (eg. base64::eyjhbgcioyj...)


.. note::
   
   The Google Cloud DNS provider requires the JSON file which contains the service account info to connect to the API.
   This service account must own the project role DNS > DNS administrator for the project associated to the DNS zone.
   You can create a new service account, associate a private key, and download its info through this url:
   https://console.cloud.google.com/iam-admin/serviceaccounts?authuser=2

