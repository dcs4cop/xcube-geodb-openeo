# xcube-geodb-openeo deployment

This document is intended to show all necessary steps to deploy the geoDB-
openEO server to the BC K8s stage cluster.

There is quite a large number of actors which have to be correctly configured
for the service to work:
- a GitHub action inside this repository
- a Dockerfile inside this repository
- a Helm chart, residing within the bc-org k8s-configs repository
- BC's internet provider IONOS
- the bc-org k8s-namespaces repository
- ArgoCD

### GitHub action

A GitHub action has been set up at `.github/workflows/workflow.yaml`
This workflow:
- runs the unit-level tests
- builds a docker image using the steps
    1) check out (of xcube-geodb-openeo)
    2) get tag of release or branch to set it to the docker image
    3) retrieve the version of geoDB-openEO
    4) deployment phase (dev/stage/prod/ignore), to determine if docker image
       actually shall be built
    5) Build docker image
        - name: `bcdev/xcube-geodb-openeo-server`, tag: fetched in previous
          step 2
- Uploads docker image to [quay.io](https://quay.io/repository/bcdev/xcube-geodb-openeo-server)
    - uses
        - `secrets.QUAY_REG_USERNAME`
        - `secrets.QUAY_REG_PASSWORD`
- can be configured with the following variables:
  - `SKIP_UNITTESTS:` "0" or "1"; if set to "1", unit tests are skipped
  - `FORCE_DOCKER_BUILD`: "1"; if set to "1", a docker image will be built and 
    uploaded to quay.io, regardless of the tag or release
- The GH action does no change on the helm chart. This may be added later.

### Dockerfile

The Dockerfile is based on miniconda. It
1) activates the base environment
2) clones the xcube-GitHub repository
3) checks out the branch that contains the server
4) and installs it into the base environment
5) then installs the current repository, i.e. xcube-geodb-openeo, into the base
   environment

In its `CMD` call, it passes the file `/etc/config/config.yml` to the starting
server.

### Helm chart

The helm chart for the xcube-geodb-openeo-server is located in [k8s-configs](https://github.com/bc-org/k8s-configs/tree/main/xcube-geodb-openeo/helm).
It consists of:
1) templates for
    - config-map (`api-config-map.yaml`), where the config is specified, and 
      configured to reside in a file `config.yml`
    - deployment (`api-deployment.yaml`), where the container is defined
      (i.e. the docker image), credentials are put into the environment, and
      the config map is written into a file at `/etc/config`
    - ingress (`api-ingress.yaml`), where the exposure to the public internet
      is configured
    - service (`api-service.yaml`), where port and protocol are configured
2) a values file used to fill in the templates. Currently in use:
   `values-dev.yaml`.
   In this file, the following values are set:
    - the actual Docker image value
    - the ingress encryption method
    - the host name

### IONOS

Needed to add a CNAME, so the server can be reached on a human-readable URL.
This has been done using these
[directions](https://github.com/bc-org/k8s-configs/blob/main/howtos/How_to_add_new_CNAME_record.md).

### k8s-namespaces

Used to store secrets securely in a deployment, instead of putting them
insecurely into the config map. Usage: every time the values change in
[values-xcube-geodb.yaml](https://github.com/bc-org/k8s-namespaces/blob/main/helm/namespaces/values-xcube-geodb.yaml),
run the [workflow](https://github.com/bc-org/k8s-namespaces/actions/workflows/create-xcube-geodb-namespaces-workflow.yaml)
manually. Then, the namespace on the K8s cluster on AWS is updated.

The values inside that file will change if a secret is added, changed or
removed. Currently, these are the secret credentials for the geodb-access.

The workflow is defined [here](https://github.com/bc-org/k8s-namespaces/blob/main/.github/workflows/create-xcube-geodb-namespaces-workflow.yaml).
Note that there are different ones on the same level; this one is the one used
for xcube-geodb-openeo, because xcube-geodb-openeo uses the xcube-geodb
namespace, as configured in `values-dev.yaml` in k8s-configs.

### ArgoCD-Deployment

The purpose of the argoCD deployment is to take the helm chart and deploy it to
BCs AWS K8s. It can be found [here](https://argocd.management.brockmann-consult.de/applications/geodb-openeo).

The relevant configuration values are:
- Cluster: `xc-dev-v2`
- Namespace: `xc-geodb`
- Using helm chart from
    - `git@github.com:bc-org/k8s-configs.git`
    - path `xcube-geodb-openeo/helm`