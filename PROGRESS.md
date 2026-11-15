# Progress (work in progress, branch `wip`)

Last updated: 15 November 2026. Delete this file before merging to `main`.

## Done

- **Data.** `code/fetch_data.py` downloads prices, exchange rates and the T-bill yield from Yahoo
  Finance with fixed dates (20 July 2015 to 13 November 2026). Everything is converted to US dollars
  and sampled weekly. Found and fixed an exchange-rate timing problem in Yahoo's data
  (see `data/README.md`).
- **Analysis.** `part1_frontier.py` (asset statistics, correlations, exact frontier, reference
  portfolios, CVaR), `part2_out_of_sample.py` (rolling test, hold-out since July 2025, end-date
  sensitivity), `part3_bootstrap.py` (2,000 resamples). Results are in `results/`.
- **Interactive plots.** Six pages in `plots/` (0.03 to 1.5 MB each, down from 8 and 18 MB), plus the
  landing page `index.html`. Rendered and checked locally in a browser.
- **Static figures and note.** `figures/` (four figures), `main.tex` with tables and numbers generated
  by `code/tables.py`, compiled to `TOK_EFFICIENT_FRONTIER_3D.pdf` (8 pages, no LaTeX warnings).
- **Repo structure.** New `README.md`, `LICENSE` (MIT), `requirements.txt`, `.gitignore`,
  `data/README.md`. The first version is preserved in `legacy/`.
- **Full rerun from a fresh download** reproduces the same numbers.

## Left to do

1. **Check the README against `results/`.** The note and the website take their numbers from the JSON
   files automatically; the README tables were typed by hand and have not been cross-checked yet.
2. **Look at the plot pages once more.** The 2D charts had a last layout change (toolbar moved to the
   side) that has not been re-rendered.
3. **Decide on the AI line.** `README.md` ("About"), `index.html` (footer) and the note (last
   paragraph) each say that AI tools assisted in developing the project, as the first version's
   README did. Keep, reword or remove.
4. **Merge `wip` into `main`.** GitHub Pages is already switched on for this repo and serves the root
   of `main`, so the site goes live as soon as `index.html` is on `main`. `.nojekyll` is included.
5. **Rename the repo to `efficient-frontier-3d`.** The links in `README.md`, `index.html` and
   `main.tex` already use the new name and will not work until the rename.
   Settings → General → Repository name. Do this before sharing the link: old GitHub Pages URLs do
   not redirect.
6. **Update the repo description and website field** (the "About" box on the repo page) to point to
   `https://2008mt.github.io/efficient-frontier-3d/`.
7. **Check the live site** after the rename: landing page, each plot, the PDF link.
8. **Update the link on the CV.**

## Next step

Item 1: run a script that compares every number in `README.md` with `results/part1.json`,
`part2.json` and `part3.json`, fix any mismatch, then go on to items 2 to 4.

## Headline results (for reference)

- In-sample maximum-Sharpe portfolio: 40.5% NVDA, 54.5% SGLN, 5.1% ARU, 0% VOO; Sharpe 1.60.
- Rolling out-of-sample test (2018 to 2026): maximum Sharpe 0.88 (expected 1.53), equal weight 0.92,
  risk parity 1.10, minimum variance 0.92.
- Portfolio published in July 2025, held to 13 November 2026: +12.6%, Sharpe 0.36. VOO: +20.1%.
- 90% bootstrap interval for the optimal NVDA weight: 21% to 71%.
