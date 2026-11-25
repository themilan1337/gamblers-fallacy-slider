# Why a learner who has seen less expects streaks to continue sooner

I never expected the gambler's fallacy to have a rational story, which is how I ended up at "Bayesians Commit the Gambler's Fallacy".

Kevin Dorst's paper "Bayesians Commit the Gambler's Fallacy" argues that expecting a switch after a streak can be a reasonable thing to do. A learner who is not sure whether a process is independent starts out unsure between three kinds of process: Steady (every outcome is a fresh 50%), Switchy (a streak makes a switch more likely) and Sticky (a streak makes a continuation more likely). The coin is in fact fair. A fair coin's outcomes rule out Sticky faster than Switchy, so on average the learner ends up leaning Switchy, and after a short streak it expects a switch.

Our page adds one slider to this: how many outcomes the learner has already seen. Think of an adult who has just started a game with a coin flip in it, and another who has played it for years.

What the slider shows, at the paper's default settings and averaged over 1000 simulated learners:

- With 10 outcomes seen, the average learner starts expecting a continuation after a streak of 3, and gives 85.3% to a continuation after 8 in a row.
- With 40 outcomes seen, the first such streak is 5, and the chance is 60.6%.
- With 100 outcomes seen, the first streak is 6, and the chance is 50.5%.

So with less experience, the move from expecting a switch to expecting a continuation comes sooner and is stronger. This is the prediction Professor Dorst described to us in an email: it follows past experience, not working memory.

The page also has a worked example with two learners who watch the same simulated coin. After one miss and five hits in a row, the learner who has seen 10 flips gives 76.1% to a sixth hit, and the learner who has seen 40 flips gives 50.7%.

What this is not: the numbers come from a simulation, not from people. The page does not model working memory, and it does not say how many outcomes any real person has seen. The code reproduces the numbers printed in the paper within the tolerances listed in the README.

Milan built the page and the code, and I wrote the explainer. Any mistakes are ours.

Page: https://themilan1337.github.io/gamblers-fallacy-slider/ · Code, tests and explainer: this repository.
