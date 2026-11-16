# V6 external transition diagnostic results

These three decoder penalties and their headline scores were already evaluated in V2. New duration/transition diagnostics reuse six consumed matches and fixed out-of-fit predictions; all results are selection-conditioned development evidence. The diagnostic program read no target files or metrics; user-supplied target diagnoses were excluded from this study. No fit, corruption, model, decoder, or release change was made.

Protocol commit: `653df81d882432455d63f0edb6ba3371486401ef`; protocol SHA-256: `8c15af3fb2c633afd3efa4db7f2bdbdf7c0086ed8b18203b8fb9c038f99b0fce`.

Recommendation: **retain context_p10_r0**.

| Candidate | spellF1 | macroF1 | transition@12 | transition@25 | spell delta | macro delta | trans25 delta | gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| context_p10_r0 | 0.4809519 | 0.8686798 | 0.4133264 | 0.5154486 | +0.0000000 | +0.0000000 | +0.0000000 | reference |
| context_p25_r0 | 0.4721337 | 0.8697351 | 0.4131947 | 0.5076051 | -0.0088181 | +0.0010553 | -0.0078435 | False |
| context_p50_r0 | 0.4437200 | 0.8694242 | 0.4083025 | 0.4928354 | -0.0372319 | +0.0007444 | -0.0226133 | False |

## context_p10_r0

Gate criteria: `{"clean_gain_positive": false, "macro_no_drop": true, "spell_gain_ge_02": false, "transition25_improves": false, "worst_match_ge_minus_05": true}`. Clean spell delta +0.0000000.
Match mean spell deltas: `{"J03WN1": 0.0, "J03WOH": 0.0, "J03WOY": 0.0, "J03WPY": 0.0, "J03WQQ": 0.0, "J03WR9": 0.0}`.
Improved/equal/worse matches: 0/6/0. Worst row: J03WN1:original.

| Match | Scenario | spellF1 | macroF1 | T12 P/R/F1 | T25 P/R/F1 | spell count ratio | trans count ratio | spell delta |
|---|---|---:|---:|---|---|---:|---:|---:|
| J03WN1 | original | 0.506030 | 0.885230 | 0.6297/0.4132/0.4990 | 0.7330/0.4810/0.5808 | 0.5920 | 0.6562 | +0.000000 |
| J03WN1 | drop40 | 0.471871 | 0.874696 | 0.5373/0.3686/0.4373 | 0.6771/0.4645/0.5510 | 0.6140 | 0.6860 | +0.000000 |
| J03WN1 | drop70 | 0.336386 | 0.759477 | 0.2928/0.2545/0.2723 | 0.3897/0.3388/0.3625 | 0.6600 | 0.8694 | +0.000000 |
| J03WOY | original | 0.526933 | 0.897003 | 0.6370/0.4550/0.5309 | 0.7358/0.5256/0.6132 | 0.6447 | 0.7143 | +0.000000 |
| J03WOY | drop40 | 0.507652 | 0.886519 | 0.5472/0.3986/0.4612 | 0.6877/0.5009/0.5796 | 0.6623 | 0.7284 | +0.000000 |
| J03WOY | drop70 | 0.359748 | 0.788832 | 0.2611/0.2487/0.2547 | 0.3537/0.3369/0.3451 | 0.7434 | 0.9524 | +0.000000 |
| J03WPY | original | 0.549349 | 0.915160 | 0.6339/0.4496/0.5261 | 0.7186/0.5097/0.5964 | 0.6413 | 0.7093 | +0.000000 |
| J03WPY | drop40 | 0.525535 | 0.905271 | 0.5816/0.4283/0.4933 | 0.6868/0.5058/0.5826 | 0.6651 | 0.7364 | +0.000000 |
| J03WPY | drop70 | 0.344258 | 0.809997 | 0.2397/0.2694/0.2536 | 0.3448/0.3876/0.3650 | 0.8409 | 1.1240 | +0.000000 |
| J03WOH | original | 0.573431 | 0.910521 | 0.5990/0.4582/0.5192 | 0.7188/0.5498/0.6230 | 0.7040 | 0.7649 | +0.000000 |
| J03WOH | drop40 | 0.551367 | 0.898652 | 0.5542/0.4382/0.4894 | 0.6650/0.5259/0.5873 | 0.7289 | 0.7908 | +0.000000 |
| J03WOH | drop70 | 0.383875 | 0.810162 | 0.2326/0.2729/0.2511 | 0.3430/0.4024/0.3703 | 0.9129 | 1.1733 | +0.000000 |
| J03WQQ | original | 0.583768 | 0.917296 | 0.5979/0.4659/0.5237 | 0.7088/0.5522/0.6208 | 0.7207 | 0.7791 | +0.000000 |
| J03WQQ | drop40 | 0.583146 | 0.910789 | 0.5145/0.4277/0.4671 | 0.6570/0.5462/0.5965 | 0.7756 | 0.8313 | +0.000000 |
| J03WQQ | drop70 | 0.390872 | 0.816280 | 0.2467/0.2610/0.2537 | 0.3548/0.3755/0.3649 | 0.8579 | 1.0582 | +0.000000 |
| J03WR9 | original | 0.555484 | 0.916511 | 0.5924/0.4391/0.5044 | 0.7038/0.5217/0.5993 | 0.6757 | 0.7413 | +0.000000 |
| J03WR9 | drop40 | 0.545800 | 0.910438 | 0.5271/0.4022/0.4562 | 0.6610/0.5043/0.5721 | 0.7054 | 0.7630 | +0.000000 |
| J03WR9 | drop70 | 0.361628 | 0.823404 | 0.2374/0.2565/0.2466 | 0.3541/0.3826/0.3678 | 0.8595 | 1.0804 | +0.000000 |

