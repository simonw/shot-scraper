# Using shot-scraper with GitHub Actions

`shot-scraper` was designed with GitHub Actions for screenshot automation in mind.

## shot-scraper-template

The [shot-scraper-template](https://github.com/simonw/shot-scraper-template) template repository can be used to quickly create your own GitHub repository with GitHub Actions configured to take screenshots of a page and write it back to the repository. Read [Instantly create a GitHub repository to take screenshots of a web page](https://simonwillison.net/2022/Mar/14/shot-scraper-template/) for details.

## Building a workflow from scratch

This Actions workflow can be used to install `shot-scraper` and its dependencies, take screenshots defined in the `shots.yml` file in that repository and then write the resulting screenshots back to the same repository:

```yaml
name: Take screenshots

on:
  push:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  shot-scraper:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python 3.10
      uses: actions/setup-python@v3
      with:
        python-version: "3.10"
    - uses: actions/cache@v3
      name: Configure pip caching
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip
    - name: Cache Playwright browsers
      uses: actions/cache@v3
      with:
        path: ~/.cache/ms-playwright/
        key: ${{ runner.os }}-playwright
    - name: Install dependencies
      run: |
        pip install shot-scraper
        shot-scraper install
    - name: Take shots
      run: |
        shot-scraper multi shots.yml
    - name: Commit and push
      run: |-
        git config user.name "Automated"
        git config user.email "actions@users.noreply.github.com"
        git add -A
        timestamp=$(date -u)
        git commit -m "${timestamp}" || exit 0
        git pull --rebase
        git push
```
The `actions/cache@v3` steps set up [caching](https://github.com/actions/cache), so your workflow will only download and install the necessary software the very first time it runs.

## Optimizing PNGs using Oxipng

You can losslessy compress the PNGs generated using `shot-scraper` by running them through [Oxipng](https://github.com/shssoichiro/oxipng). Add the following steps to the beginning of your workflow to install Oxing:

```yaml
    - name: Cache Oxipng
      uses: actions/cache@v3
      with:
        path: ~/.cargo/
        key: ${{ runner.os }}-cargo
    - name: Install Oxipng
      run: |
        cargo install oxipng
```

Then after running `shot-scraper` add this step to compress the images:

```yaml
    - name: Optimize PNGs
      run: |-
        oxipng -o 4 -i 0 --strip safe *.png
```

[simonw/datasette-screenshots](https://github.com/simonw/datasette-screenshots) is an example of a repository that uses this pattern.

See [Optimizing PNGs in GitHub Actions using Oxipng](https://til.simonwillison.net/github-actions/oxipng) for more on how this works.

