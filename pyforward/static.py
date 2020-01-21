SCHEME = "urn:schemas-upnp-org:service:WANIPConnection:1"
SSDP_REQUEST = (
    b"M-SEARCH * HTTP/1.1\r\n"
    b"Host:239.255.255.250:1900\r\n"
    b"ST:urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n"
    b'Man:"ssdp:discover"\r\n'
    b"MX:3\r\n"
)
SLEEP_TIME = 3