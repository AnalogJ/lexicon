class LexiconError(Exception):
    def __init__(self, message):
        super(Exception, self).__init__(message)

class AuthenticationError(LexiconError):
    def __init__(self, message=None):
        super(Exception, self).__init__(message)

class DomainNotFoundError(LexiconError):
    def __init__(self, message=None):
        super(Exception, self).__init__(message)

class RecordNotFoundError(LexiconError):
    def __init__(self, message=None):
        super(Exception, self).__init__(message)

class InvalidTTLError(LexiconError):
    def __init__(self, message=None):
        super(Exception, self).__init__(message)
