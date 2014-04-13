# -*- coding: utf-8 -*-

# Copyright 2012 Yao-Po Wang <blue119@gmail.com>

'''This modules handles export of LaTeX Code for Beamer'''

import re
import string
import logging
from PIL import Image

from zim.fs import File, FileNotFoundError
from zim.formats import *
from zim.parsing import TextBuffer

logger = logging.getLogger('zim.formats.beamer')


info = {
    'name': 'beamer',
    'desc':    'Beamer',
    'mimetype': 'application/x-tex',
    'extension': 'tex',
    'native': False,
    'import': False,
    'export': True,
}

# reverse dict
bullet_types = {
    UNCHECKED_BOX : '\\item[\\Square] ',
    XCHECKED_BOX  : '\\item[\\XBox] ',
    CHECKED_BOX   : '\\item[\\CheckedBox] ',
    BULLET        : '\\item ',
}

# H1 = slide title
# H2 = section title
# H3 = subsection title
# H4 = frame title
# H5 = block title
sectioning = {
    1:'',
    2:'\\section{%s}',
    3:'\\subsection{%s}',
    4:'\\begin{frame}[t]{%s}',
    5:'\\begin{block}{%s}'
}

sec_end_tag = {
    4:'\\end{frame}',
    5:'\\end{block}'
}

encode_re = re.compile(r'(\&|\$|\^|\%|\#|\_|\\|\<|\>|\n)')
encode_dict = {
    '\\': '$\\backslash$',
    '&': '\\$',
    '$': '\\$ ',
    '^': '\\^{}',
    '%': '\\%',
    '#': '\\# ',
    '_': '\\_',
    '>': '\\textgreater{}',
    '<': '\\textless{}',
    '\n': '\n\n',
}

def tex_encode(text):
    if not text is None:
        return encode_re.sub(lambda m: encode_dict[m.group(1)], text)
    else:
        return ''

