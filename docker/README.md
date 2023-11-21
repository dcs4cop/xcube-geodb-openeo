# Docker builds for the xcube-geoDB-openEO Backend

The backend image is automatically built on push to master, and on release.
The image is built and uploaded to _quay.io_ during the default GitHub workflow
in the step `build-docker-image`.

It can be run locally using docker like so:

```bash
docker run -p 8080:8080 -env-file env.list quay.io/bcdev/xcube-geodb-openeo
```

where `env.list` contains the following values:
```
postgrest_url:  <geoDB-PostGREST server url>
postgrest_port: <geoDB-PostGREST server port>
client_id:      <your client id>
client_secret:  <your client secret>
auth_domain:    <your auth domain>
```

This starts the geoDB-openEO server instance accessible through port 8080, e.g.
at `localhost:8080/processes`