Duration bins below: GT/predicted counts and mean recall across official IoUs; counts are summed across 18 rows (each match appears in three corruption scenarios).

| Duration frames | GT count | Predicted count | mean row recall |
|---|---:|---:|---:|
| 1-25 | 933 | 207 | 0.040838 |
| 26-50 | 1275 | 464 | 0.121900 |
| 51-125 | 2400 | 1678 | 0.331366 |
| 126+ | 3042 | 3139 | 0.706026 |

## context_p25_r0

Gate criteria: `{"clean_gain_positive": false, "macro_no_drop": true, "spell_gain_ge_02": false, "transition25_improves": false, "worst_match_ge_minus_05": true}`. Clean spell delta -0.0273860.
Match mean spell deltas: `{"J03WN1": -0.015434809756613562, "J03WOH": -0.010499088465031317, "J03WOY": -0.014153442802939417, "J03WPY": -0.01296045835815616, "J03WQQ": 0.00646106624109664, "J03WR9": -0.006322113380780148}`.
Improved/equal/worse matches: 1/0/5. Worst row: J03WOY:original.

| Match | Scenario | spellF1 | macroF1 | T12 P/R/F1 | T25 P/R/F1 | spell count ratio | trans count ratio | spell delta |
|---|---|---:|---:|---|---|---:|---:|---:|
| J03WN1 | original | 0.478203 | 0.882208 | 0.6704/0.3967/0.4984 | 0.7570/0.4479/0.5628 | 0.5140 | 0.5917 | -0.027827 |
| J03WN1 | drop40 | 0.447215 | 0.873581 | 0.5944/0.3488/0.4396 | 0.7239/0.4248/0.5354 | 0.5080 | 0.5868 | -0.024656 |
| J03WN1 | drop70 | 0.342564 | 0.762175 | 0.3274/0.2413/0.2778 | 0.4327/0.3190/0.3673 | 0.5600 | 0.7372 | +0.006179 |
| J03WOY | original | 0.485755 | 0.892977 | 0.6667/0.4268/0.5204 | 0.7466/0.4780/0.5828 | 0.5548 | 0.6402 | -0.041179 |
| J03WOY | drop40 | 0.495688 | 0.887433 | 0.5833/0.3827/0.4622 | 0.7285/0.4780/0.5772 | 0.5768 | 0.6561 | -0.011963 |
| J03WOY | drop70 | 0.370430 | 0.793570 | 0.2805/0.2310/0.2534 | 0.3769/0.3104/0.3404 | 0.6316 | 0.8236 | +0.010682 |
| J03WPY | original | 0.517720 | 0.910809 | 0.6728/0.4225/0.5190 | 0.7531/0.4729/0.5810 | 0.5416 | 0.6279 | -0.031629 |
| J03WPY | drop40 | 0.518003 | 0.905163 | 0.6243/0.4089/0.4941 | 0.7337/0.4806/0.5808 | 0.5701 | 0.6550 | -0.007532 |
| J03WPY | drop70 | 0.344538 | 0.811453 | 0.2460/0.2364/0.2411 | 0.3589/0.3450/0.3518 | 0.6960 | 0.9612 | +0.000280 |
| J03WOH | original | 0.543750 | 0.909355 | 0.6549/0.4422/0.5279 | 0.7611/0.5139/0.6136 | 0.5920 | 0.6753 | -0.029681 |
| J03WOH | drop40 | 0.528834 | 0.900225 | 0.6000/0.4183/0.4930 | 0.7171/0.5000/0.5892 | 0.6219 | 0.6972 | -0.022533 |
| J03WOH | drop70 | 0.404591 | 0.815234 | 0.2653/0.2590/0.2621 | 0.3816/0.3725/0.3770 | 0.7338 | 0.9761 | +0.020716 |
| J03WQQ | original | 0.571689 | 0.916228 | 0.6232/0.4418/0.5170 | 0.7365/0.5221/0.6110 | 0.6384 | 0.7088 | -0.012079 |
| J03WQQ | drop40 | 0.576241 | 0.912158 | 0.5679/0.4116/0.4773 | 0.7175/0.5201/0.6030 | 0.6584 | 0.7249 | -0.006905 |
| J03WQQ | drop70 | 0.429240 | 0.827546 | 0.2864/0.2490/0.2664 | 0.4088/0.3554/0.3802 | 0.7057 | 0.8695 | +0.038367 |
| J03WR9 | original | 0.533562 | 0.915820 | 0.6217/0.4109/0.4948 | 0.7171/0.4739/0.5707 | 0.5784 | 0.6609 | -0.021922 |
| J03WR9 | drop40 | 0.528162 | 0.911232 | 0.5641/0.3826/0.4560 | 0.6923/0.4696/0.5596 | 0.6027 | 0.6783 | -0.017638 |
| J03WR9 | drop70 | 0.382222 | 0.828065 | 0.2488/0.2261/0.2369 | 0.3708/0.3370/0.3531 | 0.7027 | 0.9087 | +0.020594 |

