import os
import kopf
import kubernetes
import base64
import github
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# Initialize the Kubernetes API client
kubernetes.config.load_incluster_config()
core_v1_api = kubernetes.client.CoreV1Api()

def get_github_token(logger):
    """Retrieve GitHub token from secret."""
    try:
        secret = core_v1_api.read_namespaced_secret(
            name='ghcr-secret',
            namespace='flux-system'
        )
        token = base64.b64decode(secret.data['github-token']).decode()
        logger.info(f"Got GitHub token: {token[:4]}...{token[-4:]}")
        return token
    except kubernetes.client.exceptions.ApiException as e:
        raise kopf.PermanentError(f"Failed to get GitHub token: {e}")

def generate_ssh_key():
    """Generate SSH key pair."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend()
    )
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    )
    
    return private_pem.decode(), public_key.decode()

def get_github_repo(token, repo_name, logger):
    """Get GitHub repository instance."""
    g = github.Github(token)
    repo = g.get_repo(repo_name)
    logger.info(f"Got repository {repo_name}")
    return repo

def manage_existing_keys(repo, title, logger):
    """Delete existing keys with the same title."""
    existing_keys = list(repo.get_keys())
    logger.info(f"Found {len(existing_keys)} existing deploy keys")
    for key in existing_keys:
        if key.title == title:
            logger.info(f"Found existing deploy key with title '{title}' (id: {key.id}), deleting it")
            key.delete()
            logger.info(f"Successfully deleted old deploy key {key.id}")

def create_or_update_secret(name, namespace, secret_data, owner_reference, logger):
    """Create or update Kubernetes secret."""
    # Base64 encode all secret data
    encoded_data = {k: base64.b64encode(v.encode()).decode() for k, v in secret_data.items()}
    
    try:
        # Try to update existing secret
        secret = core_v1_api.read_namespaced_secret(
            name=name,
            namespace=namespace
        )
        secret.data = encoded_data
        core_v1_api.replace_namespaced_secret(
            name=name,
            namespace=namespace,
            body=secret
        )
        logger.info(f"Updated existing secret {name}")
    except kubernetes.client.exceptions.ApiException as e:
        if e.status != 404:  # Only ignore if secret doesn't exist
            raise
        
        core_v1_api.create_namespaced_secret(
            namespace=namespace,
            body=kubernetes.client.V1Secret(
                metadata=kubernetes.client.V1ObjectMeta(
                    name=name,
                    owner_references=[owner_reference]
                ),
                type='Opaque',
                data=encoded_data
            )
        )
        logger.info(f"Created new secret {name}")

@kopf.on.create('github.com', 'v1alpha1', 'githubdeploykeys')
def create_deploy_key(spec, logger, patch, **kwargs):
    try:
        # Get GitHub token and repository
        github_token = get_github_token(logger)
        g = github.Github(github_token)
        repo = g.get_repo(spec['repository'])
        logger.info(f"Got repository {spec['repository']}")
        
        # Check for existing deploy keys with the same title
        title = spec.get('title', 'Kubernetes-managed deploy key')
        keys = list(repo.get_keys())
        logger.info(f"Found {len(keys)} existing deploy keys")
        
        # Track if we found and deleted our key
        key_deleted = False
        for key in keys:
            if key.title == title:
                logger.info(f"Found existing deploy key with title '{title}' (id: {key.id}), deleting it")
                key.delete()
                logger.info(f"Successfully deleted old deploy key {key.id}")
                key_deleted = True
        
        if not key_deleted:
            logger.info(f"No existing deploy key with title '{title}' found")
        
        # Generate SSH key pair
        logger.info("Generating new SSH key pair")
        private_key, public_key = generate_ssh_key()
        
        # Create GitHub deploy key
        key = repo.create_key(
            title=title,
            key=public_key,
            read_only=spec.get('readOnly', True)
        )
        logger.info(f"Created new deploy key: {key.id}")
        
        # Verify key was created
        if not verify_github_key(repo, key.id, logger):
            raise kopf.PermanentError("Failed to verify deploy key")
        logger.info(f"Verified deploy key {key.id} exists in GitHub")
        
        # Store the key ID in the status
        patch['status'] = {'keyId': key.id}
        
        # Create Kubernetes secret
        secret_name = f"{kwargs['meta']['name']}-private-key"
        owner_reference = kubernetes.client.V1OwnerReference(
            api_version=kwargs['body']['apiVersion'],
            kind=kwargs['body']['kind'],
            name=kwargs['body']['metadata']['name'],
            uid=kwargs['body']['metadata']['uid']
        )
        
        # Delete existing secret if it exists
        try:
            core_v1_api.delete_namespaced_secret(
                name=secret_name,
                namespace=kwargs['meta']['namespace']
            )
            logger.info(f"Deleted existing secret {secret_name}")
        except kubernetes.client.exceptions.ApiException as e:
            if e.status != 404:  # Only ignore if secret doesn't exist
                raise
        
        create_or_update_secret(
            secret_name,
            kwargs['meta']['namespace'],
            {'ssh-privatekey': private_key},
            owner_reference,
            logger
        )
        logger.info(f"Successfully created deploy key {key.id} and secret {secret_name}")
        
    except Exception as e:
        logger.error(f"Error creating deploy key: {str(e)}")
        # Clean up if key was created
        try:
            if 'key' in locals():
                key.delete()
                logger.info(f"Cleaned up deploy key {key.id} after error")
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {str(cleanup_error)}")
        raise kopf.PermanentError(str(e))

@kopf.on.update('github.com', 'v1alpha1', 'githubdeploykeys')
def update_deploy_key(spec, status, logger, patch, old, **kwargs):
    # Only recreate if title or readOnly changed
    if (old['spec'].get('title', 'Kubernetes-managed deploy key') == spec.get('title', 'Kubernetes-managed deploy key') and
        old['spec'].get('readOnly', True) == spec.get('readOnly', True)):
        logger.info("No relevant changes detected, skipping update")
        return
    
    logger.info("Detected changes in title or readOnly, recreating deploy key")
    # Call create handler to recreate the key
    create_deploy_key(spec, logger, patch, **kwargs)

@kopf.on.delete('github.com', 'v1alpha1', 'githubdeploykeys')
def delete_deploy_key(spec, meta, status, logger, **kwargs):
    # Get GitHub token from secret
    try:
        secret = core_v1_api.read_namespaced_secret(
            name='ghcr-secret',
            namespace='flux-system'
        )
        github_token = base64.b64decode(secret.data['github-token']).decode()
        logger.info("Got GitHub token")
    except kubernetes.client.exceptions.ApiException as e:
        raise kopf.PermanentError(f"Failed to get GitHub token: {e}")
    
    # Delete deploy key from GitHub if we have the key ID
    key_id = status.get('keyId') if status else None
    
    if key_id:
        logger.info(f"Found key ID in status: {key_id}")
        g = github.Github(github_token)
        try:
            repo = g.get_repo(spec['repository'])
            logger.info(f"Found repository {spec['repository']}")
            
            # Try to get and delete the key
            try:
                key = repo.get_key(key_id)
                key.delete()
                logger.info(f"Successfully deleted deploy key {key_id}")
            except github.GithubException as e:
                if e.status == 404:
                    logger.info(f"Deploy key {key_id} was already deleted")
                else:
                    logger.error(f"Error deleting deploy key {key_id}: {e}")
                    raise kopf.PermanentError(f"Failed to delete deploy key: {e}")
            
            # Verify the key is gone
            try:
                repo.get_key(key_id)
                logger.error(f"Deploy key {key_id} still exists after deletion!")
                raise kopf.PermanentError(f"Failed to delete deploy key {key_id}")
            except github.GithubException as e:
                if e.status == 404:
                    logger.info(f"Verified deploy key {key_id} is deleted")
                else:
                    logger.error(f"Error verifying key deletion: {e}")
                    raise kopf.PermanentError(f"Failed to verify key deletion: {e}")
        except github.GithubException as e:
            if e.status != 404:  # Ignore if repo not found
                raise kopf.PermanentError(f"Failed to delete deploy key: {e}")
    else:
        logger.info("No key ID in status, trying to find key by title")
        g = github.Github(github_token)
        try:
            repo = g.get_repo(spec['repository'])
            logger.info(f"Found repository {spec['repository']}")
            
            # List all keys to find ones with our title
            all_keys = list(repo.get_keys())
            logger.info(f"Found {len(all_keys)} total deploy keys")
            title = spec.get('title', 'Kubernetes-managed deploy key')
            
            keys_deleted = 0
            for key in all_keys:
                if key.title == title:
                    logger.info(f"Found deploy key with title '{title}' (id: {key.id}), deleting it")
                    key.delete()
                    keys_deleted += 1
                    
                    # Verify deletion
                    try:
                        repo.get_key(key.id)
                        logger.error(f"Deploy key {key.id} still exists after deletion!")
                    except github.GithubException as e:
                        if e.status == 404:
                            logger.info(f"Verified deploy key {key.id} is deleted")
                        else:
                            logger.error(f"Error verifying key deletion: {e}")
            
            if keys_deleted == 0:
                logger.info(f"No deploy keys with title '{title}' found")
            else:
                logger.info(f"Deleted {keys_deleted} deploy key(s) with title '{title}'")
                
        except github.GithubException as e:
            if e.status != 404:  # Ignore if repo not found
                raise kopf.PermanentError(f"Failed to delete deploy key: {e}")
    
    # The secret will be automatically deleted by Kubernetes garbage collection
    # since we set the owner reference
    logger.info(f"Secret {meta['name']}-private-key will be deleted by garbage collection")

def verify_github_key(repo, key_id, logger):
    """Verify GitHub deploy key exists."""
    try:
        repo.get_key(key_id)
        logger.info(f"Verified deploy key {key_id} exists in GitHub")
        return True
    except github.GithubException as e:
        logger.error(f"Failed to verify deploy key {key_id}: {e}")
        return False

@kopf.timer('github.com', 'v1alpha1', 'githubdeploykeys', interval=60.0)
def reconcile_deploy_key(spec, status, logger, patch, **kwargs):
    """Periodically reconcile the deploy key to ensure it exists."""
    try:
        # Get GitHub token and repository
        github_token = get_github_token(logger)
        g = github.Github(github_token)
        repo = g.get_repo(spec['repository'])
        
        # Get key ID from status
        key_id = status.get('keyId') if status else None
        if not key_id:
            logger.info("No key ID in status, recreating deploy key")
            create_deploy_key(spec, logger, patch, **kwargs)
            return
            
        # Check if our key still exists
        try:
            key = repo.get_key(key_id)
            if key.title != spec.get('title', 'Kubernetes-managed deploy key'):
                logger.info(f"Deploy key {key_id} exists but title has changed, recreating")
                create_deploy_key(spec, logger, patch, **kwargs)
            else:
                logger.info(f"Deploy key {key_id} exists and is correctly configured")
        except github.GithubException as e:
            if e.status == 404:
                logger.info(f"Deploy key {key_id} no longer exists, recreating")
                create_deploy_key(spec, logger, patch, **kwargs)
            else:
                logger.error(f"Error checking deploy key {key_id}: {e}")
                
        # Verify secret exists
        secret_name = f"{kwargs['meta']['name']}-private-key"
        try:
            core_v1_api.read_namespaced_secret(
                name=secret_name,
                namespace=kwargs['meta']['namespace']
            )
            logger.info(f"Secret {secret_name} exists")
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                logger.info(f"Secret {secret_name} is missing, recreating deploy key")
                create_deploy_key(spec, logger, patch, **kwargs)
            else:
                logger.error(f"Error checking secret {secret_name}: {e}")
                
    except Exception as e:
        logger.error(f"Error during reconciliation: {str(e)}")
