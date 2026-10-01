| Model | Scen. | Weak-3 P / R / F1 | Slot F1 | Rel. F1 | Actions / gold |
|---|---|---|---|---|---|
| sonnet-5 | MUM-T | 0.00 / 0.00 / 0.00 | 0.66 | 0.45 | 25.0 / 14 |
| sonnet-5 | NGHE | 0.83 / 0.16 / 0.26 | 0.63 | 0.37 | 32.3 / 18 |
| sonnet-5 | AV | 0.61 / 0.13 / 0.20 | 0.77 | 0.56 | 17.3 / 16 |
| opus-5-5 | MUM-T | 0.42 / 0.29 / 0.34 | 0.67 | 0.43 | 27.0 / 14 |
| opus-5-5 | NGHE | 0.17 / 0.16 / 0.16 | 0.62 | 0.41 | 35.3 / 18 |
| opus-5-5 | AV | 0.80 / 0.71 / 0.74 | 0.86 | 0.70 | 18.7 / 16 |
| *Repository prompt* | | | | | |
| sonnet-5 | all | 0.48 / 0.10 / 0.16 | 0.68 | 0.46 | |
| opus-5-5 | all | 0.47 / 0.39 / 0.42 | 0.71 | 0.51 | |
| *Corrected contract* | | | | | |
| sonnet-5 | all | 0.38 / 0.42 / 0.39 | 0.68 | 0.46 | |
| opus-5-5 | all | 0.36 / 0.58 / 0.43 | 0.69 | 0.48 | |

repository claude-sonnet-5: runs without control 9/9, without flow 8; NGHE flows predicted [0, 0, 0] aligned [0, 0, 0]
repository claude-opus-5-5: runs without control 2/9, without flow 0; NGHE flows predicted [5, 12, 12] aligned [0, 0, 1]
bench-corr claude-sonnet-5: runs without control 5/18, without flow 0; NGHE flows predicted [15, 9, 16, 21, 6, 17] aligned [0, 0, 0, 0, 0, 0]
bench-corr claude-opus-5-5: runs without control 3/18, without flow 0; NGHE flows predicted [32, 28, 26, 34, 27, 25] aligned [3, 1, 1, 2, 1, 2]
corrected - repository: mean dS +0.056, positive 3/6
