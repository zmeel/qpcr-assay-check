# qpcr-assay-check

**qpcr-assay-check** re-evaluates a real-time PCR (TaqMan) assay against all current public
sequence data at NCBI. It answers the questions a clinical microbiology laboratory asks each
year about an assay that is already in use:

1. **Does the assay still detect its target?** Which genomes of the target still match the
   primers and probes, which carry variants that may weaken detection, and which escape.
2. **Does it still detect *only* its target?** Is anything the assay must not detect (close
   relatives, other pathogens in the same specimen, human DNA) now predicted to amplify?
3. **Is the oligo design itself sound?** Melting temperatures, GC content, runs, hairpins and
   dimers of every primer and probe in the mix.

The answer is a record for the laboratory's quality system: an HTML report, a JSON record and an
Excel workbook, each with the tool version and a SHA-256 hash of every input.

> **In silico analysis does not replace experimental validation.** The tool shows where public
> sequences differ from the oligos and how published data classify those differences. It does
> not predict Ct values or analytical sensitivity. The laboratory must verify the software
> within its own quality system before relying on its output.

## Pages

| Page | What it explains |
|---|---|
| [How it works](How-it-works) | The workflow from assay file to report, step by step |
| [Finding the target in a genome](Finding-the-target-in-a-genome) | How the region of the assay is located in every genome: seeds, blocks, chains and the copy rule |
| [Judging primer and probe sites](Judging-primer-and-probe-sites) | How each oligo is aligned to each copy, the graded mismatch classes, and how a genome and a channel are judged |
| [Specificity search](Specificity-search) | The tiered remote BLAST search for off-target binding and predicted off-target products |
| [Data storage and cache](Data-storage-and-cache) | What is stored where, what is kept for how long, and why later runs are fast |
| [Limits and validation](Limits-and-validation) | What the tool cannot tell you, and what was measured to set its rules |

## Three principles

- **Every genome, not a sample.** For bacteria every genome assembly of the target in NCBI
  Datasets is scanned; for viruses every Nucleotide record. A percentage in the report is
  always a count over genomes, with its denominator shown.
- **Missing evidence is never "no flags".** A search that could not finish, a genome that could
  not be judged or a tier that was not searched makes the result *Incomplete*, never a pass.
- **Every rule names its source.** Mismatch classes come from published primer-mismatch studies
  (Stadhouders et al. 2010; Lefever et al. 2013); where no source exists the report says so
  and does not guess.

## Three kinds of assay

The tool is generic. An assay file describes its oligos, the region(s) they amplify (*loci*)
and the fluorescence channels read out (*channels*):

| Assay | Example | Loci | Channels |
|---|---|---|---|
| One forward, one reverse, one probe | CDC 2019-nCoV N1 | 1 | 1 |
| Several primers or probes on one region | *N. gonorrhoeae* opa, two probes in FAM | 1 | 1 |
| Several probes or targets on one region | *Legionella*: genus probe (VIC) + *L. pneumophila* probe (FAM) | 1 | 2 |
| A true multiplex | two regions, two targets | 2 or more | 2 or more |

Each channel is judged on its own target taxon: the *L. pneumophila* channel must detect
*L. pneumophila* and should stay silent in the other *Legionella* species, while the genus
channel must detect all of them.
