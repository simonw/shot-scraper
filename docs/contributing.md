# Contributing

To contribute to this tool, first checkout the code. Then create a new virtual environment:

    cd shot-scraper
    python -m venv venv
    source venv/bin/activate

Or if you are using `pipenv`:

    pipenv shell

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest

Some of the tests exercise the CLI utility directly. Run those like so:

    tests/run_examples.sh
