# My Achieve Your achieve (MAYA)

## Documentation

[github](sites/demo/docs)

[website and demo](https://demo.openaws.dk/)

To preview the GitHub Pages documentation locally:

```sh
uv run --locked --only-group docs mkdocs serve
```

To build the documentation:

```sh
uv run --locked --only-group docs mkdocs build
```

Documentation dependencies are managed in the `docs` group in `pyproject.toml`
and pinned in `uv.lock`.
