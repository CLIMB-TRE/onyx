# Server Control

Start the server:

```
$ ./scripts/start.sh
```

Stop the server:

```
$ ./scripts/stop.sh
```

View access logs:

```
$ tail -f access.log
```

View error logs:

```
$ tail -f error.log
```

## With Docker-compose

Create containers and start Onyx:

```
$ docker compose up -d
```

Destroy containers and stop Onyx:

```
$ docker compose down
```

View access logs:

```
$ tail -f logs/wsgi/access.log
```

View error logs:

```
$ tail -f logs/wsgi/error.log
```
