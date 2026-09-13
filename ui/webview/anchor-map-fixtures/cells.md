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

## Handlers

Code lines below, for the code section.

```python
total = 1
def handler(request):
	return respond(request)
total = 1
```

A repeated line and a tab-indented line above.

- A list item holding a fence:

  ```sh
  npm run build
  ```

  after the item's fence

> A quote holding a fence:
>
> ```
> quoted = 1
> second = 2
> ```

    indented = 3
    next = 4

An indented code block above.

  ```js
  compensated = 5
    deeper = 6
  ```

  ~~~
  tilde = 7
  ~~~

A backtick fence with an indented opener and a tilde fence with one.

```
```

An empty fence above.

```zig
const unknown = 8;
```

A fence in a language the highlighter does not know, then a linked address in a code line.

```
url = "https://notes-api.test/handlers"
```

Last of all, an unclosed fence:

```
open = 9
