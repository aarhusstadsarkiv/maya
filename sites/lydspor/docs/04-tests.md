# Test

Set an API key:

    export API_KEY=your-api-key

## Run all tests

    maya source-test

## Run a specific test

Set a config directory to use for your tests,
    
    export BASE_DIR=sites/aarhus

Run the test:

    python -m unittest tests/config-aarhus/html_test.py