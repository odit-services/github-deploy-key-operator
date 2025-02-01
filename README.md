# GitHub Deploy Key Operator

🔑 Automatically manage GitHub Deploy Keys in your Kubernetes cluster

## Why?

Managing deploy keys across multiple repositories is a common challenge in GitOps:
- Manual key creation is error-prone
- Key rotation is often forgotten
- Tracking which keys belong to which clusters is difficult

This operator automates these tasks by:
1. Creating and rotating SSH keys automatically
2. Storing keys securely in Kubernetes secrets
3. Managing keys through Kubernetes resources

```
┌──────────────┐         ┌──────────────┐
│              │   1️⃣    │              │
│  GitHubKey   │────────▶│   Operator   │
│     CRD      │         │              │
│              │         │              │
└──────────────┘         └───────┬──────┘
                                 │
                                 │ 2️⃣
                                 ▼
                         ┌──────────────┐
                         │   Generate   │
                         │ SSH keypair  │
                         └───────┬──────┘
                                 │
                         3️⃣      │
               ┌─────────────────┴─────────────┐
               │                               │
               ▼                               ▼
     ┌──────────────┐                 ┌──────────────┐
     │   GitHub     │                 │  Kubernetes  │
     │ Deploy Key   │                 │   Secret     │
     │  (public)    │                 │  (private)   │
     └──────────────┘                 └──────────────┘
```

## Quick Start (5 minutes)

```bash
# 1. Add the Helm repository
flux create source helm github-deploy-key-operator \
  --url=oci://ghcr.io/gurghet/github-deploy-key-operator \
  --namespace=flux-system

# 2. Create GitHub token secret
kubectl create secret generic github-token \
  --namespace=flux-system \
  --from-literal=GITHUB_TOKEN=your_github_token

# 3. Install the operator
flux create helmrelease github-deploy-key-operator \
  --namespace=flux-system \
  --source=HelmRepository/github-deploy-key-operator \
  --chart=github-deploy-key-operator \
  --values='{"github":{"existingSecret":"github-token","existingSecretKey":"GITHUB_TOKEN"}}'
```

## Usage

Create a GitHubDeployKey resource:

```yaml
apiVersion: github.com/v1alpha1
kind: GitHubDeployKey
metadata:
  name: my-repo-key
  namespace: flux-system
spec:
  repository: "owner/repository"
  title: "Kubernetes-managed deploy key"
  readOnly: true  # Recommended for security
```

The operator will:
- Generate a new SSH key pair
- Add the public key to your GitHub repository
- Store the private key in a Kubernetes secret
- Monitor and maintain the key's existence

## Security

- Private keys are stored only in Kubernetes secrets
- Deploy keys are read-only by default
- SSH keys use RSA 4096-bit encryption
- Automatic key rotation on CRD updates
- GitHub token needs only repo deploy key permissions

## Troubleshooting

Common issues:
1. **Key creation fails**: Check GitHub token permissions
2. **Pod fails to start**: Verify secret exists and is readable
3. **Key rotation fails**: Ensure old key exists in GitHub

For detailed configuration and advanced usage, see our [Helm chart documentation](charts/github-deploy-key-operator/values.yaml).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

Apache License 2.0
