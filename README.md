# Automated Software Testing
## Part 1: Automated Bug Detection in Database Engines

### Building the Docker image
```
docker build -t sqlite-fuzzer .
```

### Running the container
```
docker run -it sqlite-fuzzer
```

### Available commands
```
/usr/bin/test-db fuzz -queries <n> #runs the fuzzer until n queries have been generated
/usr/bin/test-db test --file <path/to/query.sql> #differentially tests one query (useful for bug reproduction)

```

