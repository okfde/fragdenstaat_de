# FragDenStaat.de Theming

This repository contains the theming for
[FragDenStaat.de](https://fragdenstaat.de) - the German instance of [Froide](https://github.com/stefanw/froide).


Setup a separate Python virtual environment:

```
pip install virtualenv
python -m virtualenv fds-env
source fds-env/bin/activate
```

Then install dependencies:

```
pip install -r requirements.txt -e .
```


Copy `local_settings.py.example` to `local_settings.py`.

## License

Froide is licensed under the MIT License.

Some folders contain an attributions.txt with more information about the copyright holders for files in this specific folder.
