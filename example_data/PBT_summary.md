# Model Adequacy Evaluation Summary


## Mean Difference (Entropy)

**Best-fit model according to Mean Difference (entropy):** `EXM-C10Ffix-R3-PMSF`

List of models sorted by |original − simulated| for entropy:

| Model | Entropy original data | Average entropy simulated data | SD simulated | Z-score | abs(Diff) |
|-----|---------------------|------------------------------|------------|-------|---------|
| EXM-C10Ffix-R3-PMSF | 0.271698 | 0.267099 | 0.014069 | -0.327 | 0.004599 |
| EXM-C10Fopt-R3-PMSF | 0.271698 | 0.281616 | 0.015429 | 0.643 | 0.009918 |
| EXM-C10Ffix-R3 | 0.271698 | 0.288890 | 0.015412 | 1.116 | 0.017192 |
| LG-C10opt-R3-PMSF | 0.271698 | 0.289648 | 0.016128 | 1.113 | 0.017950 |
| LG-C10fix-R3-PMSF | 0.271698 | 0.291069 | 0.013955 | 1.388 | 0.019371 |
| LG-C10fix-R3 | 0.271698 | 0.302973 | 0.015304 | 2.044 | 0.031275 |
| LG-C10opt-R3 | 0.271698 | 0.304256 | 0.015836 | 2.056 | 0.032558 |
| EXM-C10Fopt-R3 | 0.271698 | 0.306948 | 0.016990 | 2.075 | 0.035251 |

![Entropy ridge plot](mean_entropy.png)


## Mean Difference (Diversity)

**Best-fit model according to Mean Difference (diversity):** `EXM-C10Ffix-R3-PMSF`

List of models sorted by |original − simulated| for diversity:

| Model | Diversity original data | Average diversity simulated data | SD simulated | Z-score | abs(Diff) |
|-----|-----------------------|--------------------------------|------------|-------|---------|
| EXM-C10Ffix-R3-PMSF | 1.570780 | 1.624345 | 0.033552 | 1.596 | 0.053565 |
| EXM-C10Ffix-R3 | 1.570780 | 1.625299 | 0.033437 | 1.631 | 0.054519 |
| EXM-C10Fopt-R3-PMSF | 1.570780 | 1.659114 | 0.035321 | 2.501 | 0.088335 |
| LG-C10opt-R3-PMSF | 1.570780 | 1.661257 | 0.038166 | 2.371 | 0.090477 |
| LG-C10fix-R3 | 1.570780 | 1.661908 | 0.035652 | 2.556 | 0.091128 |
| LG-C10fix-R3-PMSF | 1.570780 | 1.666041 | 0.033184 | 2.871 | 0.095261 |
| LG-C10opt-R3 | 1.570780 | 1.667434 | 0.035533 | 2.720 | 0.096654 |
| EXM-C10Fopt-R3 | 1.570780 | 1.704141 | 0.038912 | 3.427 | 0.133361 |

![Diversity ridge plot](mean_diversity.png)


## Cramer-von Mises Test On Sitewise Entropy

**Best-fit model:** `EXM-C10Ffix-R3`

List of models sorted by W² statistic`:

| Model | W2_statistic |
|-----|------------|
| EXM-C10Ffix-R3 | 0.096827 |
| LG-C10opt-R3 | 0.134593 |
| LG-C10fix-R3 | 0.140210 |
| EXM-C10Fopt-R3 | 0.144356 |
| EXM-C10Fopt-R3-PMSF | 0.227008 |
| LG-C10opt-R3-PMSF | 0.241592 |
| LG-C10fix-R3-PMSF | 0.242645 |
| EXM-C10Ffix-R3-PMSF | 0.269618 |

![CVM entropy ridge plot](cvm_entropy.png)


## Cramer-von Mises Test On Sitewise Diversity

**Best-fit model:** `EXM-C10Ffix-R3`

List of models sorted by W² statistic:

| Model | W2_statistic |
|-----|------------|
| EXM-C10Ffix-R3 | 0.132750 |
| LG-C10fix-R3 | 0.205805 |
| LG-C10opt-R3 | 0.210733 |
| EXM-C10Fopt-R3 | 0.281791 |
| EXM-C10Fopt-R3-PMSF | 0.325861 |
| EXM-C10Ffix-R3-PMSF | 0.339915 |
| LG-C10opt-R3-PMSF | 0.352212 |
| LG-C10fix-R3-PMSF | 0.354241 |

![CVM diversity ridge plot](cvm_diversity.png)

