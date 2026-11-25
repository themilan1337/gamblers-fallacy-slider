# How much has the learner already seen? An experience slider for the gambler's fallacy

An interactive page and a tested implementation of the model in Kevin Dorst, ["Bayesians Commit the Gambler's Fallacy"](https://doi.org/10.1111/cogs.70171), *Cognitive Science* 50(1), e70171 (2026). The page's main slider is how many outcomes the learner has already seen.

Built by Milan Gorislavets and Kamilya Mukh, who answer for any mistakes. This is an independent implementation, not written or endorsed by the paper's author.

- The page: https://themilan1337.github.io/gamblers-fallacy-slider/ (GitHub Pages, the files in `docs/`). An earlier copy of the same files is at https://gamblers-fallacy-page.gorislavetsmilan123.workers.dev/.
- A short post about what the slider shows: [POST.md](POST.md)
- A one-page explainer: [explainer/explainer.pdf](explainer/explainer.pdf)

## What the slider shows

A learner knows a process has a 50% hit rate, such as a coin. It does not know whether the process is Steady (each outcome independent), Switchy (a streak makes a switch more likely) or Sticky (a streak makes a continuation more likely). It starts equally unsure about the three and updates by Bayes' rule on everything it has seen. The data really do come from a fair coin, so Sticky is ruled out faster than Switchy, and on average the learner leans Switchy. After a short streak it expects a switch. A long streak is evidence for Sticky, so after enough repeats it expects a continuation.

The slider sets how many fair-coin outcomes the learner has seen before the streak. With less experience, the point where the average learner starts expecting a continuation comes sooner and the expectation is stronger. These are the numbers the page itself shows at three amounts of experience (1000 simulated learners, fixed seed; `results/live_page_numbers.csv`):

| Outcomes seen | First streak where the average learner expects a continuation | Chance of a continuation after 8 in a row |
|---|---|---|
| 10 | 3 | 85.3% |
| 40 | 5 | 60.6% |
| 100 | 6 | 50.5% |

The page also lets you change the prior weights on the three processes, the number of steps and the maximum shift of the chains, and shows one worked example with two learners and one simulated coin. All numbers come from simulated learners, not from people.

## What is in this repository

| Part | Where |
|---|---|
| The static page: plain HTML, CSS, JS and SVG, no libraries, no build step | `docs/` |
| Python reference implementation of the model, standard library only, with the paper's section numbers in the comments and the choices the paper leaves open marked `CHOICE` | `src/gfmodel/model.py`, `src/gfmodel/experience.py` |
| A numpy version for large simulations. It shares the chain definition with the reference, so it checks the simulation code, not the chain | `src/gfmodel/vectorized.py` |
| JavaScript port of the reference, and a cross-check of the two on 50 parameter cases | `docs/model.js`, `tests/js_runner.cjs`, `src/gfmodel/crosscheck.py` |
| Comparison with the numbers and curves printed in the paper | `src/gfmodel/reproduce.py`, `scripts/reproduce_paper.py`, `results/reproduction.csv` |
| Figures and CSVs behind the tables above | `scripts/make_figures.py`, `results/` |
| Explainer (source and PDF) and the post | `explainer/`, `POST.md` |
| Sources, with how each was verified | `SOURCES.md` |

## How to run

```bash
uv sync                                              # Python 3.12; uv.lock pins the dependencies
uv run ruff check . && uv run ruff format --check .
uv run pytest                                        # needs Node 22+ for the cross-check and a local Chrome or Chromium for the page tests
uv run python scripts/reproduce_paper.py             # writes results/reproduction.csv
uv run python scripts/make_figures.py                # writes results/fig_*.png and experience_curves.csv
uv run python scripts/crosscheck_report.py           # writes results/crosscheck_report.json
python3 -m http.server -d docs 8000                  # then open http://localhost:8000/
```

Opening `docs/index.html` directly also works. Tests never use the network. For the page tests, set `GF_CHROMIUM` to a Chrome or Chromium binary, or run `uv run playwright install chromium` once. `GF_REQUIRE_BROWSER=1 uv run pytest` fails instead of skipping when no browser is found.

The page is served by GitHub Pages from the `main` branch, folder `/docs` (Settings, Pages). `docs/_headers` (a `noindex` header for Cloudflare hosting) has no effect there.

## Results

Every number comes from the command shown.

1. **The model reproduces what the paper prints.** `uv run python scripts/reproduce_paper.py` compares 32 numbers (`results/reproduction.csv`) with tolerances fixed before the comparison: 0.01 for numbers printed with two decimals or as whole percents, 0.02 for values read by eye from a figure, 0.05 for one informational row. Three results sit near the edge of that tolerance: Section 4's 17% (16.2% here), the 5.13 expected switches (5.119 here, outside the paper's own confidence interval by 0.005), and the Section 5.3 percentages (the paper used specific sequences we do not have, so we averaged over all sequences with the same number of switches). The paper's "already around 95%" for Steady after 150 outcomes is 98.7% here, which agrees with the paper's own Fig. 4. Figures: `results/fig_reproduction_fig4.png`, `results/fig_reproduction_fig6.png`.
2. **Less experience shifts the expectation sooner and more strongly.** `uv run python scripts/make_figures.py` (200,000 learners per curve) gives `results/experience_curves.csv` and `results/fig_experience_effect.png`. The depth of the dip below 50% is not monotone in experience: it is deepest around 25 outcomes, because a learner with no experience has no lean toward Switchy yet.
3. **Python and JavaScript agree.** `uv run python scripts/crosscheck_report.py` compares 4044 numbers over 50 cases; the largest absolute difference is 5e-14 (`results/crosscheck_report.json`).
4. **The page works.** `tests/test_page.py` loads the page in Chromium: no console errors, keyboard use of the slider, no horizontal scroll at 375 px, labelled inputs, and the table equals the Python reference to 0.06 percentage points. Screenshots: `results/page_375px.png`, `results/page_desktop_top.png`.

## Limitations

- Experience means outcomes seen and remembered perfectly. The paper's limited-memory ("unpacking") model is not implemented, and neither is working memory; Dorst's reply to us said the model runs on length of past experience.
- The paper does not say how a sequence starts or how a streak is shown. The choices we made are marked `CHOICE` in `src/gfmodel/model.py`: the first outcome has probability 0.5 under every hypothesis, and a streak is shown as one miss followed by s hits.
- The page uses 1000 learners and a fixed seed, so its numbers differ slightly from the large run (85.3% against 85.1% at 10 outcomes, for example).
- The reproduction compares numbers printed in the paper; it does not check them against human data.
- The figure PNGs in `results/` draw Sticky in an older green; the page uses a darker one for contrast.

## License

MIT, see [LICENSE](LICENSE). The paper itself is open access (CC BY); nothing from it or from the author's materials is copied here.

## Sources

[SOURCES.md](SOURCES.md).
