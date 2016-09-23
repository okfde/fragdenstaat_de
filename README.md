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
pip install -U -r requirements-dev.txt -e .
```

Initialise the database:
```
python manage.py migrate
```

Run the server:
```
python manage.py runserver
```
Now you can visit <http://localhost:8000>.

To customise settings, copy the example settings and edit:

```
cp fragdenstaat_de/local_settings.py.example fragdenstaat_de/local_settings.py
```

To have the German translation, you need to install [gettext](https://www.gnu.org/software/gettext/gettext.html) on your system. See the [Django documentation for details](https://docs.djangoproject.com/en/1.10/topics/i18n/translation/). Compile translations like this:

```
python manage.py compilemessages
```

## License

Froide and fragdenstaat_de are licensed under the MIT License.

Some folders contain an attributions.txt with more information about the copyright holders for files in this specific folder.
