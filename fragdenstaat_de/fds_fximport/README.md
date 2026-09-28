## Certificate renewal

The file `pad_cadata.pem` needs to be renewed roughly every year.

This can be done via the output of:

```
uv run --with aia python -c "from aia import AIASession; print(AIASession().cadata_from_url('https://pad.frontex.europa.eu/Token/Create'))"
```
