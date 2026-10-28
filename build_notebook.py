"""Regenerates notebooks/CBR-OF_QDA_Colab.ipynb from codebook.py and cbrof_qda.py.
Run from the repository root after editing either file:  python tools/build_notebook.py"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
read = lambda f: open(os.path.join(ROOT, f), encoding='utf-8').read()
def md(text): return {'cell_type': 'markdown', 'metadata': {}, 'source': text.splitlines(keepends=True)}
def code(text): return {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [], 'source': text.splitlines(keepends=True)}
cells = [
    md('# CBR-OF workshop transcripts: live qualitative analysis\n\n'
       'Runs the full pipeline on your transcripts: text extraction, rule-based coding against the codebook, quote selection, '
       'NVivo-style queries, NMF topic modelling, all figures, an Excel coding workbook and a Word report, downloaded as one zip.\n\n'
       '**How to use:** Runtime > Run all, then upload the transcripts zip when the upload button appears (about 1 minute).\n\n'
       '**Privacy:** transcripts are processed in this Colab session only. Do not commit transcripts or outputs to a public repository.'),
    md('## 1. Install packages'),
    code("!pip install -q python-docx openpyxl squarify wordcloud scikit-learn"),
    md('## 2. Codebook\nEdit the themes, nodes and coding rules here to refine the coding, then re-run the cells below.'),
    code('%%writefile codebook.py\n' + read('codebook.py')),
    md('## 3. Analysis pipeline'),
    code('%%writefile cbrof_qda.py\n' + read('cbrof_qda.py')),
    md('## 4. Upload the transcripts zip and run\n'
       'Optional settings: `N_TOPICS` (number of inductive topics). To benchmark against manual coding, upload a CSV with columns '
       '`file, excerpt, nodes` and set `MANUAL` to its file name. To mask names, include `names_to_mask.txt` (one name per line) inside the zip.'),
    code("N_TOPICS = 8\nMANUAL = None   # e.g. 'manual_coding.csv'\n\n"
         "import importlib, sys\nsys.path.insert(0, '.')\nimport codebook, cbrof_qda\nimportlib.reload(codebook); importlib.reload(cbrof_qda)\n"
         "from google.colab import files\nprint('Upload the transcripts zip')\nup = files.upload()\nzip_name = [k for k in up if k.endswith('.zip')][0]\n"
         "result = cbrof_qda.run(zip_name, 'CBR-OF_QDA_Results', MANUAL, N_TOPICS)\nfiles.download(result)"),
    md('## 5. Preview the figures'),
    code("from IPython.display import Image, display\nimport glob\nfor p in sorted(glob.glob('CBR-OF_QDA_Results/figures/*.png')):\n    print(p.split('/')[-1]); display(Image(p, width=900))"),
]
nb = {'nbformat': 4, 'nbformat_minor': 0, 'metadata': {'colab': {'provenance': []}, 'kernelspec': {'name': 'python3', 'display_name': 'Python 3'}, 'language_info': {'name': 'python'}}, 'cells': cells}
os.makedirs(os.path.join(ROOT, 'notebooks'), exist_ok=True)
json.dump(nb, open(os.path.join(ROOT, 'notebooks', 'CBR-OF_QDA_Colab.ipynb'), 'w', encoding='utf-8'), indent=1)
print('notebooks/CBR-OF_QDA_Colab.ipynb written')
