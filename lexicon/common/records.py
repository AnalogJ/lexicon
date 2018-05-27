# Common class for DNS record
class Record(object):
    def __init__(self, type=None, id=None, name=None, content=None, ttl=None):
        self.type = type
        self.id = id
        self.name = name
        self.content = content
        self.ttl = ttl

class A_Record(Record):
    def __init__(self, id=None, name=None, content=None, ttl=None, **kwargs):
        super(A_Record, self).__init__('A', id, name, content, ttl)

class AAAA_Record(Record):
    def __init__(self, id=None, name=None, content=None, ttl=None, **kwargs):
        super(AAAA_Record, self).__init__('AAAA', id, name, content, ttl)

class CNAME_Record(Record):
    def __init__(self, id=None, name=None, content=None, ttl=None, **kwargs):
        super(CNAME_Record, self).__init__('CNAME', id, name, content, ttl)

class TXT_Record(Record):
    def __init__(self, id=None, name=None, content=None, ttl=None, **kwargs):
        super(TXT_Record, self).__init__('TXT', id, name, content, ttl)

class MX_Record(Record):
    def __init__(self, id=None, name=None, content=None, ttl=None, priority=None, **kwargs):
        super(MX_Record, self).__init__('MX', id, name, content, ttl)
        self.priority = priority

class RecordFactory:
    @staticmethod
    def create_record(type, **kwargs):
        record = None
        if type == 'A':
            record = A_Record(**kwargs)
        elif type == 'AAAA':
            record = AAAA_Record(**kwargs)
        elif type == 'CNAME':
            record = CNAME_Record(**kwargs)
        elif type == 'TXT':
            record = TXT_Record(**kwargs)
        elif type == 'MX':
            record = MX_Record(**kwargs)
        
        return record
