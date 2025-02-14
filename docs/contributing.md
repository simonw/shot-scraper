(contributing)=

# Contributing

To contribute to this tool, first checkout the code. Then create a new virtual environment:
```bash
cd shot-scraper
python -m venv venv
source venv/bin/activate
```
Or if you are using `pipenv`:
```bash
pipenv shell
```
Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```
Then you'll need to install the Playwright browsers too:
```bash
shot-scraper install
```
To run the tests:
```bash
pytest
```
Some of the tests exercise the CLI utility directly. Run those like so:
```bash
tests/run_examples.sh
```
## Documentation

Documentation for this project uses [MyST](https://myst-parser.readthedocs.io/) - it is written in Markdown and rendered using Sphinx.

To build the documentation locally, run the following:
```bash
cd docs
pip install -r requirements.txt
make livehtml
```
This will start a live preview server, using [sphinx-autobuild](https://pypi.org/project/sphinx-autobuild/).

The CLI `--help` examples in the documentation are managed using [Cog](https://github.com/nedbat/cog). Update those files like this:
```bash
cog -r docs/*.md
```
## Publishing the release notes

After pushing a release, I use the following to create a screenshot of the release notes to use in social media posts:
```bash
shot-scraper https://github.com/simonw/shot-scraper/releases/tag/0.15 \
  --selector '.Box-body' --width 700 \
  --retina
```
[Example post](https://twitter.com/simonw/status/1569431710345089024).
