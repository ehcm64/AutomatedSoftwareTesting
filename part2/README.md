# Automated Software Testing
## Part 2: Automated Reduction of Bug-Triggering SQL Queries

### Building the Docker image
```
docker build -t sql-reducer .
```

### Running the container
```
docker run -it sql-reducer
```

### Available commands
```
reducer --query <path/to/query.sql> --test <path/to/oracle.sh>
```