Duration bins below: GT/predicted counts and mean recall across official IoUs; counts are summed across 18 rows (each match appears in three corruption scenarios).

| Duration frames | GT count | Predicted count | mean row recall |
|---|---:|---:|---:|
| 1-25 | 933 | 49 | 0.020411 |
| 26-50 | 1275 | 221 | 0.081259 |
| 51-125 | 2400 | 1293 | 0.274292 |
| 126+ | 3042 | 3076 | 0.690150 |

## context_p50_r0

Gate criteria: `{"clean_gain_positive": false, "macro_no_drop": true, "spell_gain_ge_02": false, "transition25_improves": false, "worst_match_ge_minus_05": false}`. Clean spell delta -0.0672156.
Match mean spell deltas: `{"J03WN1": -0.055831986309163285, "J03WOH": -0.034013719930413765, "J03WOY": -0.03330986082608334, "J03WPY": -0.03181212951376827, "J03WQQ": -0.029737857668714136, "J03WR9": -0.038685868435090566}`.
Improved/equal/worse matches: 0/0/6. Worst row: J03WR9:original.

| Match | Scenario | spellF1 | macroF1 | T12 P/R/F1 | T25 P/R/F1 | spell count ratio | trans count ratio | spell delta |
|---|---|---:|---:|---|---|---:|---:|---:|
| J03WN1 | original | 0.431373 | 0.879332 | 0.6984/0.3636/0.4783 | 0.7683/0.4000/0.5261 | 0.4280 | 0.5207 | -0.074658 |
| J03WN1 | drop40 | 0.408989 | 0.871231 | 0.6390/0.3306/0.4357 | 0.7540/0.3901/0.5142 | 0.4240 | 0.5174 | -0.062882 |
| J03WN1 | drop70 | 0.306430 | 0.758428 | 0.3245/0.2033/0.2500 | 0.4274/0.2678/0.3293 | 0.4620 | 0.6264 | -0.029956 |
| J03WOY | original | 0.453846 | 0.891066 | 0.6839/0.3968/0.5022 | 0.7599/0.4409/0.5580 | 0.4825 | 0.5802 | -0.073087 |
| J03WOY | drop40 | 0.470930 | 0.883671 | 0.6088/0.3651/0.4564 | 0.7500/0.4497/0.5623 | 0.5088 | 0.5996 | -0.036721 |
| J03WOY | drop70 | 0.369628 | 0.802206 | 0.3167/0.2240/0.2624 | 0.4239/0.2998/0.3512 | 0.5307 | 0.7072 | +0.009879 |
| J03WPY | original | 0.490032 | 0.910049 | 0.7138/0.4109/0.5215 | 0.7912/0.4554/0.5781 | 0.4774 | 0.5756 | -0.059317 |
| J03WPY | drop40 | 0.472669 | 0.904318 | 0.6667/0.3837/0.4871 | 0.7710/0.4438/0.5633 | 0.4774 | 0.5756 | -0.052866 |
| J03WPY | drop70 | 0.361004 | 0.814916 | 0.2648/0.2248/0.2432 | 0.3813/0.3236/0.3501 | 0.6081 | 0.8488 | +0.016746 |
| J03WOH | original | 0.502341 | 0.906872 | 0.7172/0.4243/0.5332 | 0.7980/0.4721/0.5932 | 0.4876 | 0.5916 | -0.071090 |
| J03WOH | drop40 | 0.504290 | 0.902055 | 0.6601/0.3984/0.4969 | 0.7789/0.4701/0.5863 | 0.5075 | 0.6036 | -0.047076 |
| J03WOH | drop70 | 0.400000 | 0.822586 | 0.2935/0.2351/0.2611 | 0.4179/0.3347/0.3717 | 0.5995 | 0.8008 | +0.016125 |
| J03WQQ | original | 0.535256 | 0.914355 | 0.6687/0.4297/0.5232 | 0.7656/0.4920/0.5990 | 0.5561 | 0.6426 | -0.048512 |
| J03WQQ | drop40 | 0.520130 | 0.909409 | 0.6026/0.3775/0.4642 | 0.7596/0.4759/0.5852 | 0.5362 | 0.6265 | -0.063016 |
| J03WQQ | drop70 | 0.413187 | 0.826971 | 0.3118/0.2329/0.2667 | 0.4355/0.3253/0.3724 | 0.5885 | 0.7470 | +0.022314 |
| J03WR9 | original | 0.478853 | 0.909700 | 0.6475/0.3913/0.4878 | 0.7266/0.4391/0.5474 | 0.5081 | 0.6043 | -0.076631 |
| J03WR9 | drop40 | 0.482143 | 0.909305 | 0.5950/0.3609/0.4493 | 0.7168/0.4348/0.5413 | 0.5135 | 0.6065 | -0.063657 |
| J03WR9 | drop70 | 0.385859 | 0.833165 | 0.2603/0.2065/0.2303 | 0.3863/0.3065/0.3418 | 0.6054 | 0.7935 | +0.024231 |

Duration bins below: GT/predicted counts and mean recall across official IoUs; counts are summed across 18 rows (each match appears in three corruption scenarios).

| Duration frames | GT count | Predicted count | mean row recall |
|---|---:|---:|---:|
| 1-25 | 933 | 8 | 0.007220 |
| 26-50 | 1275 | 77 | 0.042191 |
| 51-125 | 2400 | 867 | 0.210254 |
| 126+ | 3042 | 2974 | 0.653017 |

Machine-readable `v6-results.json` contains all 54 rows, per-class F1, per-row duration-bin counts/recalls, transition counts/latencies, scenario summaries, all paired deltas and input/source fingerprints. New transition matching is explicitly restricted within each GT-valid run; headline metrics use the unchanged official scorer. No hidden-score, independent-validation or target-improvement claim follows.
