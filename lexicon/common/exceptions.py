
__all__ = [
    'LexiconError',
    'ZoneError',
    'ZoneDoesNotExistError',
    'ZoneAmbiguousError',
    'ZoneAlreadyExistsError',
    'RecordError',
    'RecordDoesNotExistError',
    'RecordAmbiguousError',
    'RecordAlreadyExistsError',
]


# Exceptions
class LexiconError(Exception):
    def __init__(self, value, provider=None):
        super(LexiconError, self).__init__(value)
        self.value = value
        self.provider = provider

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return ("<LexiconError in " +
                repr(self.provider) +
                " " +
                repr(self.value) + ">")

class ZoneError(LexiconError):
    error_type = 'ZoneError'
    kwargs = ('zone_id', )

    def __init__(self, value, provider, zone_id):
        self.zone_id = zone_id
        super(ZoneError, self).__init__(value=value, provider=provider)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return ('<%s in %s, zone_id=%s, value=%s>' %
                (self.error_type, repr(self.provider),
                 repr(self.zone_id), self.value))



class ZoneDoesNotExistError(ZoneError):
    error_type = 'ZoneDoesNotExistError'

class ZoneAmbiguousError(ZoneError):
    error_type = 'ZoneAmbiguousError'

class ZoneAlreadyExistsError(ZoneError):
    error_type = 'ZoneAlreadyExistsError'



class RecordError(LexiconError):
    error_type = 'RecordError'

    def __init__(self, value, provider, record_id):
        self.record_id = record_id
        super(RecordError, self).__init__(value=value, provider=provider)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return ('<%s in %s, record_id=%s, value=%s>' %
                (self.error_type, repr(self.driver),
                 self.record_id, self.value))



class RecordDoesNotExistError(RecordError):
    error_type = 'RecordDoesNotExistError'

class RecordAmbiguousError(ZoneError):
    error_type = 'RecordAmbiguousError'

class RecordAlreadyExistsError(RecordError):
    error_type = 'RecordAlreadyExistsError'
