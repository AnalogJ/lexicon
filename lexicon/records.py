import inspect
import re
import sys
from abc import ABC
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar, Union

import dns
from dns.name import Name
from dns.rdata import Rdata
from dns.rdatatype import RdataType

T = TypeVar("T", bound="Record")


@dataclass
class RecordsFilter:
    identifier: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    content: Optional[str] = None


@dataclass
class Record(ABC):
    rname: Name
    rdata: Rdata
    identifier: Optional[str] = None
    ttl: Optional[int] = None
    rdatatype: ClassVar[RdataType] = NotImplemented

    @property
    def name(self) -> str:
        return self.rname.to_text()

    @property
    def content(self) -> str:
        return self.rdata.to_text()

    @property
    def type(self):
        return dns.rdatatype.to_text(self.rdata.rdtype)

    def to_text(self):
        rdclass = dns.rdataclass.to_text(self.rdata.rdclass)
        ttl = f" {self.ttl}s" if self.ttl else ""

        return f"{self.name}{ttl} {rdclass} {self.type} {self.content}"

    def to_dict(self):
        dict_ = {"type": self.type, "name": self.name, "content": self.content}
        if self.ttl:
            dict_["ttl"] = self.ttl

        return dict_

    @classmethod
    def from_text(cls: Type[T], text: str) -> T:
        rdtype = dns.rdatatype.to_text(cls.rdatatype)
        match = re.match(rf"^(.*)IN {rdtype}(.*)$", text)
        if not match:
            raise ValueError(f"Invalid string to split: {text}")

        name_ttl = match.group(1).strip()
        content = match.group(2).strip()

        match = re.match(r"^(.*)\s+(\d+[smhdw])$", name_ttl)
        ttl: Optional[int]
        if match:
            name = match.group(1).strip()
            ttl = _parse_duration(match.group(2).strip())
        else:
            name = name_ttl
            ttl = None

        return cls.create(name, content, ttl=ttl)

    @classmethod
    def from_dict(cls: Type[T], dict_: Dict[str, Any]) -> T:
        return cls.create(dict_["name"], dict_["content"], ttl=dict_.get("ttl"))

    @classmethod
    def create(cls, name: str, content: str, ttl: Optional[int] = None):
        rname = dns.name.from_text(name)
        rdata = dns.rdata.from_text(dns.rdataclass.IN, cls.rdatatype, content)

        return cls(rname=rname, rdata=rdata, ttl=ttl)


class ARecord(Record):
    rdatatype = dns.rdatatype.A


class AAAARecord(Record):
    rdatatype = dns.rdatatype.AAAA


class CNAMERecord(Record):
    rdatatype = dns.rdatatype.CNAME


class MXRecord(Record):
    rdatatype = dns.rdatatype.MX


class NSRecord(Record):
    rdatatype = dns.rdatatype.NS


class SOARecord(Record):
    rdatatype = dns.rdatatype.SOA


class TXTRecord(Record):
    rdatatype = dns.rdatatype.TXT


class SRVRecord(Record):
    rdatatype = dns.rdatatype.SRV


class LOCRecord(Record):
    rdatatype = dns.rdatatype.LOC


_RECORD_CLASSES: Dict[RdataType, Type[Record]] = {
    entry[1].rdatatype: entry[1]
    for entry in inspect.getmembers(
        sys.modules[__name__], lambda o: inspect.isclass(o) and issubclass(o, Record)
    )
}


def from_text(text: str) -> Record:
    exceptions: List[Exception] = []
    for record in _RECORD_CLASSES.values():
        try:
            return record.from_text(text)
        except Exception as e:
            # Ignore, we try all possible types
            exceptions.append(e)

    for error in exceptions:
        print(str(error), file=sys.stderr)
    raise ValueError(f"Could not parse entry: {text}")


def from_dict(dict_: Dict[str, Any]) -> Record:
    rdatatype = dns.rdatatype.from_text(dict_["type"])

    if rdatatype not in _RECORD_CLASSES:
        raise ValueError(f"Unsupported rdatatype: {rdatatype}")

    return _RECORD_CLASSES[rdatatype].from_dict(dict_)


def _parse_duration(duration: str) -> int:
    if duration.endswith("s"):
        return int(duration[:-1])
    if duration.endswith("m"):
        return int(duration[:-1]) * 60
    if duration.endswith("h"):
        return int(duration[:-1]) * 60 * 60
    if duration.endswith("d"):
        return int(duration[:-1]) * 60 * 60 * 24
    if duration.endswith("w"):
        return int(duration[:-1]) * 60 * 60 * 24 * 7
    raise ValueError(f"Invalid duration {duration}")
