# Tests

## Run the tests

To run the tests on highest verbosity:

```
$ python manage.py test -v 2
```

If the tests are run repeatedly, use the `--keepdb` flag:

```
$ python manage.py test -v 2 --keepdb
```

## Code coverage

First, ensure test dependencies are installed:

```
$ poetry install --with test
```

Then, to generate coverage information:

```
$ coverage run --rcfile=../pyproject.toml manage.py test -v 2 --keepdb
```

This can be viewed in the command line:

```
$ coverage report
```

Or as a HTML report:

```
$ coverage html
```
