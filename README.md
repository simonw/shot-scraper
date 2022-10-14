# shot-scraper

[![PyPI](https://img.shields.io/pypi/v/shot-scraper.svg)](https://pypi.org/project/shot-scraper/)
[![Changelog](https://img.shields.io/github/v/release/simonw/shot-scraper?include_prereleases&label=changelog)](https://github.com/simonw/shot-scraper/releases)
[![Tests](https://github.com/simonw/shot-scraper/workflows/Test/badge.svg)](https://github.com/simonw/shot-scraper/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/shot-scraper/blob/master/LICENSE)

A command-line utility for taking automated screenshots of websites

For background on this project see [shot-scraper: automated screenshots for documentation, built on Playwright](https://simonwillison.net/2022/Mar/10/shot-scraper/).

## Documentation

- [Full documentation for shot-scraper](https://shot-scraper.datasette.io/)
- [Tutorial: Automating screenshots for the Datasette documentation using shot-scraper](https://simonwillison.net/2022/Oct/14/automating-screenshots/)
- [Release notes](https://github.com/simonw/shot-scraper/releases)

## Get started with GitHub Actions

To get started without installing any software, use the [shot-scraper-template](https://github.com/simonw/shot-scraper-template) template to create your own GitHub repository which takes screenshots of a page using `shot-scraper`. See [Instantly create a GitHub repository to take screenshots of a web page](https://simonwillison.net/2022/Mar/14/shot-scraper-template/) for details.

## Quick installation

You can install the `shot-scraper` CLI tool using [pip](https://pip.pypa.io/):

    pip install shot-scraper
    # Now install the browser it needs:
    shot-scraper install

## Taking your first screenshot

You can take a screenshot of a web page like this:

    shot-scraper https://datasette.io/

This will create a screenshot in a file called `datasette-io.png`.

Many more options are available, see [Taking a screenshot](https://shot-scraper.datasette.io/en/stable/screenshots.html) for details.

## Examples

- The [shot-scraper-demo](https://github.com/simonw/shot-scraper-demo) repository uses this tool to capture recently spotted owls in El Granada, CA according to [this page](https://www.owlsnearme.com/?place=127871), and to  generate an annotated screenshot illustrating a Datasette feature as described [in my blog](https://simonwillison.net/2022/Mar/10/shot-scraper/#a-complex-example).
- The [Datasette Documentation](https://docs.datasette.io/en/latest/) uses screenshots taken by `shot-scraper` running in the [simonw/datasette-screenshots](https://github.com/simonw/datasette-screenshots) GitHub repository, described in detail in [Automating screenshots for the Datasette documentation using shot-scraper](https://simonwillison.net/2022/Oct/14/automating-screenshots/).
- Ben Welsh built [@newshomepages](https://twitter.com/newshomepages), a Twitter bot that uses `shot-scraper` and GitHub Actions to take screenshots of news website homepages and publish them to Twitter. The code for that lives in [palewire/news-homepages](https://github.com/palewire/news-homepages).
- [scrape-hacker-news-by-domain](https://github.com/simonw/scrape-hacker-news-by-domain) uses `shot-scraper javascript` to scrape a web page. See [Scraping web pages from the command-line with shot-scraper](https://simonwillison.net/2022/Mar/14/scraping-web-pages-shot-scraper/) for details of how this works.
