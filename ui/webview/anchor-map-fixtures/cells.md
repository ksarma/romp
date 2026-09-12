# Budgets

The notes-api routes and their budgets, for the review.

| Route | p95 |
|-------|-----|
| GET /notes | 120 ms |
| POST /notes | 180 ms |

Every route above returns JSON.

| Method | Path | Budget |
|:-------|:----:|-------:|
| GET | /notes/{id} | 90 ms |
| DELETE | /notes/{id} | 90 ms |

The two identical budgets are the second table's.

| Filter | Example |
|--------|---------|
| by tag | `tag=a\|b` and `\|` alone |
| by owner | **web** session, see [the guide](https://notes-api.test/guide) |

Markup inside a cell.

| Symbol | Note |
|--------|------|
| count $xy$ here | the count[^1] |
| plain | a note |

Holes inside cells.

| Short | Row |
|-------|-----|
| padded |
| long | row | extra tail |

A padded and a truncated row.

- A list item holding a table:

  | Item | Qty |
  |------|-----|
  | pen | 2 |

  after the item's table

> A quote holding a table:
>
> | Quoted | Cell |
> |--------|------|
> | qbody | qtail |

<div align="center">

| Wrapped | Table |
|---------|-------|
| in a div | wrapper |

</div>

After the wrapper.

| Entity | Beside |
|--------|--------|
| Fast &amp; simple | maps fine |
| ![logo](logo.png) picture | also maps |

Last paragraph here.

[^1]: The footnote definition.
