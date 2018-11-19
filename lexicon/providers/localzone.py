from __future__ import absolute_import, print_function
import logging

from .base import Provider as BaseProvider


# localzone is an optional dependency of lexicon; do not throw an ImportError if
# the dependency is unmet.
try:
    import localzone
except ImportError:
    pass


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = []


def ProviderParser(subparser):
    subparser.add_argument(
        "--filename", help="specify location of zone master file")


class Provider(BaseProvider):
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.ttl = self._get_lexicon_option("ttl")
        self.domain = self._get_lexicon_option("domain")
        self.origin = self.domain + "."
        self.filename = self._get_provider_option("filename")

    def authenticate(self):
        """Authentication is not required for localzone."""
        pass

    def create_record(self, type, name, content):
        """
        Create a resource record. If a record already exists with the same
        content, do nothing.
        """
        result = False
        name = self._relative_name(name)
        ttl = None

        # TODO: shoud assert that this is an int
        if self.ttl:
            ttl = self.ttl

        with localzone.manage(self.filename, self.origin, autosave=True) as z:
            if z.add_record(name, type, content, ttl=ttl):  # pylint: disable=no-member
                result = True

        LOGGER.debug("create_record: %s", result)
        return result

    def list_records(self, type=None, name=None, content=None):
        """
        Return a list of records matching the supplied params. If no params are
        provided, then return all zone records. If no records are found, return
        an empty list.
        """
        if name:
            name = self._relative_name(name)
        if not type:
            type = "ANY"

        filter = {"rdtype": type, "name": name, "content": content}

        with localzone.manage(self.filename, self.origin, autosave=True) as z:
            records = z.find_record(**filter)  # pylint: disable=no-member

        result = []
        for record in records:
            rdict = {
                "type": record.rdtype,
                "name": self._full_name(record.name),
                "ttl": record.ttl,
                "content": record.content,
                "id": record.hashid,
            }

            if rdict["type"] == "TXT":
                rdict["content"] = rdict["content"].replace('"', "")

            result.append(rdict)

        LOGGER.debug("list_records: %s", result)
        return result

    def update_record(self, identifier, type=None, name=None, content=None):
        """
        Update a record. Returns `False` if no matching record is found.
        """
        result = False

        # TODO: some providers allow content-based updates without supplying an
        # ID, and therefore `identifier` is here optional. If we don't receive
        # an ID, look it up.
        if not identifier and type and name:
            records = self.list_records(type, name)
            if len(records) == 1:
                identifier = records[0]["id"]

        if identifier and content:
            with localzone.manage(self.filename, self.origin, autosave=True) as z:
                if z.update_record(identifier, content):  # pylint: disable=no-member
                    result = True

        LOGGER.debug("update_record: %s", result)
        return result

    def delete_record(self, identifier=None, type=None, name=None, content=None):
        """
        Delete record(s) matching the provided params. If there is no match, do
        nothing.
        """
        ids = []

        if identifier:
            ids.append(identifier)
        elif not identifier and type and name:
            records = self.list_records(type, name, content)
            if len(records) > 0:
                ids = [record["id"] for record in records]

        if len(ids) > 0:
            LOGGER.debug("delete_records: %s", ids)
            with localzone.manage(self.filename, self.origin, autosave=True) as z:
                for hashid in ids:
                    z.remove_record(hashid)  # pylint: disable=no-member
                    LOGGER.debug("delete_record: %s", hashid)

        return True

    def _request(self, **kwargs):
        """
        Not required.
        """
        pass
