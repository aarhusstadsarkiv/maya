# Test

Set an API key:

    export API_KEY=your-api-key

## Run all tests

    maya source-test

## Run a specific test

Set a config directory to use for your tests:
    
    export BASE_DIR=sites/aarhus

Run the test:

    python -m unittest tests/config-aarhus/html_test.py

## Run tests when .env site in sites/*

If a API_KEY is set in a .env file in e.g. `sites/some-test-site` folder, it will be used automatically when running tests for that site.

So the API_KEY needs to be correct if API_KEY is set. 
