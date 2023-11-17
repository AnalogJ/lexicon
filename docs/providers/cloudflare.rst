cloudflare
    * ``auth_username`` Specify email address for authentication (for global api key only)

    * ``auth_token`` Specify token for authentication (global api key or api token)

    * ``zone_id`` Specify the zone id (if set, api token can be scoped to the target zone)


.. note::
   
   There are two ways to provide an authentication granting edition to the target CloudFlare DNS zone.
   
   1 - A Global API key, with --auth-username and --auth-token flags.
   
   2 - An unscoped API token (permissions Zone:Zone(read) + Zone:DNS(edit) for all zones), with --auth-token flag.
   
   3 - A scoped API token (permissions Zone:Zone(read) + Zone:DNS(edit) for one zone), with --auth-token and --zone-id flags.
   
   Finding zone_id value is explained in CloudFlare `Doc <https://developers.cloudflare.com/fundamentals/setup/find-account-and-zone-ids/>`_
   

