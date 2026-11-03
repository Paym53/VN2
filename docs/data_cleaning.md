# Data cleaning (phase 1)

All numbers use the history only: 599 rows x 157 weeks, 2021-04-12 to 2024-04-08.

## What the data shows

| Cell type (sales x in-stock flag) | Cells | Share |
|---|---|---|
| In stock, sales > 0 | 53,429 | 56.8 % |
| In stock, sales = 0 | 30,097 | 32.0 % |
| Out of stock, sales > 0 | 0 | 0.0 % |
| Out of stock, sales = 0 | 10,517 | 11.2 % |

- No missing, negative or fractional sales.
- **An out-of-stock week never has a sale.** The flag marks weeks with no stock at all.
  A week that sold out part-way is flagged in stock: that censoring is invisible in the data.
- **Late launches:** 371 rows have weeks before their first sale (7,134 cells, 7.6 %);
  91 % of them are flagged out of stock, 629 cells in 212 rows are flagged in stock.
- After launch, stock-outs fall over time: 8.0 % of weeks in 2021, 6.0 % in 2022, 2.4 % in 2023,
  0.9 % in 2024; none of the 599 rows is out of stock in week 0. 604 of 1,352 stock-out
  episodes last one week; 210 last more than four.
- **No catch-up after a stock-out:** the week after sells 2.17 units on average, below the rows'
  usual 2.51. Nothing to correct.
- Demand is small: median row sells 1.26 units a week when in stock (10 % of rows under 0.71,
  10 % above 5.15). 81 rows have a week above 10x their mean; these are kept (no outlier trimming).

## Rules

1. **Stock-out week -> missing (NaN).** Demand unknown; the forecast skips the week.
2. **Optional: weeks before the first sale -> missing.** Off by default; decided in phase 3.
3. Nothing else.

Code: `vn2/cleaning.py`. Tests: `tests/test_cleaning.py` (scenarios, no look-ahead, real counts).

## Forecast Value Added (`python scripts/cleaning_fva.py`)

The benchmark's seasonal moving average fed with three histories, scored on the same cells
(in-stock weeks only) over every weekly cutoff with 3 weeks of history left after it.

Two years of cutoffs (102):

| History | MAE% lag 1 | Bias% lag 1 | Score% lag 1 | MAE% 3 weeks | Bias% 3 weeks | Score% 3 weeks |
|---|---|---|---|---|---|---|
| A raw sales | 57.9 | -9.7 | 67.6 | 41.7 | -9.1 | 50.8 |
| B stock-outs missing | 58.7 | 0.3 | **59.0** | 42.2 | 0.6 | **42.8** |
| C B + pre-launch missing | 58.8 | 0.8 | 59.6 | 42.1 | 1.0 | 43.1 |

Last year only (50 cutoffs):

| History | MAE% lag 1 | Bias% lag 1 | Score% lag 1 | MAE% 3 weeks | Bias% 3 weeks | Score% 3 weeks |
|---|---|---|---|---|---|---|
| A raw sales | 55.9 | -5.8 | 61.8 | 40.0 | -5.6 | 45.6 |
| B stock-outs missing | 56.5 | 0.4 | 56.9 | 40.3 | 0.4 | 40.7 |
| C B + pre-launch missing | 56.5 | 0.3 | **56.8** | 40.2 | 0.3 | **40.5** |

Reading: treating stock-outs as missing removes a -6 to -10 % bias and improves the Score by
5 to 9 points (MAE rises slightly because forecasts are no longer pulled down by fake zeros).
The pre-launch rule is neutral for a 13-week moving average; t0-gamma reads the whole history,
so phase 3 tests it again.
