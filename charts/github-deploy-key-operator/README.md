# GitHub Deploy Key Operator Helm Chart

This Helm chart installs the GitHub Deploy Key Operator in your Kubernetes cluster.

## Prerequisites

- Kubernetes 1.16+
- Helm 3.0+
- A GitHub token with appropriate permissions

## Installation

### Add the Helm Repository

```bash
helm repo add github-deploy-key-operator https://gurghet.github.io/github-deploy-key-operator
helm repo update
```

### Install the Chart

1. Using a new GitHub token:

```bash
helm install github-deploy-key-operator github-deploy-key-operator/github-deploy-key-operator \
  --set github.token=<your-github-token>
```

2. Using an existing secret:

```bash
helm install github-deploy-key-operator github-deploy-key-operator/github-deploy-key-operator \
  --set github.existingSecret=my-github-secret \
  --set github.existingSecretKey=GITHUB_TOKEN
```

## Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of operator replicas | `1` |
| `image.repository` | Image repository | `ghcr.io/gurghet/github-deploy-key-operator` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `Always` |
| `github.existingSecret` | Name of existing secret with GitHub token | `""` |
| `github.existingSecretKey` | Key in existing secret for GitHub token | `"GITHUB_TOKEN"` |
| `github.token` | GitHub token (if not using existing secret) | `""` |
| `serviceAccount.create` | Create service account | `true` |
| `serviceAccount.name` | Service account name | `""` |
| `podSecurityContext` | Pod security context | See values.yaml |
| `securityContext` | Container security context | See values.yaml |
| `resources` | Pod resource requests/limits | `{}` |
| `nodeSelector` | Node selector | `{}` |
| `tolerations` | Pod tolerations | `[]` |
| `affinity` | Pod affinity | `{}` |

## Usage with Flux

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: github-deploy-key-operator
  namespace: flux-system
spec:
  interval: 5m
  chart:
    spec:
      chart: github-deploy-key-operator
      version: "0.1.0"  # Use specific version
      sourceRef:
        kind: HelmRepository
        name: github-deploy-key-operator
        namespace: flux-system
  values:
    github:
      existingSecret: github-token
      existingSecretKey: GITHUB_TOKEN
```

## License

This chart is available under the same license as the GitHub Deploy Key Operator.
