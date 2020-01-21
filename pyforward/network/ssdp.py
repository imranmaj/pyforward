import socket
import re

from pyforward.static import SSDP_REQUEST, SLEEP_TIME
from pyforward.exceptions import IGDNotFoundError
from pyforward.network import IGD

class SSDP:
    def __init__(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(SSDP_REQUEST, ("239.255.255.250", 1900))
        sock.settimeout(SLEEP_TIME)

        try:
            self.response, self.address = sock.recvfrom(4096)
        except TimeoutError:
            raise IGDNotFoundError

    def get_igd(self) -> IGD:
        return IGD(self.response, self.address)