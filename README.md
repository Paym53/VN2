# VN2 inventory competition: data and code

VN2 was an inventory planning competition organized by Nicolas Vandeput (SupChains) in 2025.
Competitors ordered stock for 599 products in the stores of a retail chain, over six weekly rounds.
The lowest cost won. Flieber, Daybreak and SupChains sponsored the competition, and DataSource.ai
hosted it.

Page, results and citation: https://supchains.com/vn2-inventory-competition/

## The scenario

It is Monday 15 April 2024, early in the morning. You are the inventory planner of a retail chain.
Every week, before the stores open, you order stock from the central warehouse. It arrives two
weeks later. You know your stock, the orders on their way, and about three years of weekly sales.

You place six orders, one per week. Each order should keep the shelves stocked without leaving
too much on them.

## The rules

- **Holding cost**: 0.2 € per unit left on the shelf at the end of a week. Goods in transit cost
  nothing. Stock does not expire.
- **Shortage cost**: 1 € per unit of lost sales. There are no backorders: a sale the shelf cannot
  serve is lost.
- **Lead time**: you place order k before week k starts. It is on the shelf at the start of week
  k+2. Order 1 arrives in week 3, order 6 in week 8.
- **Supply**: the warehouse delivers every order in full, always in two weeks.
- **Setup**: weeks 1 and 2 are played with the stock and the orders you start with. No order can
  change them, so they cost 913.8 € to every player.
- **Score**: the cost of weeks 3 to 8. The lowest score wins.

Each round, a week of sales is played and you see it before your next order:

| Round | You know the sales up to | You order before | The order arrives in |
|---|---|---|---|
| 1 | Week 0, 8 April 2024 | Week 1, 15 April | Week 3, 29 April |
| 2 | Week 1, 15 April | Week 2, 22 April | Week 4, 6 May |
| 3 | Week 2, 22 April | Week 3, 29 April | Week 5, 13 May |
| 4 | Week 3, 29 April | Week 4, 6 May | Week 6, 20 May |
| 5 | Week 4, 6 May | Week 5, 13 May | Week 7, 27 May |
| 6 | Week 5, 13 May | Week 6, 20 May | Week 8, 3 June |

Weeks 7 and 8 are played with no new order: an order placed then would arrive after week 8.

The competition ran in 2025. The data came out on 29 September. The six rounds ran from
21 October to 5 November.

## What this folder holds

| File | What it holds |
|---|---|
| `Data/Week 0 - 2024-04-08 - Sales.csv` | Units sold per week, 157 weeks, from 12 April 2021 to 8 April 2024: what you know before round 1 |
| `Data/Week 0 - In Stock.csv` | The in-stock flag of every week, up to 3 June 2024 |
| `Data/Week 0 - Master.csv` | The product and store hierarchy |
| `Data/Week 0 - 2024-04-08 - Initial State.csv` | The stock at the end of week 0 and the orders in transit, the same for every player |
| `Data/Week 0 - Submission Template.csv` | The layout of an order |
| `Data/Week 1 - 2024-04-15 - Sales.csv` to `Data/Week 8 - 2024-06-03 - Sales.csv` | The sales file of each round: each one adds a week |
| `vn2_simulate.py` | The official rules: it plays six orders and prints the score |
| `vn2_play.py` | Replays the six rounds with your ordering policy |
| `vn2_benchmark.py` | The benchmark of the competition, as a policy |

## The data

The sales are real. They come from the stores of an anonymous retail chain. Each row is one
product in one store: 599 rows, 67 stores and 297 products. Two columns identify a row, `Store`
and `Product`. They are anonymized integer codes. Every file lists the same 599 rows in the same
order.

Every other column is one week, labelled with its Monday date (`2024-04-08`). Sales are whole
units. A week's sales are also its demand in the simulation.

The in-stock flag is `True` when some stock was left at the end of the week. It is `False` when
the shelf was empty at the end of the week: the sales of that week may be lower than the demand.
As this is real data, some flags may be wrong.

The master file gives each row its `ProductGroup`, `Division`, `Department` and `DepartmentGroup`,
and the `StoreFormat` and `Format` of its store. They are anonymized codes too.

