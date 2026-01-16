# Install

```bash
uv venv .venv-docs
source .venv-docs/bin/activate
uv pip install -r docs/requirements.txt
```

## Usage

```bash
mkdocs serve
```

Edit files. 

## Build

The site is built using github actions. So you just need to push to the main branch and it will be built automatically.