# GitHub Deploy Key Operator Helm Chart

This Helm chart installs the GitHub Deploy Key Operator in your Kubernetes cluster.

## Prerequisites

- Kubernetes 1.16+
- Helm 3.0+ or Flux v2
- A GitHub token with repository access permissions

## Installation

### Using Flux (recommended)

1. Add the Helm repository:
```bash
flux create source helm github-deploy-key-operator \
  --url=oci://ghcr.io/gurghet/github-deploy-key-operator \
  --namespace=flux-system
```

2. Create a GitHub token secret:
```bash
kubectl create secret generic github-token \
  --namespace flux-system \
  --from-literal=GITHUB_TOKEN=your_github_token
```

3. Install the operator:
```bash
flux create helmrelease github-deploy-key-operator \
  --namespace=flux-system \
  --source=HelmRepository/github-deploy-key-operator \
  --chart=github-deploy-key-operator \
  --values='{"github":{"existingSecret":"github-token","existingSecretKey":"GITHUB_TOKEN"}}'
```

### Using Helm directly

1. Add the Helm repository:
```bash
helm registry login ghcr.io
helm pull oci://ghcr.io/gurghet/github-deploy-key-operator/github-deploy-key-operator --version 1.3.1
```

2. Install the chart:
```bash
helm install github-deploy-key-operator github-deploy-key-operator-1.3.1.tgz \
  --namespace flux-system \
  --set github.existingSecret=github-token \
  --set github.existingSecretKey=GITHUB_TOKEN
```

## Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of operator replicas | `1` |
| `image.repository` | Image repository | `ghcr.io/gurghet/github-deploy-key-operator/operator` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `Always` |
| `github.existingSecret` | Name of existing secret with GitHub token | `""` |
| `github.existingSecretKey` | Key in existing secret for GitHub token | `"GITHUB_TOKEN"` |
| `github.token` | GitHub token (if not using existing secret) | `""` |
| `serviceAccount.create` | Create service account | `true` |
| `serviceAccount.name` | Service account name | `""` |
| `podSecurityContext` | Pod security context | See values.yaml |
| `securityContext` | Container security context | See values.yaml |

## Security Considerations

- The GitHub token should have the minimum required permissions (repo access)
- Use `github.existingSecret` instead of `github.token` to avoid exposing the token in Helm values
- The operator runs with restricted security context by default
- All generated SSH keys are stored as Kubernetes secrets
