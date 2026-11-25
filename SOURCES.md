# Sources

Every source used, what was taken from it, and how it was verified.

## The paper (primary source for the model)

| Source | Used for | How obtained and verified |
|---|---|---|
| Kevin Dorst (2026), "Bayesians Commit the Gambler's Fallacy", *Cognitive Science* 50(1), e70171. https://doi.org/10.1111/cogs.70171 (full text: https://onlinelibrary.wiley.com/doi/full/10.1111/cogs.70171) | The whole model: hypothesis space (Sections 2-3), the streak chains and their matrices (Section 3, Fig. 2, Fig. 3), the prior and update rule (Section 4), the prediction rule (Section 3.1), the experience simulations (Sections 5.1, 5.2, Fig. 6, Fig. 7), the numbers reproduced in `results/reproduction.csv` (Sections 4, 5.1, 5.3, 5.5), the speed mixture (Section 4, Fig. 4, Section 6.3). | A direct fetch of the Wiley page returned HTTP 403 on 16 Oct 2026; the full text (about 287,000 characters of Markdown) came through a web-fetch service and was read for Sections 1 to 7 and the notes. The text is not committed. Author, title, year, venue, DOI and licence (CC BY) re-checked on OpenAlex work W7125798768 on 19 Nov 2026. |
| Kevin Dorst, comment of 9 Jan 2024 on the LessWrong post of the paper, https://www.greaterwrong.com/posts/oZMNoxWsfsHQyzzB7/bayesians-commit-the-gambler-s-fallacy/comment/KkqYMWnfmj3bQixjA | An independent printed example of the streak-chain matrices (2-step, 60%), used in `tests/test_model.py::test_two_step_matrix_equals_dorst_blog_comment`. | Opened directly: it shows the Switchy and Sticky matrices. |
| Author's email of 14 Oct 2026 to Kamilya Mukh | The statement that the model predicts from length of past experience, not working memory, and that adults with more or less experience are the easier case. | Primary source (our own correspondence); quoted in the README only in short. |

## Other papers named on the page

| Paper | Used for | Verification |
|---|---|---|
| Xiang, Dorst & Gershman (2025), *Psychological Science* 36(6), 451-464, doi:10.1177/09567976251344570 | Named as the source of the IID-sequence findings the paper uses. Not used for any number. | OpenAlex reference lookup: exact DOI match. |
| Asparouhova, Hertzel & Lemmon (2009), *Management Science* 55(11), doi:10.1287/mnsc.1090.1059; Rao & Hastie (2023), *Cognitive Science* 47(1), e13211, doi:10.1111/cogs.13211 | Named as adult studies the paper (Section 5.2) uses to contrast familiar and unfamiliar processes. Not used for any number. | OpenAlex reference lookup: exact title matches. The claim about what they compare is taken from the paper's Section 5.2, not from these two papers, which we did not open. |

`refs.bib` holds the four references. A reference check with `academic-refchecker` on 16 Oct 2026 found all four with correct authors. Two warnings were database artifacts, checked by hand: Semantic Scholar holds the 2024 SSRN preprint of the Dorst paper (DOI 10.2139/ssrn.4683064) under the same title, so the DOI differs from the published one, which the Wiley page and OpenAlex confirm; and it spells the Xiang et al. venue "Psychology Science".

## Hosting and libraries

- GitHub Pages, publishing source: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site (fetched 19 Nov 2026): "Deploy from a branch", then a branch and the `/docs` folder.
- The live page was compared with `docs/` on 19 Nov 2026: `index.html`, `app.js`, `model.js` and `style.css` have identical SHA-256 sums.
- The seeded generator is mulberry32 (public domain), written from memory and not checked against an outside reference. What is checked is that the Python and JavaScript versions give identical streams (`tests/test_crosscheck_js.py`) and that seed 1 starts 0.6270739405881613 (`tests/test_experience.py`, which pins our own output).
- The page uses no libraries, so nothing is loaded from a CDN. numpy and matplotlib (figures, fast simulation), pytest, ruff and playwright==1.56.0 (dev) are pinned in `uv.lock`. The Playwright launch options in `src/gfmodel/browser.py` were checked against the Playwright Python documentation on 18 Oct 2026.
