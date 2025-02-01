# GitHub Deploy Key Operator

A Kubernetes operator that automatically manages GitHub Deploy Keys for your repositories. This operator creates, rotates, and maintains SSH deploy keys for GitHub repositories, making it easier to manage secure repository access in your Kubernetes cluster.

## Features

- 🔑 Automatic SSH key generation and rotation
- 🔒 Secure storage of private keys in Kubernetes secrets
- 🔄 Periodic reconciliation to ensure keys exist and are valid
- 📝 Read-only deploy keys by default
- 🎯 Kubernetes-native custom resource definition
- 🗑️ Automatic cleanup of old keys

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

For Helm-only installation, see the [chart documentation](charts/github-deploy-key-operator/README.md).

## Usage

1. Create a GitHubDeployKey resource:

```yaml
apiVersion: github.com/v1alpha1
kind: GitHubDeployKey
metadata:
  name: my-repo-deploy-key
  namespace: flux-system
spec:
  repository: "owner/repository"  # Your GitHub repository
  title: "Kubernetes-managed deploy key"
  readOnly: true  # Recommended for security
```

The operator will:
- Generate a new SSH key pair
- Add the public key to your GitHub repository
- Store the private key in a Kubernetes secret
- Monitor and maintain the key's existence

## Configuration

The operator requires:
- A GitHub token with repository access permissions
- The token secret must be in the same namespace as the operator
- RBAC permissions to manage secrets and custom resources

## Security

- Private keys are stored only in Kubernetes secrets
- Deploy keys are created as read-only by default
- SSH keys use RSA 4096-bit encryption
- Automatic key rotation on CRD updates
- No sensitive information is stored in the operator itself

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
