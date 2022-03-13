#!/bin/bash

# exit when any command fails
set -e

mkdir -p examples
# Without the -o option should produce www-example-com.png
(cd examples && shot-scraper https://www.example.com/)
# Run again should produce www-example-com.1.png
(cd examples && shot-scraper https://www.example.com/)
shot-scraper https://www.example.com/ -o - > examples/from-stdout-example.png
# HTML page
echo '<html><h1>This is a page on disk</h1><p>...</p></html>' > local.html
shot-scraper local.html -o examples/local.png
# Full page
shot-scraper https://github.com/ -o examples/github.com.png
# Using a selector
shot-scraper https://simonwillison.net/ -s '#bighead' -o examples/bighead.png
# Selector and JavaScript
shot-scraper https://simonwillison.net/ -s '#bighead' \
  --javascript "document.body.style.backgroundColor = 'pink';" \
  -o examples/bighead-pink.png
# Multiple selectors
shot-scraper https://simonwillison.net/ \
  -s '#bighead' -s .overband --padding 20 \
  -o examples/bighead-multi-selector.png
# Height and width
shot-scraper https://simonwillison.net/ -w 400 -h 800 -o examples/simon-narrow.png
# JPEG quality
shot-scraper https://simonwillison.net/ \
  -h 800 -o examples/simonwillison-quality-80.jpg --quality 80
# Selector with a wait
shot-scraper 'https://www.owlsnearme.com/?place=127871' \
  --selector 'section.secondary' \
  -o examples/owlsnearme-wait.jpg \
  --wait 2000
# Accessbility
shot-scraper accessibility https://datasette.io/ \
  > examples/datasette-accessibility.json
shot-scraper accessibility https://simonwillison.net \
  --javascript "document.getElementById('wrapper').style.display='none'" \
  > examples/simonwillison-accessibility-javascript.json
shot-scraper accessibility https://simonwillison.net \
  --javascript "document.getElementById('wrapper').style.display='none'" \
  --output examples/simonwillison-accessibility-javascript-and-dash-output.json
shot-scraper accessibility local.html -o examples/local-accessibility.json
# PDF
(cd examples && shot-scraper pdf https://datasette.io/tools)
shot-scraper pdf https://datasette.io \
  --landscape -o examples/datasette-landscape.pdf
shot-scraper pdf https://datasette.io/tutorials/learn-sql \
  -o - > examples/learn-sql.pdf
shot-scraper pdf local.html -o examples/local.pdf
## JavaScript
shot-scraper javascript https://datasette.io/ "document.title" \
  > examples/datasette-io-title.json
shot-scraper javascript datasette.io "
new Promise(done => setInterval(
  () => {
    done({
      title: document.title,
      tagline: document.querySelector('.tagline').innerText
    });
  }, 1000
));" -o examples/datasette-io-title-tagline-from-promise.json
# And using multi
echo '
- output: examples/example.com.png
  url: http://www.example.com/
- output: examples/w3c.org.png
  url: https://www.w3.org/
- output: examples/bighead-from-multi.png
  url: https://simonwillison.net/
  selector: "#bighead"
- output: examples/bighead-pink-from-multi.png
  url: https://simonwillison.net/
  selector: "#bighead"
  javascript: |
    document.body.style.backgroundColor = "pink";
- output: examples/simon-narrow-from-multi.png
  url: https://simonwillison.net/
  width: 400
  height: 800
- output: examples/simon-quality-80-from-multi.png
  url: https://simonwillison.net/
  height: 800
  quality: 80
# Multiple selectors
- output: examples/bighead-multi-selector-from-multi.png
  url: https://simonwillison.net/
  selectors:
  - "#bighead"
  - .overband
  padding: 20
# Local page on disk
- url: local.html
  output: examples/local-from-multi.png
' | shot-scraper multi -
