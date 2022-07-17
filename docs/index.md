# API

This is how you instantiate a connection with milky.

```
>>> from milky import Transport
>>> t = Transport(api_key, secret)
>>> t.start_auth(open=True)
>>>
>>> # Wait for user to grant permissions.
>>> print(t.whoami)
"milkymark" with read permissions
```

::: milky.Transport
