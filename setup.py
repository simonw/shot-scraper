from setuptools import setup
import os

VERSION = "0.17"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="shot-scraper",
    description="A command-line utility for taking automated screenshots of websites",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Simon Willison",
    url="https://github.com/simonw/shot-scraper",
    project_urls={
        "Issues": "https://github.com/simonw/shot-scraper/issues",
        "CI": "https://github.com/simonw/shot-scraper/actions",
        "Changelog": "https://github.com/simonw/shot-scraper/releases",
    },
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["shot_scraper"],
    entry_points="""
        [console_scripts]
        shot-scraper=shot_scraper.cli:cli
    """,
    install_requires=["click", "PyYAML", "playwright", "click-default-group"],
    extras_require={"test": ["pytest", "cogapp", "pytest-mock"]},
    python_requires=">=3.7",
)
