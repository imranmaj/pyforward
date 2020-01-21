import re

import requests
from bs4 import BeautifulSoup
from yarl import URL

class IGD:
    def __init__(self, ssdp_response: bytes, ssdp_address: tuple):
        self.ip = ssdp_address[0]

        response = ssdp_response.decode()
        response = dict(re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", response))
        # get location of igd profile from info about igd device
        profile_location = response["LOCATION"]

        # look for control url (api to set port forwarding)
        profile = requests.get(profile_location).content
        parser = BeautifulSoup(profile, "lxml-xml")
        # look for types of services
        services = parser.find_all("serviceType")
        control_path = None
        for service in services:
            schema = service.string.split(":")[-2]
            if schema in ("WANIPConnection", "WANPPPConnection"):
                # find the path to control url
                control_path = service.parent.find("controlURL").string
                break
        # get full url
        self._control_url = URL(profile_location).with_path(control_path)

    @property
    def control_url(self) -> URL:
        return self._control_url