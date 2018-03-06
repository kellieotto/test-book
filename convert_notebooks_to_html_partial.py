"""
This script takes the .ipynb files in the notebooks/ folder and removes the
hidden cells as well as the newlines before closing </div> tags so that the
resulting HTML partial can be embedded in a Gitbook page easily.
For reference:
https://nbconvert.readthedocs.org/en/latest/nbconvert_library.html
http://nbconvert.readthedocs.org/en/latest/nbconvert_library.html#using-different-preprocessors
"""

import glob
import re
import os

import bs4
import nbformat
from nbconvert import HTMLExporter
from traitlets.config import Config

preamble = """
<script type="text/x-mathjax-config">
  MathJax.Hub.Config({
    tex2jax: {
      inlineMath: [['$','$']],
      processEscapes: true
    }
  });
</script>
"""

# Use ExtractOutputPreprocessor to extract the images to separate files
config = Config()
config.HTMLExporter.preprocessors = [
    'nbconvert.preprocessors.ExtractOutputPreprocessor',
]

# Output a HTML partial, not a complete page
html_exporter = HTMLExporter(config=config)
html_exporter.template_file = 'basic'

# Output notebook HTML partials into this directory
NOTEBOOK_HTML_DIR = 'notebooks-html'

# Output notebook HTML images into this directory
NOTEBOOK_IMAGE_DIR = 'notebooks-images'

# The prefix for the interact button links. The path format string gets filled
# with path to notebook to open from root of repo
INTERACT_LINK = 'https://mybinder.org/v2/gh/kellieotto/test-book/gh-pages?filepath={path}'

# Used to ensure all the closing div tags are on the same line for Markdown to
# parse them properly
CLOSING_DIV_REGEX = re.compile('\s+</div>')

import pdb

def convert_notebooks_to_html_partial(notebook_paths):
    """
    Converts notebooks in notebook_paths to HTML partials in NOTEBOOK_HTML_DIR
    """
    for notebook_path in notebook_paths:
        # Computes <name>.ipynb from notebooks/<name>.ipynb
        filename = notebook_path.split('/')[-1]
        # Computes <name> from <name>.ipynb
        basename = filename.split('.')[0]
        # Computes <name>.html from notebooks/<name>.ipynb
        outfile_name = basename + '.html'

        # This results in images like AB_5_1.png for a notebook called AB.ipynb
        unique_image_key = basename
        # This sets the img tag URL in the rendered HTML. This restricts the
        # the chapter markdown files to be one level deep. It isn't ideal, but
        # the only way around it is to buy a domain for the staging textbook as
        # well and we'd rather not have to do that.
        output_files_dir = '/' + NOTEBOOK_IMAGE_DIR

        extract_output_config = {
            'unique_key': unique_image_key,
            'output_files_dir': output_files_dir,
        }

        notebook = nbformat.read(notebook_path, 4)
        raw_html, resources = html_exporter.from_notebook_node(notebook,
            resources=extract_output_config)

        html = preamble + _extract_cells(raw_html)

        with_wrapper = """<div id="ipython-notebook">
            <a class="interact-button" href="{interact_link}">Interact</a>
            {html}
        </div>""".format(
            interact_link=INTERACT_LINK.format(path='notebooks/' + filename),
            html=html
        )

        # Remove newlines before closing div tags
        final_output = CLOSING_DIV_REGEX.sub('</div>', with_wrapper)

        # Write out HTML
        outfile_path = os.path.join(os.curdir, NOTEBOOK_HTML_DIR, outfile_name)
        with open(outfile_path, 'w') as outfile:
            outfile.write(final_output)

        # Write out images
        for relative_path, image_data in resources['outputs'].items():
            image_name = relative_path.split('/')[-1]
            final_image_path = '{}/{}'.format(NOTEBOOK_IMAGE_DIR, image_name)
            with open(final_image_path, 'wb') as outimage:
                outimage.write(image_data)
        print(outfile_path + " written.")

def _extract_cells(html):
    """Return a html partial of divs with cell contents."""
    doc = bs4.BeautifulSoup(html, 'html5lib')

    def is_cell(classes):
        return classes and ('inner_cell' in classes or 'output_subarea' in classes)

    divs = doc.find_all('div', class_=is_cell)
    visible = [div for div in divs if '# HIDDEN' not in str(div)]

    def remove_empty_spans_and_prompts(tag):
        map(lambda t: t.decompose(), tag.find_all('div', class_='prompt'))
        map(lambda t: t.decompose(), tag.find_all('span', text='None'))
    [remove_empty_spans_and_prompts(div) for div in visible]

    return '\n'.join(map(str, visible))

if __name__ == '__main__':
    notebook_paths = glob.glob('notebooks/*.ipynb')
    convert_notebooks_to_html_partial(notebook_paths)