# PyForward

Python port forwarding, for humans

## Overview

Easy to use port forwarding using UPnP's IGD-PCP (see [https://tools.ietf.org/html/rfc6970](https://tools.ietf.org/html/rfc6970) for more information). Great for peer-to-peer networking, etc.

Note that the default arguments for methods are set up for convenience. Calling `enable()` without any arguments will automatically forward an open port on the IGD to an open port on the host machine. Additionally, calling `disable()` or `refresh()` without any arguments will disable or refresh the mapping created with the last `enable` call.

Install requirements with:

`pip install -r requirements.txt`

On linux, you must install some packages first before running the pip command: 

`sudo apt-get install libxml2-dev libxslt-dev python-dev python3-lxml`

## Documentation

### `class PyForward`

#### `PyForward.__init__(wait_time=3, debug=False)`

Sets up PyForward service by attempting to connect to IGD

If there is no IGD available, throws `RuntimeError`

`wait_time` - how long to wait for IGD response (default is 3 seconds)

`debug` - whether to display debug information (will be written to log file regardless)

#### `PyForward.enable(external_port=None, internal_port=None, internal_ip=None, protocol="TCP", description="PyForward", duration=0)`

Maps an external port to an internal port

Returns tuple of external ip, external port, internal ip, internal port on success, error message on error


`external_port` - router port to forward from (default is random open port)

`internal_port` - port to forward to from router port (default is a random open port if ip is unspecified, otherwise random)

`internal_ip` - ip address to forward to (default is local ip address)

`protocol` - protocol to allow over port ("TCP" or "UDP") (default is "TCP")

`description` - description of port forward (default is "PyForward")

`duration` - lease duration of port mapping in seconds (default is 604800 seconds (7 days))

#### `PyForward.disable(external_port=None, protocol=None)`

Disables port mapping on a port and protocol

Returns True on success, error message on error


`external_port` - router port to disable forwarding from (default is port that forwarding was enabled on, if enable was called earlier)

`protocol` - protocol allowed over port to disable ("TCP" or "UDP") (default is protocol that forwarding was enabled on, if enable was called earlier)

#### `PyForward.disable_all(external_port=None, internal_port=None, internal_ip=None, protocol=None, description=None, duration=0)`

Disables all mappings matching given rules


`args` - same as args for enable

#### `PyForward.refresh(external_port=None, internal_port=None, internal_ip=None, protocol="TCP", description="PyForward", duration=0)`

Refreshes an existing port mapping

Returns tuple received from enable on success, error message on fail


`args` - same as args for enable, but default is values used in previous enable call

#### `PyForward.get_mapping(index)`

Get a single mapping given the index in the IGD's table of mappings

Returns dict of mapping on success, error message on fail


dict form:
```
{
    "external_port": <external port>,
    "internal_port": <internal port>,
    "internal_ip": <internal ip>,
    "protocol": <protocol>,
    "description": <description>,
    "duration": <remaining mapping lease duration>
}
```

#### `PyForward.get_all_mappings()`

Returns list of all port mappings (each mapping is dict with form described in get_mapping)

#### `PyForward.get_local_ip()`

Returns local ip address

#### `PyForward.get_external_ip()`

Returns the external ip address

#### `PyForward.get_open_local_port()`

Returns an available port on local machine

#### `PyForward.get_open_external_port()`

Returns available port on IGD

#### `PyForward.get_random_port()`

Returns a random port number

## Examples

### Create and then disable a mapping for an unspecified port

```
from pyforward import PyForward

pf = PyForward()
external_ip, external_port, internal_ip, internal_port = pf.enable()
pf.disable()
```

That's it!

### Delete all existing mappings

```
from pyforward import PyForward

pf = PyForward()
for mapping in pf.get_all_mappings():
    pf.disable(external_port=mapping["external_port"], protocol=mapping["protocol"])
```

### Refresh a mapping

```
from pyforward import PyForward
import time

pf = PyForward()
pf.enable(duration=5)
time.sleep(10) # mapping will expire
pf.refresh()
```

## License

See LICENSE.md for the full license under which this software is provided.