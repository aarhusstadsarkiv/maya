# My Achieve Your Achieve (MAYA)

`maya` is used to make web clients 
that can interact with aarhus stadsarkivs API service. Aarhus stadsarkiv
contains a lot of public archives and the API service is used to search
and retrieve data from the archives.

The following describes how to install and use `maya`.

## development

    git clone git@github.com:aarhusstadsarkiv/maya.git maya
    cd maya
    uv venv # Python >= 3.10.6 should work
    source .venv/bin/activate

Install requirements:

Using pip

    uv pip install -r pyproject.toml

You may also need to install danish language packs

    sudo apt-get install language-pack-da
    sudo locale-gen da_DK.UTF-8

### Run for development

Install `maya` and make the code "editable":

    uv pip install -e .

Show all commands: 

    maya

Run dev server with a config dir `sites/aarhus`: 

    maya server-dev sites/aarhus

In order to perform api-calls you will need a valid `API_KEY` which you can get from aarhus stadsarkiv.

Create a folder that can be named e.g. `maya_base`. Inside the `maya_base` folder add a `.env` file with the following content:

    API_KEY=your-api-key

Then you can run the server with the following command:

    maya server-dev maya_base

You may also just export the `API_KEY`:

    export API_KEY=your-api-key
    maya server-dev maya_base

### Fix code

Run black, mypy and flake8:

    maya source-fix

### Run tests

Before running the tests you must first export a valid `API_KEY`:

    export API_KEY=your-api-key

Then:

    maya source-test

### Tag a release

Install `bump-py-version`:

    pipx install git+https://github.com/diversen/bump-py-version@v2.0.3

Bump version:

    bump-py-version v1.2.3 # or any other version

## Install using pipx

Install main branch: 
    
    pipx install git+https://github.com/aarhusstadsarkiv/maya.git

Install latest version: 
<!-- LATEST-VERSION-PIPX -->
	pipx install git+https://github.com/aarhusstadsarkiv/maya@v1.3.834

Usage is the same as for development.
