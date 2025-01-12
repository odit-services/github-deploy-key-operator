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

1. Apply the CRD and RBAC configurations:
```bash
kubectl apply -f config/deploy/operator.yaml
```

2. Create a GitHub token secret in the `flux-system` namespace:
```bash
kubectl create secret generic ghcr-secret \
  --namespace flux-system \
  --from-literal=github-token=your_github_token
```

3. Deploy the operator:
```bash
kubectl apply -f config/deploy/operator.yaml
```

## Usage

1. Create a GitHubDeployKey resource:

```yaml
apiVersion: github.com/v1alpha1
kind: GitHubDeployKey
metadata:
  name: my-repo-deploy-key
spec:
  repository: "owner/repository"  # Your GitHub repository
  title: "Kubernetes-managed deploy key"
  readOnly: true
```

The operator will:
- Generate a new SSH key pair
- Add the public key to your GitHub repository
- Store the private key in a Kubernetes secret
- Monitor and maintain the key's existence

## Configuration

The operator requires:
- A GitHub token with repo access stored in a secret named `ghcr-secret`
- The token secret must be in the `flux-system` namespace
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

## Acknowledgments

Built with:
- [Kopf](https://github.com/nolar/kopf) - Kubernetes Operator Framework
- [PyGithub](https://github.com/PyGithub/PyGithub) - GitHub API wrapper for Python
- [kubernetes-client](https://github.com/kubernetes-client/python) - Official Kubernetes Python client
