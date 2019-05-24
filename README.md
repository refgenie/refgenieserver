# refgenieserver

This folder contains code for an API to provide reference genomes.

## Building container

1. In the same directory as the `Dockerfile`:

```
docker build -t fastapi .
```

## Running container for development:

Mount a directory of files to serve at `/genomes`:

```
docker run --rm -p 80:80 --name fastapi -v $(pwd):/app -v $(pwd)/files:/genomes fastapi refgenieserver -c refgenie.yaml serve
```

## Running container for production:

2. Run the container from the image you just built:

```
docker run --rm -d -p 80:80 -v $GENOMES:/genomes --name fastapi refgenieserver -c refgenie.yaml serve 
```

We use `-d` to detach so it's in background. Terminate container when finished:

```
docker stop fastapi
```


## Interacting with the API web server

Navigate to [http://localhost/](http://localhost/) to see the server in action.

You can see the automatic docs and interactive swagger openAPI interface at [http://localhost/docs](http://localhost/docs). That will also tell you all the endpoints, etc.


## Monitoring for errors

Attach to container to see debug output:

```
docker attach fastapi
```

Grab errors:

```
docker events | grep -oP "(?<=die )[^ ]+"
```

View those error codes:

```
docker logs <error_code>
```

Enter an interactive shell to explore the container contents:

```
docker exec -it fastapi sh
```
