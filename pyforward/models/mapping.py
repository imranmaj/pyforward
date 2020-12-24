from __future__ import annotations

import socket
import random
from datetime import timedelta
from typing import List, Union, Literal

from bs4 import BeautifulSoup

from pyforward.models import Response
from pyforward.static import SCHEME
from pyforward.network import SSDP, Requester
from pyforward.exceptions import MappingError, NoSuchMappingError

class Mapping:
    _ssdp = SSDP()
    _igd = _ssdp.get_igd()
    _requester = Requester(_igd)

    def __init__(self, 
        external_port: int=None,
        internal_ip: str=None,
        internal_port: int=None,
        protocol: Union[Literal["TCP"], Literal["UDP"]]=None,
        description: str=None,
        duration: timedelta=None
    ):
        """
        external_port - external port on igd to map
        internal_ip - internal ip on local device to map
        internal_port - internal port on local device to map
        protocol - protocol to allow over port ("TCP" or "UDP")
        description - description of port forward
        duration - lease duration of port mapping as a timedelta
        """

        self.external_port = external_port
        self.internal_port = internal_port
        self.internal_ip = internal_ip
        self.protocol = protocol
        self.description = description
        self.duration = duration

    def enable(self):
        """
        Maps an external port to an internal port
        Returns Response

        Defaults external port to random open port
        Defaults internal ip to local ip
        Defaults internal port to random open port if ip is local ip, otherwise random
        Defaults protocol to TCP
        Defaults description to empty string
        Defaults duration to 604800 seconds (7 days)
        """

        external_port = self.external_port
        internal_ip = self.internal_ip
        internal_port = self.internal_port
        protocol = self.protocol
        description = self.description
        duration = self.duration
        
        # default external port to random open port
        if not self.external_port:
            external_port = self.get_open_external_port()
        # default internal ip to local ip
        if not self.internal_ip:
            internal_ip = self.get_local_ip()
        # default internal port to local port if internal ip is local ip
        if not self.internal_port and self.internal_ip == self.get_local_ip():
            internal_port = self.get_open_local_port()
        # otherwise random port
        else:
            internal_port = self._get_random_dynamic_port()
        # default protocol to tcp
        if not self.protocol:
            protocol = "TCP"
        # default description to ""
        if not self.description:
            description = ""
        # default duration to 604800 seconds
        if not self.duration:
            duration = timedelta(seconds=604800)

        # create AddPortMapping request
        ACTION = "AddPortMapping"
        CONTENT = """
            <m:{action} xmlns:m="{scheme}">
                <NewRemoteHost></NewRemoteHost>
                <NewExternalPort>{external_port}</NewExternalPort>
                <NewProtocol>{protocol}</NewProtocol>
                <NewInternalPort>{internal_port}</NewInternalPort>
                <NewInternalClient>{internal_ip}</NewInternalClient>
                <NewEnabled>1</NewEnabled>
                <NewPortMappingDescription>{description}</NewPortMappingDescription>
                <NewLeaseDuration>{duration}</NewLeaseDuration>
            </u:{action}>
        """.format(
            action=ACTION,
            scheme=SCHEME,
            external_port=external_port,
            protocol=protocol,
            internal_port=internal_port,
            internal_ip=internal_ip,
            description=description,
            duration=duration.total_seconds(),
        )

        r = self._requester.do_request(ACTION, CONTENT)

        parser = BeautifulSoup(r.text, "lxml-xml")
        # raise errors
        self.raise_errors(parser)

        # success
        return Response(
            external_ip=self.get_external_ip(),
            external_port=external_port,
            internal_ip=internal_ip,
            internal_port=internal_port,
            protocol=protocol,
            description=description,
            duration=duration
        )

    def disable(self):
        """
        Disables port mapping on this mappings external port and protocol
        """

        # create DeletePortMapping request
        ACTION = "DeletePortMapping"
        CONTENT = """
            <m:{action} xmlns:m="{scheme}">
                <NewRemoteHost></NewRemoteHost>
                <NewExternalPort>{external_port}</NewExternalPort>
                <NewProtocol>{protocol}</NewProtocol>
            </u:{action}>
        """.format(
            action=ACTION,
            scheme=SCHEME, 
            external_port=self.external_port, 
            protocol=self.protocol
        )

        r = self._requester.do_request(ACTION, CONTENT)

        parser = BeautifulSoup(r.text, "lxml-xml")
        # raise errors
        try:
            self.raise_errors(parser)
        except MappingError as e:
            if str(e) == "SpecifiedArrayIndexInvalid":
                raise NoSuchMappingError
            else:
                raise e

    @classmethod
    def disable_all(cls):
        """
        Disables all mappings
        """

        for mapping in cls.get_all_mappings():
            mapping.disable()

    def disable_matching(self):
        """
        Disables all mappings matching rules (interprets intialized values as rules to match with)
        """

        for mapping in self.get_all_mappings():
            if self.external_port == mapping.external_port:
                mapping.disable()
            if self.internal_ip == mapping.internal_ip:
                mapping.disable()
            if self.internal_port == mapping.internal_port:
                mapping.disable()
            if self.protocol == mapping.protocol:
                mapping.disable()
            if self.description == mapping.description:
                mapping.disable()
            if self.duration == mapping.duration:
                mapping.disable()

    def refresh(self):
        """
        Refreshes this port mapping
        Returns Response
        """

        self.disable()
        return self.enable()

    @classmethod
    def get_mapping(cls, index) -> Mapping:
        """
        Get a single mapping given the index in the IGD's table of mappings
        Returns Mapping
        """

        # create GetGenericPortMappingEntry request
        ACTION = "GetGenericPortMappingEntry"
        CONTENT = """
            <m:{action} xmlns:m="{scheme}">
                <NewPortMappingIndex>{index}</NewPortMappingIndex>
            </m:{action}>
        """.format(
            action=ACTION,
            scheme=SCHEME,
            index=index
        )

        r = cls._requester.do_request(ACTION, CONTENT)

        parser = BeautifulSoup(r.text, "lxml-xml")
        # raise errors
        try:
            cls.raise_errors(parser)
        except MappingError as e:
            if str(e) == "SpecifiedArrayIndexInvalid":
                raise NoSuchMappingError
            else:
                raise e

        # success
        external_port = parser.find("NewExternalPort").contents[0]
        internal_port = parser.find("NewInternalPort").contents[0]
        internal_ip = parser.find("NewInternalClient").contents[0]
        protocol = parser.find("NewProtocol").contents[0]
        try:
            description = parser.find("NewPortMappingDescription").contents[0]
        except IndexError:
            description = ""
        duration = parser.find("NewLeaseDuration").contents[0]

        return Mapping(
            external_port=external_port,
            internal_port=internal_port,
            internal_ip=internal_ip,
            protocol=protocol,
            description=description,
            duration=duration
        )

    @classmethod
    def get_all_mappings(cls) -> List[Mapping]:
        """
        Returns list of all active Mappings
        """

        index = 0
        all_mappings = []
        response = ""
        # keep going until we get an out of bounds error
        while True:
            try:
                response = cls.get_mapping(index)
            except NoSuchMappingError as e:
                break
            else:
                all_mappings.append(response)

            index += 1

        return all_mappings

    @classmethod
    def get_local_ip(cls) -> str:
        """
        Returns local ip address
        """

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # connect to igd device to check what ip is
            s.connect((cls._igd.ip, 0))
            ip = s.getsockname()[0]
            s.close()

            return ip

    @classmethod
    def get_external_ip(cls) -> str:
        """
        Returns the external ip address
        """

        ACTION = "GetExternalIPAddress"
        CONTENT = """
            <m:{action} xmlns:m="{scheme}">
            </u:{action}>
        """.format(
            action=ACTION,
            scheme=SCHEME
        )

        r = cls._requester.do_request(ACTION, CONTENT)

        parser = BeautifulSoup(r.text, "lxml-xml")
        # raise errors
        cls.raise_errors(parser)

        # success
        ip = parser.find("NewExternalIPAddress").contents[0]
        return ip

    @staticmethod
    def get_open_local_port() -> int:
        """
        Returns an available port on local machine
        """

        with socket.socket() as s:
            # os will assign port on bind when requested 0 port
            s.bind(("", 0))
            port = s.getsockname()[1]
            s.close()

            return port

    @classmethod
    def get_open_external_port(cls) -> int:
        """
        Returns available port on IGD
        """

        # temporarily use AddAnyPortMapping to get a valid port, then disable the map
        # create AddAnyPortMapping request
        ACTION = "AddAnyPortMapping"
        CONTENT = """
            <m:{action} xmlns:m="{scheme}">
                <NewRemoteHost></NewRemoteHost>
                <NewExternalPort>{external_port}</NewExternalPort>
                <NewProtocol>{protocol}</NewProtocol>
                <NewInternalPort>{internal_port}</NewInternalPort>
                <NewInternalClient>{internal_ip}</NewInternalClient>
                <NewEnabled>1</NewEnabled>
                <NewPortMappingDescription>{description}</NewPortMappingDescription>
                <NewLeaseDuration>{duration}</NewLeaseDuration>
            </u:{action}>
        """.format(
            action=ACTION,
            scheme=SCHEME,
            external_port=cls._get_random_dynamic_port(),
            protocol="TCP",
            internal_port=cls.get_open_local_port(),
            internal_ip=cls.get_local_ip(),
            description="",
            duration=0,
        )

        r = cls._requester.do_request(ACTION, CONTENT)

        parser = BeautifulSoup(r.text, "lxml-xml")
        # raise errors
        cls.raise_errors(parser)

        # success
        port = int(parser.find("NewReservedPort").contents[0])
        # deactivate so it can be used later
        cls(external_port=port, protocol="TCP").disable()

        return port

    @staticmethod
    def _get_random_dynamic_port() -> int:
        """
        Returns a random port number
        """

        port = random.randint(49152, 65535)
        return port

    @staticmethod
    def raise_errors(parser: BeautifulSoup):
        """
        Raises errors in response from IGD if they exist

        parser - bs4 parser of IGD response
        """

        if parser.find("errorDescription") is not None:
            error = parser.find("errorDescription").contents[0]
            raise MappingError(error)

    def __repr__(self) -> str:
        return f"Mapping(external_port={self.external_port}, internal_ip={self.internal_ip}, internal_port={self.internal_port}, protocol={self.protocol}, description={self.description}, duration={self.duration})"