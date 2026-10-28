# CBR-OF Qualitative Analysis

Live, reproducible qualitative analysis of stakeholder workshop transcripts for **community-based rehabilitation and prevention care services for obstetric fistula (CBR-OF)** in Kenya.

Give it a zip of transcripts and it returns one zip with NVivo-style outputs: a coded dataset, figures, tables, an Excel coding workbook and a Word report.

## What the pipeline does

Every step runs live on the transcripts you supply:

| Step | Method |
|---|---|
| Text extraction | Reads `.docx`, `.txt` or `.md` files in any folder layout inside the zip; removes transcription service banners |
| Segmentation | Splits each transcript into sentences, the coding unit |
| Deductive coding | Tests every sentence against the coding rules of 37 child nodes under 7 themes (`codebook.py`). Specific rules score 1, broad rules score 0.5, and a sentence is coded when its score reaches 1. Adjacent coded sentences are merged into coding references, as in NVivo |
| Quote selection | Ranks references for each node by rules matched, TF-IDF similarity to the node definition and length, then picks the best quotes from different transcripts. Transcription errors are corrected in square brackets and personal names are masked |
| Inductive analysis | Non-negative matrix factorisation (NMF) topic modelling on all sentences, independent of the codebook, with a topic-to-theme alignment matrix |
| NVivo-style queries | Coding summary, word frequency (stemmed, stop words removed), matrix coding (theme by transcript), coding coverage, theme co-occurrence |
| Benchmark (optional) | Sentence-level recall, precision and Cohen's kappa per theme against a manual coding file |

## Outputs

```
CBR-OF_QDA_Results.zip
├── CBR-OF_Thematic_Analysis_Report.docx   Word report with all tables, figures and selected quotes
├── CBR-OF_Coding_Workbook.xlsx            Codebook, coded references, sentence coding, matrices, topics
├── summary.json                           Key counts
├── figures/                               9 PNG figures (hierarchy chart, node references, word frequency,
│                                          word cloud, matrix, coverage, co-occurrence, topics, alignment)
└── tables/                                CSV copy of every workbook sheet
```

## Run it

### Option A: Google Colab (no installation)

1. Click the **Open in Colab** badge above, or in Colab choose **File > Open notebook > GitHub** and paste the repository URL.
2. Choose **Runtime > Run all**.
3. Upload the transcripts zip when the upload button appears. The results zip downloads automatically after about a minute.

### Option B: your own computer

```bash
git clone https://github.com/YOUR-USERNAME/cbrof-qualitative-analysis.git
cd cbrof-qualitative-analysis
pip install -r requirements.txt
python cbrof_qda.py path/to/transcripts.zip
```

Options:

```bash
python cbrof_qda.py transcripts.zip --topics 10                      # number of inductive topics
python cbrof_qda.py transcripts.zip --manual manual_coding.csv       # benchmark against manual coding
python cbrof_qda.py transcripts.zip --out my_results                 # output folder name
```

The manual coding file is a CSV with the columns `file` (transcript name without extension), `excerpt` (verbatim text) and `nodes` (node IDs separated by semicolons, for example `T1.1;T5.3`).

## Refining the coding

All analytic decisions live in `codebook.py`:

- `THEMES` and `NODES`: names, definitions and coding rules (regular expressions; prefix a rule with `~` to make it a weak rule).
- `MIN_SCORE`, `WEAK`, `MIN_WORDS`: coding thresholds.
- `EXCLUDE`: patterns for facilitation talk that should not be coded.
- `CORRECTIONS`: known transcription errors and the word to show in quotes.

After editing, re-run the pipeline. If you use the Colab notebook, regenerate it so it carries your changes:

```bash
python tools/build_notebook.py
```

## Privacy and ethics

**This repository contains code only. Never commit transcripts, audio, names or outputs.**

- Workshop transcripts include survivors' accounts of illness, abandonment and trauma, and the names of participants. Publishing them would breach participant confidentiality and, in most cases, the terms of ethical approval.
- `.gitignore` blocks zips, Word and Excel files, CSVs, audio, the results folder and `names_to_mask.txt`, so they are not uploaded by accident.
- Names after a title (Dr, Mr, Mrs, Ms, Madam, Prof, Sister) are masked automatically. To mask other names, put a file called `names_to_mask.txt` (one name per line) **inside your transcripts zip**. Keep it private: a list of participant names is itself identifying data.
- Colab processes files in a temporary session on Google's servers. Check that this is permitted by your ethics approval and data protection obligations (including Kenya's Data Protection Act, 2019) before uploading transcripts.

## Methodological notes

Rule-based coding is transparent and reproducible, but it is literal. It finds ideas expressed in the vocabulary of the rules, can miss ideas phrased differently, and cannot interpret irony or context. It cannot attribute speakers in unlabelled transcripts. On the Phase 3 workshop data, sentence-level agreement with an independent manual coding was moderate to substantial (Cohen's kappa 0.42 to 0.77 across the seven themes). Treat the output as a structured first pass to be reviewed by the research team, and check every quote against the audio before publication.

## Citation

If you use this code, please cite the repository:

> Kavulavu B. M. (2026). *CBR-OF qualitative analysis* [Computer software]. GitHub. https://github.com/Independent-Learner1/cbrof-qualitative-analysis

## Licence

MIT. See `LICENSE`.