class Dumper(DumperClass):

    def dump(self, tree):
        assert isinstance(tree, ParseTree)
        assert self.linker, 'LaTeX dumper needs a linker object'
        self.linker.set_usebase(False)
        self.end_tag_pending = []

        output = TextBuffer()
        self.dump_children(tree.getroot(), output)
        self.end_tag_pending.reverse()
        for et in self.end_tag_pending: output.append(sec_end_tag[et] + '\n')
        return output.get_lines()


    def dump_children(self, list, output, list_level = -1):

        if list.text:
            output.append(tex_encode(list.text))

        for element in list.getchildren():
            text = tex_encode(element.text)

            if element.tag in ('p', 'div'):
                if 'indent' in element.attrib:
                    indent = int(element.attrib['indent'])
                else:
                    indent = 0
                myoutput = TextBuffer()
                self.dump_children(element,myoutput)
                if indent:
                    myoutput.prefix_lines('\t'*indent)
                output.extend(myoutput)

            elif element.tag == 'h':
                level = int(element.attrib['level'])
                if level < 1: level = 1
                elif level > 5: level = 5

                if self.end_tag_pending:
                    if self.end_tag_pending[-1] == level and level == 5:
                        output.append(sec_end_tag[level] + '\n')
                        self.end_tag_pending.pop()

                    if level <= 4:
                        self.end_tag_pending.reverse()
                        for et in self.end_tag_pending:
                            output.append(sec_end_tag[et] + '\n')
                        self.end_tag_pending = []

                if level >= 4:
                    if level == 4: output.append('%' + '_' * 78 + '\n')
                    self.end_tag_pending.append(level)

                output.append(sectioning[level] % (text))

            elif element.tag == 'ul':
                output.append('\\begin{itemize}\n')
                self.dump_children(element, output, list_level=list_level+1)
                output.append('\\end{itemize}')

            elif element.tag == 'ol':
                start = element.attrib.get('start', 1)
                if start in string.lowercase:
                    type = 'a'
                    start = string.lowercase.index(start) + 1
                elif start in string.uppercase:
                    type = 'A'
                    start = string.uppercase.index(start) + 1
                else:
                    type = '1'
                    start = int(start)
                output.append('\\begin{enumerate}[%s]\n' % type)
                if start > 1:
                    output.append('\setcounter{enumi}{%i}\n' % (start-1))
                self.dump_children(element,output,list_level=list_level+1)
                output.append('\\end{enumerate}')

            elif element.tag == 'li':
                if 'bullet' in element.attrib:
                    bullet = bullet_types[element.attrib['bullet']]
                else:
                    bullet = bullet_types[BULLET]
                output.append('\t'*list_level+bullet)
                self.dump_children(element, output, list_level=list_level) # recurse
                output.append('\n')

            elif element.tag == 'pre':
                indent = 0
                if 'indent' in element.attrib:
                    indent = int(element.attrib['indent'])
                myoutput = TextBuffer()
                myoutput.append(element.text)
                if indent:
                    myoutput.prefix_lines('    ' * indent)
                output.append('\n\\begin{lstlisting}\n')
                output.extend(myoutput)
                output.append('\n\\end{lstlisting}\n')

            elif element.tag == 'sub':
                output.append('$_{%s}$' % element.text)

            elif element.tag == 'sup':
                output.append('$^{%s}$' % element.text)

            elif element.tag == 'img':

                print element.attrib
                if list_level == -1: output.append('\\begin{center}\n')

                #we try to get images about the same visual size, therefore need to specify dot density
                #96 dpi seems to be common for computer monitors
                dpi = 96
                done = False
                if 'type' in element.attrib and element.attrib['type'] == 'equation':
                    try:
                        # Try to find the source, otherwise fall back to image
                        src = element.attrib['src'][:-4] + '.tex'
                        file = self.linker.resolve_file(src)
                        if file is not None:
                            equation = file.read().strip()
                        else:
                            equation = None
                    except FileNotFoundError:
                        logger.warn('Could not find latex equation: %s', src)
                    else:
                        if equation:
                            output.append('\\begin{math}\n')
                            output.extend(equation)
                            output.append('\n\\end{math}')
                            done = True

                if not done:
                    #  if 'width' in element.attrib and not 'height' in element.attrib:
                        #  options = 'width=%fin, keepaspectratio=true' \
                                #  % ( float(element.attrib['width']) / dpi )
                    #  elif 'height' in element.attrib and not 'width' in element.attrib:
                        #  options = 'height=%fin, keepaspectratio=true' \
                                #  % ( float(element.attrib['height']) / dpi )
                    #  else:
                        #  options = ''

                    imagepath = File(self.linker.link(element.attrib['src'])).path
                    # imagepath = self.linker.link(element.attrib['src'])

                    # choose refering to width or height by w/h ratio.
                    # if height bigger than width, set to 0.8 by textheight.
                    # Otherwise if width bigger than height, set to 0.9 by
                    # textwidth
                    img_width, img_height = Image.open(imagepath).size
                    ratio = img_width / img_height

                    if ratio > 1:
                        options = 'width=0.90\\textwidth'
                    else:
                        options = 'height=0.80\\textheight'

                    image = '\\includegraphics[%s]{%s}' % (options, imagepath)
                    if 'href' in element.attrib:
                        href = self.linker.link(element.attrib['href'])
                        output.append('\\href{%s}{%s}' % (href, image))
                    else:
                        output.append(image)

                if list_level == -1:  output.append('\n\\end{center}\n')

            elif element.tag == 'link':
                href = self.linker.link(element.attrib['href'])
                output.append('\\href{%s}{%s}' % (href, text))

            elif element.tag == 'emphasis':
                output.append('\\emph{'+text+'}')

            elif element.tag == 'strong':
                output.append('\\textbf{'+text+'}')

            elif element.tag == 'mark':
                output.append('\\uline{'+text+'}')

            elif element.tag == 'strike':
                output.append('\\sout{'+text+'}')

            elif element.tag == 'code':
                success = False
                #Here we try several possible delimiters for the inline verb command of LaTeX
                for delim in '+*|$&%!-_':
                    if not delim in text:
                        success = True
                        output.append('\\lstinline'+delim+text+delim)
                        break

                if not success:
                    assert False, 'Found no suitable delimiter for verbatim text: %s' % element
                    pass

            elif element.tag == 'tag':
                # LaTeX doesn't have anything similar to tags afaik
                output.append(text)

            else:
                assert False, 'Unknown node type: %s' % element

            if element.tail:
                output.append(tex_encode(element.tail))

