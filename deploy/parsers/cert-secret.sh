kubectl get secret cert-secret -n front -o yaml | \
  sed 's/namespace: front/namespace: parsers/' | \
  kubectl apply -f -
