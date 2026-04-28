# Automated Software Testing
## Part 1: Automated Bug Detection in Database Engines

```
docker build -t sqlite-fuzzer .
docker run -it -v "$PWD":/home/test/fuzzer -w /home/test/fuzzer sqlite-fuzzer
```

```
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

```
python3 run.py <args>
```

OR
```
pip install -e . # Creates executable in editable mode (no need to re-run this even after editing code)
test-db <args>
```
