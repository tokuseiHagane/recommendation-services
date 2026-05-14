kubectl get secret ghcr-login-secret -n bots -o yaml | \
  sed 's/namespace: bots/namespace: parsers/' | \
  kubectl apply -f -