An order file has the layout of `Week 0 - Submission Template.csv`: the columns `Store` and
`Product`, then one column of orders. It holds 599 rows in the order of the template, whole
numbers, 0 or more.

## How to play

The scripts need Python 3 with pandas and NumPy. Run them from this folder.

Write your policy in a Python file, `my_policy.py`, as one function:

```python
def policy(sales, in_stock, master, state):
    ...
    return orders  # 599 whole numbers, 0 or more, indexed by Store and Product
```

Then replay the competition with it:

    python vn2_play.py my_policy.py

Before each round, `vn2_play.py` gives your policy what the competitors had at that time, and
nothing more: the sales up to the week before, the in-stock flags of the same weeks, the master
file, and your stock and orders in transit at the end of the week before. It checks each order
like the competition did. It plays the eight weeks and prints the cost of each week, the setup,
your score and where it would rank. It writes your six orders in the folder `Orders - my_policy`.

To score six order files you made another way, name them like the competition did,
`Week 1 - 2024-04-15 - Order.csv` to `Week 6 - 2024-05-20 - Order.csv`, put them in one folder
and run:

    python vn2_simulate.py "Orders - my_policy"

Start with the benchmark: `python vn2_play.py vn2_benchmark.py` must print a setup of 913.8 € and
a score of 4,334.0 €.

## The score

    Score = Σ over weeks 3 to 8 of (0.2 € × units left at the end of the week + 1 € × units of lost sales)

The competition played every order with this code, once per week:

```python
state["Start Inventory"] = previous_state["End Inventory"] + previous_state["In Transit W+1"]
state["Sales"] = state["Start Inventory"].clip(upper=demand)
state["Missed Sales"] = demand - state["Sales"]
state["End Inventory"] = state["Start Inventory"] - state["Sales"]
state["In Transit W+1"] = previous_state["In Transit W+2"]
state["In Transit W+2"] = orders
state["Holding Cost"] = state["End Inventory"] * 0.2
state["Shortage Cost"] = state["Missed Sales"] * 1.0
```

## The benchmark

`vn2_benchmark.py` forecasts with a seasonal moving average and orders up to four weeks of
forecast:

1. It sets aside the weeks with a shortage, using the in-stock flag.
2. It computes one seasonal factor per calendar week, from the mean sales of all rows.
3. It forecasts with the mean of the last 13 weeks of deseasonalized sales, reseasonalized.
4. Each order brings the stock on the shelf and in transit up to the forecast of the next four
   weeks.

Over the eight weeks, it costs 5,247.8 €: 913.8 € of setup and a score of 4,334.0 €.

## Results

| Final ranking | Score |
|---|---|
| 1st: Bartosz Szabłowski | 3,763.2 € |
| 2nd: Matias Alvo | 3,764.6 € |
| 3rd: Philip Stubbs and Jakub Figura | 3,791.6 € |
| 4th: Carlo Cavalieri | 3,794.4 € |
| 5th: Ruben van de Geer, Diederik Perdok and Simon Grest | 3,824.4 € |
| Benchmark | 4,334.0 € |

The winner cost 13% less than the benchmark.

## How to cite VN2

The data is free to use. When you use it, please cite the competition:

> Vandeput, N. (2025). VN2 Inventory Planning Challenge. Organized by Nicolas Vandeput
> (SupChains). Sponsored by Flieber, Daybreak and SupChains.
> https://supchains.com/vn2-inventory-competition/

```bibtex
@misc{vandeput2025vn2,
  author       = {Vandeput, Nicolas},
  title        = {{VN2} Inventory Planning Challenge},
  year         = {2025},
  howpublished = {\url{https://supchains.com/vn2-inventory-competition/}},
  note         = {Organized by Nicolas Vandeput (SupChains). Sponsored by Flieber, Daybreak and SupChains.}
}
```

## Learn more

- The winners explain their solutions, webinar: https://www.youtube.com/watch?v=pypzcvwmApA
- My learning points from VN2, the first inventory competition, on Medium: https://nicolas-vandeput.medium.com/my-learning-points-from-vn2-the-first-inventory-competition-a4bffcc92856
