azure
    * ``auth_client_id`` Specify the client id (aka application id) of the app registration

    * ``auth_client_secret`` Specify the client secret of the app registration

    * ``auth_tenant_id`` Specify the tenant id (aka directory id) of the app registration

    * ``auth_subscription_id`` Specify the subscription id attached to the resource group

    * ``resource_group`` Specify the resource group hosting the dns zone to edit


.. note::
   
   The Azure provider orchestrates the DNS zones hosted in a resource group for a subscription
   in Microsoft Azure Cloud. To authenticate, an App registration must be created in an Azure
   Active Directory. This App registration must be granted Admin for API permissions to
   Domain.ReadWrite.All" to this Active Directory, and must have a usable Client secret.
   

