#!/usr/bin/env bash

[[ -f /root/.bashrc ]] && source /root/.bashrc
function prop { key="${2}=" file="/root/.k8s/${1}" rslt=$(grep "${3:-}" "$file" -A 10 | grep "$key" | head -n 1 | cut -d '=' -f2 | sed 's/ //g'); [[ -z "$rslt" ]] && key="${2} = " && rslt=$(grep "${3:-}" "$file" -A 10 | grep "$key" | head -n 1 | cut -d '=' -f2 | sed 's/ //g'); rslt=$(echo "$rslt" | tr -d '\n' | tr -d '\r'); echo "$rslt"; }
BASE_DIR="${TZ_REPO_ROOT:-/vagrant/tz-local/resource}"
cd "${BASE_DIR}/minio"

#set -x
shopt -s expand_aliases
alias k='kubectl --kubeconfig ~/.kube/config'

k8s_project=$(prop 'project' 'project')
k8s_domain=$(prop 'project' 'domain')
basic_password=$(prop 'project' 'basic_password')
NS=devops

kubectl create namespace ${NS}
#k apply -f storageclass.yaml -n ${NS}

# Use official MinIO Helm chart (same as dev server)
helm repo add minio https://charts.min.io/
helm repo update
helm uninstall minio -n ${NS} 2>/dev/null || true

# Install MinIO Helm chart
cp -Rf values.yaml values.yaml_bak
sed -i "s/k8s_project/${k8s_project}/g" values.yaml_bak
sed -i "s/basic_password/${basic_password}/g" values.yaml_bak
helm upgrade --install minio minio/minio --version 5.4.0 -n ${NS} -f values.yaml_bak

sleep 60

MINIO_ROOT_USER=$(kubectl get secret --namespace ${NS} minio -o jsonpath="{.data.rootUser}" | base64 --decode; echo)
MINIO_ROOT_PASSWORD=$(kubectl get secret --namespace ${NS} minio -o jsonpath="{.data.rootPassword}" | base64 --decode; echo)
echo "MinIO Root User: ${MINIO_ROOT_USER}"
echo "MinIO Root Password: ${MINIO_ROOT_PASSWORD}"

# Deploy Ingress for MinIO external access
cp -Rf minio-ingress.yaml minio-ingress.yaml_bak
sed -i "s/k8s_project/${k8s_project}/g" minio-ingress.yaml_bak
sed -i "s/k8s_domain/${k8s_domain}/g" minio-ingress.yaml_bak
kubectl apply -f minio-ingress.yaml_bak -n ${NS}

#kubectl -n ${NS} port-forward svc/minio 9000:9000
#kubectl -n ${NS} port-forward svc/minio-console 9001:9001

exit 0
