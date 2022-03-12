#!/bin/bash

# exit when any command fails
set -e

mkdir -p examples
shot-scraper https://github.com/ -o examples/github.com.png
shot-scraper https://simonwillison.net/ -s '#bighead' -o examples/bighead.png
shot-scraper https://simonwillison.net/ -s '#bighead' \
  --javascript "document.body.style.backgroundColor = 'pink';" \
  -o examples/bighead-pink.png
shot-scraper https://simonwillison.net/ -w 400 -h 800 -o examples/simon-narrow.png
shot-scraper https://simonwillison.net/ \
  -h 800 -o examples/simonwillison-quality-80.jpg --quality 80
shot-scraper 'https://www.owlsnearme.com/?place=127871' \
  --selector 'section.secondary' \
  -o examples/owlsnearme-wait.jpg \
  --wait 2000
shot-scraper accessibility https://datasette.io/ \
  > examples/datasette-accessibility.json
shot-scraper accessibility https://simonwillison.net \
  --javascript "document.getElementById('wrapper').style.display='none'" \
  > examples/simonwillison-accessibility-javascript.json
shot-scraper accessibility https://simonwillison.net \
  --javascript "document.getElementById('wrapper').style.display='none'" \
  --output examples/simonwillison-accessibility-javascript-and-dash-output.json
shot-scraper pdf https://datasette.io \
  --landscape -o examples/datasette-landscape.pdf
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
' | shot-scraper multi -
