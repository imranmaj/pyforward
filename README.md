# PyForward

Pythonic port forwarding over UPnP's IGD-PCP

## Overview

Easy to use port forwarding using Universal Plug 'n Play's Internet Gateway Device Port Control Protocol (see [https://tools.ietf.org/html/rfc6970](https://tools.ietf.org/html/rfc6970) for more information).

Install requirements with:

`pip install -r requirements.txt`

On Linux, you must install some packages first before running the pip command: 

`sudo apt-get install libxml2-dev libxslt-dev python-dev python3-lxml`

## Documentation

### `class Mapping`

Port forwards are defined with mappings. A Mapping represents the mapping of a port on the internet gateway device (external port and IP) to an internal device (internal port and IP).

#### `Mapping.__init__(external_port: int, internal_port: int, internal_ip: str, protocol: Union[Literal["TCP"], Literal["UDP"]], description: str, duration: datetime.timedelta)`


* `external_port` - external port on IGD to map

* `internal_ip` - internal ip on local device to map

* `internal_port` - internal port on local device to map

* `protocol` - protocol to allow over port ("TCP" or "UDP")

* `description` - description of port forward

* `duration` - lease duration of port mapping. This is a `timedelta` object from the built-in `datetime` module

#### `Mapping.enable() -> Response`

Enables this mapping. Returns a Response object.

If attributes are not assigned values when this object is initalized, they are defaulted to certain values for the purposes of this method.

* Defaults `external_port` to random open port

* Defaults `internal_ip` to local IP

* Defaults `internal_port` to random open port if IP is local IP, otherwise random

* Defaults `protocol` to TCP

* Defaults `description` to empty string

* Defaults `duration` to `timedelta(seconds=604800)` (7 days)

Because of these defaults, calling `enable()` without any arguments will automatically forward an open port on the IGD to an open port on the host machine.

#### `Mapping.disable()`

Disables this mapping. The Mapping to disable is only determined based on `external_port` and `protocol`.

#### `Mapping.disable_all()` (`@classmethod`)

Disables all mappings.

#### `Mapping.disabled_matching()`

Disables all mappings that match at least one of the attributes that this Mapping was initialized with.

#### `Mapping.refresh() -> Response`

Refreshes this mapping. Returns a Response object.

#### `Mapping.get_mapping(index) -> Mapping` (`@classmethod`)

Get a single mapping given the index in the IGD's table of mappings. Returns a Mapping object.

#### `Mapping.get_all_mappings() -> List[Mapping]` (`@classmethod`)

Returns list of all Mappings.

#### `Mapping.get_local_ip() -> str` (`@classmethod`)

Returns local IP address.

#### `Mapping.get_external_ip() -> str` (`@classmethod`)

Returns the external IP address.

#### `Mapping.get_open_local_port() -> int` (`@staticmethod`)

Returns an available port on local machine.

#### `Mapping.get_open_external_port() -> int` (`@classmethod`)

Returns available port on IGD.

### `class Response`

Returned when a Mapping is enabled or refreshed in order to provide full information on the mapping.

`Response.external_ip` - external IP on IGD which was mapped

`Response.external_port` - external port on IGD which was mapped

`Response.internal_ip` - internal IP on local device which was mapped

`Response.internal_port` - internal port which was mapped

`Response.protocol` - protocol to allow over port ("TCP" or "UDP")

`Response.description` - description of port forward

`Response.duration` - lease duration of port mapping as a timedelta

## Examples

### Create and then disable a mapping to the local machine

```
from pyforward import Mapping

m = Mapping()
m.enable()
m.disable()
```

### Get all mappings to host machine

```
from pyforward import Mapping

print([mapping for mapping in Mapping.get_all_mappings() if mapping.internal_ip == Mapping.get_local_ip()])
```

### Delete all mappings to host machine

```
from pyforward import Mapping

Mapping.disable_all(internal_ip=Mapping.get_local_ip())
```

### Refresh a mapping

```
from datetime import timedelta
from time import sleep

from pyforward import Mapping

m = Mapping(duration=timedelta(seconds=5)) # mapping expires after 5 seconds
m.enable()
sleep(10) # the mapping will expire after this time
m.refresh()
```

## License

See LICENSE.md for the full license under which this software is provided.