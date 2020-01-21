from datetime import timedelta
from typing import Union, Literal

class Response:
    def __init__(self,
        external_ip: str=None,
        external_port: int=None,
        internal_ip: str=None,
        internal_port: int=None,
        protocol: Union[Literal["TCP"], Literal["UDP"]]=None,
        description: str=None,
        duration: timedelta=None
    ):
        """
        external_ip - external ip on igd which was mapped
        external_port - external port on IGD which was mapped
        internal_ip - internal ip on local device which was mapped
        internal_port - internal port which was mapped
        protocol - protocol to allow over port ("TCP" or "UDP")
        description - description of port forward
        duration - lease duration of port mapping as a timedelta
        """

        self.external_ip = external_ip
        self.external_port = external_port
        self.internal_ip = internal_ip
        self.internal_port = internal_port
        self.protocol = protocol
        self.description = description
        self.duration = duration

    def __repr__(self) -> str:
        return f"Response(external_ip={self.external_ip}, external_port={self.external_port}, internal_ip={self.internal_ip}, internal_port={self.internal_port}, protocol={self.protocol}, description={self.description}, duration={self.duration}))"