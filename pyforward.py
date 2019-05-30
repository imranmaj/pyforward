"""
Copyright (c) 2019 Imran Majeed
See LICENSE.md for the full license under which this software is provided.

PyForward: Python port forwarding, for humans
Implements UPnP's IGD-PCP for NAT traversal
See https://tools.ietf.org/html/rfc6970
"""

import socket
from socket import timeout as TimeoutError
import re
import requests
import random
import os
import datetime
from bs4 import BeautifulSoup
from yarl import URL

class PyForward:
    def __init__(self, wait_time=3, debug=False):
        """
        wait_time - how long to wait for IGD response (default is 3 seconds)
        debug - whether to display debug information (will be written to log file regardless)

        Sets up PyForward service by attempting to connect to IGD
        If UPnP is not supported, throws RuntimeError
        """
        
        # whether to print debug info
        self.debug = debug

        # scheme constant
        self.SCHEME = "urn:schemas-upnp-org:service:WANIPConnection:1"

        self.log("Starting PyForward service")

        # ssdp request to find igd location
        SSDP_REQUEST = (
            b"M-SEARCH * HTTP/1.1\r\n"
            b"Host:239.255.255.250:1900\r\n"
            b"ST:urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n"
            b'Man:"ssdp:discover"\r\n'
            b"MX:3\r\n"
        )
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # ask network for info about the igd device
        self.log("Looking for IGD")
        sock.sendto(SSDP_REQUEST, ("239.255.255.250", 1900))

        # wait before timing out
        sock.settimeout(wait_time)
        try:
            # receive information about igd device, ip address of igd
            response, address = sock.recvfrom(4096)
        except TimeoutError:
            # request for igd timed out, none available
            self.log("No IGD available")
            raise RuntimeError("Could not find a UPnP enabled IGD")
        else:
            self.log("IGD detected")

        # ip address of gateway device
        self.igd_ip = address[0]
        self.log("IGD ip is", self.igd_ip)

        # split into tuples containing header, value
        response = response.decode()
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
        self.control_url = URL(profile_location).with_path(control_path)
        self.log("Control url is", self.control_url)

        self.log("Successfully finished PyForward service setup")

    def body(self, content):
        """
        content - body content

        Generates body for request
        """

        return """
            <?xml version="1.0"?>
            <s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"
                    xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" >
                <s:Body>
                    {content}
                </s:Body>
            </s:Envelope>
        """.format(content=content)

    def headers(self, action):
        """
        action - SOAPAction

        Generates headers for request
        """

        return {
            "SOAPAction": "{scheme}#{action}".format(
                scheme=self.SCHEME,
                action=action
            ),
            "Content-Type": "text/xml"
        }

    def enable(
        self,
        external_port=None,
        internal_port=None,
        internal_ip=None,
        protocol="TCP",
        description="PyForward",
        duration=0
    ):
        """
        external_port - router port to forward from (default is random open port)
        internal_port - port to forward to from router port 
            (default is a random open port if ip is unspecified, otherwise random)
        internal_ip - ip address to forward to (default is local ip address)
        protocol - protocol to allow over port ("TCP" or "UDP") (default is "TCP")
        description - description of port forward (default is "PyForward")
        duration - lease duration of port mapping in seconds (default is 604800 seconds (7 days))

        Maps an external port to an internal port
        Returns tuple of external ip, external port, internal ip, internal port on success,
            error message on error
        """

        if not protocol.upper() in ("TCP", "UDP"):
            raise ValueError("Protocol must be TCP or UDP")

        ACTION = "AddPortMapping"
        
        # set external port if not chosen by user
        if not external_port:
            external_port = self.get_open_external_port()
        # set internal port if not chosen by user
        if not internal_ip and not internal_port:
            internal_port = self.get_open_local_port()
        # cannot pick port ourselves because it could be a different computer
        elif internal_ip and not internal_port:
            internal_port = self.get_random_port()
        # set ip if not chosen by user
        if not internal_ip:
            internal_ip = self.get_local_ip()

        # save values
        self.external_port = external_port
        self.internal_port = internal_port
        self.internal_ip = internal_ip
        self.protocol = protocol
        self.description = description
        self.duration = duration

        # create AddPortMapping request
        body = self.body(
            """
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
                scheme=self.SCHEME,
                external_port=external_port,
                protocol=protocol,
                internal_port=internal_port,
                internal_ip=internal_ip,
                description=description,
                duration=duration,
            )
        )
        headers = self.headers(ACTION)

        r = requests.post(
            self.control_url,
            headers=headers, 
            data=body
        )
        self.log(
            "Attempted to enable mapping: \nexternal port:", external_port, 
            "\nprotocol:", protocol,
            "\ninternal port:", internal_port,
            "\ninternal ip", internal_ip,
            "\ndescription:", description,
            "\nduration:", duration
        )

        parser = BeautifulSoup(r.text, "lxml-xml")
        # error
        if parser.find("errorDescription") is not None:
            error = parser.find("errorDescription").contents[0]
            self.log("Error:", error)

            return error

        # success
        self.log("Mapping successful")
        return self.get_external_ip(), external_port, internal_ip, internal_port

    def disable(self, external_port=None, protocol=None):
        """
        external_port - router port to disable forwarding from 
            (default is port that forwarding was enabled on, if enable was called earlier)
        protocol - protocol allowed over port to disable ("TCP" or "UDP") 
            (default is protocol that forwarding was enabled on, if enable was called earlier)

        Disables port mapping on a port and protocol
        Returns True on success, error message on error
        """

        if not protocol.upper() in ("TCP", "UDP"):
            raise ValueError("Protocol must be TCP or UDP")

        ACTION = "DeletePortMapping"

        assert external_port is not None or self.external_port is not None, "External port must be specified for disable"
        assert protocol is not None or self.protocol is not None, "Protocol must be specified for disable"

        # set external port if not chosen by user
        if not external_port:
            external_port = self.external_port
        # set internal port if not chosen by user
        if not protocol:
            protocol = self.protocol

        # create DeletePortMapping request
        body = self.body(
            """
                <m:{action} xmlns:m="{scheme}">
                    <NewRemoteHost></NewRemoteHost>
                    <NewExternalPort>{external_port}</NewExternalPort>
                    <NewProtocol>{protocol}</NewProtocol>
                </u:{action}>
            """.format(
                action=ACTION,
                scheme=self.SCHEME, 
                external_port=external_port, 
                protocol=protocol
            )
        )
        headers = self.headers(ACTION)

        r = requests.post(
            self.control_url,
            headers=headers, 
            data=body
        )
        self.log(
            "Attempted to disable mapping of external port", external_port, 
            "with protocol", protocol
        )

        parser = BeautifulSoup(r.text, "lxml-xml")
        # error
        if parser.find("errorDescription") is not None:
            error = parser.find("errorDescription").contents[0]
            self.log("Error:", error)

            return error

        # success
        self.log("Disable successful")
        return True

    def refresh(
            self,
            external_port=None,
            internal_port=None,
            internal_ip=None,
            protocol=None,
            description=None,
            duration=None
        ):
        """
        args - same as args for enable
            (default is values used in previous enable call)

        Refreshes an existing port mapping
        Returns tuple received from enable on success,
            error message on fail
        """

        if not protocol.upper() in ("TCP", "UDP"):
            raise ValueError("Protocol must be TCP or UDP")

        # set values to values specified by previous enable call
        if external_port is None:
            external_port = self.external_port
        if internal_port is None:
            internal_port = self.internal_port
        if internal_ip is None:
            internal_ip = self.internal_ip
        if protocol is None:
            protocol = self.protocol
        if description is None:
            description = self.description
        if duration is None:
            duration = self.duration

        # disable old mapping
        response = self.disable(external_port=external_port, protocol=protocol)
        if response is str:
            # got an error message
            self.log("Could not refresh due to error")

            return response
        
        # enable new mapping with same args
        response = self.enable(
            external_port=external_port,
            internal_port=internal_port,
            internal_ip=internal_ip,
            protocol=protocol,
            description=description,
            duration=duration
        )
        if response is str:
            # got an error message
            self.log("Could not refresh due to error")

            return response

        # success
        self.log("Refresh successful")
        # return tuple from enable
        return response

    def get_mapping(self, index):
        """
        Get a single mapping given the index in the IGD's table of mappings

        Returns dict of mapping on success, error message on fail

        dict form:
        {
            "external_port": <external port>,
            "internal_port": <internal port>,
            "internal_ip": <internal ip>,
            "protocol": <protocol>,
            "description": <description>,
            "duration": <remaining mapping lease duration>
        }
        """

        ACTION = "GetGenericPortMappingEntry"

        # create GetGenericPortMappingEntry request
        body = self.body(
            """
                <m:{action} xmlns:m="{scheme}">
                    <NewPortMappingIndex>{index}</NewPortMappingIndex>
                </m:{action}>
            """.format(
                action=ACTION,
                scheme=self.SCHEME,
                index=index
            )
        )
        headers = self.headers(ACTION)

        r = requests.post(
            self.control_url,
            headers=headers, 
            data=body
        )
        self.log("Attempted to get mapping at index", index)

        parser = BeautifulSoup(r.text, "lxml-xml")
        # error
        if parser.find("errorDescription") is not None:
            error = parser.find("errorDescription").contents[0]
            self.log("Error:", error)

            return error

        # success
        mapping = {
            "external_port": parser.find("NewExternalPort").contents[0],
            "internal_port": parser.find("NewInternalPort").contents[0],
            "internal_ip": parser.find("NewInternalClient").contents[0],
            "protocol": parser.find("NewProtocol").contents[0],
            "description": parser.find("NewPortMappingDescription").contents[0],
            "duration": parser.find("NewLeaseDuration").contents[0]
        }
        self.log("Found mapping successfully, got mapping", mapping)
        return mapping

    def get_all_mappings(self):
        """
        Returns list of all port mappings
            (each mapping is dict with form described in get_mapping)
        """

        index = 0
        all_responses = []
        response = ""
        # keep going until we get an out of bounds error
        while not "SpecifiedArrayIndexInvalid" in response:
            response = self.get_mapping(index)
            all_responses.append(response)

            index += 1
        self.log("No more mappings")

        # delete the last response (it's the error message)
        del all_responses[-1]

        return all_responses

    def get_local_ip(self):
        """
        Returns local ip address
        """

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # connect to igd device to check what ip is
            s.connect((self.igd_ip, 0))
            ip = s.getsockname()[0]
            s.close()

            self.log("Local ip is", ip)
            return ip

    def get_external_ip(self):
        """
        Returns the external ip address
        """

        ACTION = "GetExternalIPAddress"

        body = self.body(
            """
                <m:{action} xmlns:m="{scheme}">
                </u:{action}>
            """.format(
                action=ACTION,
                scheme=self.SCHEME
            )
        )
        headers = self.headers(ACTION)

        r = requests.post(
            self.control_url,
            headers=headers, 
            data=body
        )

        parser = BeautifulSoup(r.text, "lxml-xml")
        # error
        if parser.find("errorDescription") is not None:
            error = parser.find("errorDescription").contents[0]
            self.log("Error:", error)

            return error

        # success
        ip = parser.find("NewExternalIPAddress").contents[0]
        self.log("External ip is", ip)
        return ip

    def get_open_local_port(self):
        """
        Returns an available port on local machine
        """

        with socket.socket() as s:
            # os will assign port on bind when requested 0 port
            s.bind(("", 0))
            port = s.getsockname()[1]
            s.close()

            self.log("Open local port is", port)
            return port

    def get_open_external_port(self):
        """
        Returns available port on IGD
        """

        ACTION = "AddAnyPortMapping"

        # temporarily use AddAnyPortMapping to get a valid port, then disable the map
        # create AddAnyPortMapping request
        body = self.body(
            """
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
                scheme=self.SCHEME,
                external_port=self.get_random_port(),
                protocol="TCP",
                internal_port=self.get_open_local_port(),
                internal_ip=self.get_local_ip(),
                description="PyForward",
                duration=0,
            )
        )
        headers = self.headers(ACTION)
        r = requests.post(
            self.control_url,
            headers=headers, 
            data=body
        )

        parser = BeautifulSoup(r.text, "lxml-xml")
        # error
        if parser.find("errorDescription") is not None:
            error = parser.find("errorDescription").contents[0]
            self.log("Error:", error)

            return error

        # success
        port = int(parser.find("NewReservedPort").contents[0])
        self.log("Open external port is", port)
        # deactivate so it can be used later
        self.disable(external_port=port, protocol="TCP")

        return port

    def get_random_port(self):
        """
        Returns a random port number
        """

        port = random.randint(49152, 65535)

        self.log("Random port is", port)
        return port

    def log(self, *args):
        """
        If debug level was set as True,
            prints debug information to console and writes to file
        """

        if self.debug:
            # assemble full log message
            full_message = " ".join([str(arg) for arg in args])
            # add current time
            full_message = "[%s] %s" % (str(datetime.datetime.now()), full_message)

            if not os.path.isfile("log.txt"):
                open("log.txt", "w").close()

            # write to file
            with open("log.txt", "a") as f:
                f.write(full_message + "\n")
            # print to console
            print(full_message)
