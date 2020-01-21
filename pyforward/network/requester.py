from typing import Dict

import requests
from requests.models import Response

from pyforward.static import SCHEME
from pyforward.network import IGD

class Requester:
    def __init__(self, igd: IGD):
        self.igd = igd

    @staticmethod
    def make_headers(action: str) -> Dict[str, str]:
        """
        Generates headers for request

        action - SOAPAction
        """

        return {
            "SOAPAction": "{scheme}#{action}".format(
                scheme=SCHEME,
                action=action
            ),
            "Content-Type": "text/xml"
        }

    @staticmethod
    def make_body(content: str) -> str:
        """
        Generates body for request

        content - body content
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

    def do_request(self, action: str, content: str) -> Response:
        headers = self.make_headers(action)
        body = self.make_body(content)

        return requests.post(
            self.igd.control_url,
            headers=headers, 
            data=body
        )