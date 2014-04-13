README
======

Installation
------------
* copy data and zim to your pyzim.
* patch zim/formats/\__init__.py with formats.patch

Tutorial
--------
- brain down your mind in pyzim and export to beamer format.
    zim.py --export --template=data/templates/beamer/Default.tex --output=./ --format=beamer ./pyzim-export-beamer/example/

- Convert TeX to pdf with pdflatex
- Do pdflatex again for indexing. 

Further
------
* Beamer titles defined by heading
    * H1 = slide title
    * H2 = section title
    * H3 = subsection title
    * H4 = frame title
    * H5 = block title

* The example come from [examples of beamer class](http://goo.gl/5OEYfU)
