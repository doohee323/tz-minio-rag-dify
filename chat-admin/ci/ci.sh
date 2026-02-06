#!/bin/bash

# Local CI/CD Test Script
# This script simulates Jenkins pipeline flow for local testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌${NC} $1"
}

# Default values (can be overridden by environment variables)
export BUILD_NUMBER="${BUILD_NUMBER:-$(date +%Y%m%d%H%M%S)}"
export GIT_BRANCH="${GIT_BRANCH:-origin/dev}"
export BRANCH_NAME="${BRANCH_NAME:-dev}"
export REGISTRY="${REGISTRY:-doohee323}"
export DOCKER_NAME="${DOCKER_NAME:-drillquiz}"
export FRONT_DOCKER_NAME="${FRONT_DOCKER_NAME:-drillquiz-frontend}"
export DOCKER_USERNAME="${DOCKER_USERNAME:-doohee323}"
export DOCKER_PASSWORD="${DOCKER_PASSWORD:-Hongdoohee!323}"
export APP_NAME="${APP_NAME:-drillquiz}"
export DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-drillquiz}"
export NAMESPACE="${NAMESPACE:-devops-dev}"
export TAG_ID="${TAG_ID:-${BUILD_NUMBER}}"
export KUBECONFIG_CREDENTIALS_ID="${KUBECONFIG_CREDENTIALS_ID:-kubeconfig}"

# ArgoCD related environment variables
export ARGOCD_ID="${ARGOCD_ID:-admin}"
export ARGOCD_PASSWORD="${ARGOCD_PASSWORD:-aaaaa}"
export GIT_TOKEN="${GIT_TOKEN:-ghp_aaaaaaa}"

# Debug: verify environment variable setup
log "🔍 DEBUG: Environment variable setup in ci.sh:"
log "🔍 DEBUG: GIT_TOKEN from parameter: '${GIT_TOKEN}'"
log "🔍 DEBUG: GIT_TOKEN length: ${#GIT_TOKEN}"
log "🔍 DEBUG: GIT_TOKEN first 10 chars: ${GIT_TOKEN:0:10}"
log "🔍 DEBUG: GIT_TOKEN last 10 chars: ${GIT_TOKEN: -10}"
export ARGOCD_SERVER="${ARGOCD_SERVER:-argocd.drillquiz.com}"
export ARGOCD_REPO_URL="${ARGOCD_REPO_URL:-https://github.com/doohee323/tz-argocd-repo.git}"
export ARGOCD_ENABLED="${ARGOCD_ENABLED:-false}"  # Disable ArgoCD for local testing
export GIT_USERNAME="${GIT_USERNAME:-doohee323}"
export GIT_REPO_NAME="${GIT_REPO_NAME:-tz-argocd-repo}"

# Additional Jenkins variables
export GIT_COMMITTER_EMAIL="${GIT_COMMITTER_EMAIL:-doohee323@gmail.com}"
export NODE_ENV="${NODE_ENV:-development}"
export K8S_FILE="${K8S_FILE:-k8s.yaml}"
export KUBECTL="${KUBECTL:-kubectl -n ${NAMESPACE}}"
export GIT_CREDENTIAL="${GIT_CREDENTIAL:-github-token}"
export GIT_TOKEN="${GITHUB_TOKEN:-ghp_aaaaa}"
export DOCKERHUB_CREDENTIALS_ID="${DOCKERHUB_CREDENTIALS_ID:-DOCKERHUB_CREDENTIALS_ID}"
export VAULT_TOKEN="${VAULT_TOKEN:-your-vault-token}"

# Application secrets
export GOOGLE_OAUTH_CLIENT_SECRET="${GOOGLE_OAUTH_CLIENT_SECRET:-your-google-oauth-secret}"
export MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-your-minio-access-key}"
export MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-your-minio-secret-key}"
export MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio.devops.svc.cluster.local:9000}"
export MINIO_BUCKET_NAME="${MINIO_BUCKET_NAME:-drillquiz}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-your-postgres-password}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-your-openai-api-key}"

# Security scan variables (disabled for local testing)
export SAST_YN="${SAST_YN:-false}"
export SCA_YN="${SCA_YN:-false}"
export IAC_YN="${IAC_YN:-false}"
export IAC_SCAN_YN="${IAC_SCAN_YN:-false}"
export CONTAINER_SCAN_YN="${CONTAINER_SCAN_YN:-false}"
export DAST_SCAN_YN="${DAST_SCAN_YN:-false}"
export SBOM_YN="${SBOM_YN:-false}"
export IMAGE_SIGNING_YN="${IMAGE_SIGNING_YN:-false}"
export PROVENANCE_YN="${PROVENANCE_YN:-false}"

# Other variables
export WORKSPACE="${PWD}"
export BACKEND_URL="${BACKEND_URL:-http://localhost:3000}"
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:3001}"
export SERVICE_URL="${SERVICE_URL:-http://localhost:3000}"
export VAULT_TOKEN="${VAULT_TOKEN:-your-vault-token}"
export GOOGLE_OAUTH_CLIENT_SECRET="${GOOGLE_OAUTH_CLIENT_SECRET:-your-google-secret}"

log "🚀 Starting Local CI/CD Pipeline Simulation"
log "📋 Pipeline Configuration:"
log "  BUILD_NUMBER: ${BUILD_NUMBER}"
log "  GIT_BRANCH: ${GIT_BRANCH}"
log "  NAMESPACE: ${NAMESPACE}"
log "  ARGOCD_ENABLED: ${ARGOCD_ENABLED}"
log "  ARGOCD_SERVER: ${ARGOCD_SERVER}"
log "  ARGOCD_REPO_URL: ${ARGOCD_REPO_URL}"

# Function to check prerequisites
check_prerequisites() {
    log "🔍 Checking prerequisites..."
    
    # Check if required tools are installed
    local tools=("docker" "kubectl" "git")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is not installed"
            exit 1
        fi
        log_success "$tool is available"
    done
    
    # Check if ci/k8s.sh exists and is executable
    if [ ! -f "ci/k8s.sh" ]; then
        log_error "ci/k8s.sh not found"
        exit 1
    fi
    
    if [ ! -x "ci/k8s.sh" ]; then
        log "🔧 Making ci/k8s.sh executable..."
        chmod +x ci/k8s.sh
    fi
    
    log_success "Prerequisites check completed"
}

# Function to simulate Jenkins stages
run_stage() {
    local stage_name="$1"
    local stage_function="$2"
    
    log "🎯 Starting stage: $stage_name"
    echo "================================================"
    
    if $stage_function; then
        log_success "Stage completed: $stage_name"
        echo "================================================"
        return 0
    else
        log_error "Stage failed: $stage_name"
        echo "================================================"
        return 1
    fi
}

# Stage 1: Checkout
stage_checkout() {
    log "📥 Checkout stage (simulated)"
    log "  Repository: $(git remote get-url origin)"
    log "  Branch: $(git branch --show-current)"
    log "  Commit: $(git rev-parse HEAD)"
    return 0
}

# Stage 2: Build Frontend
stage_build_frontend() {
    log "🔨 Build Frontend stage"
    log "⚠️ Frontend build not implemented yet, skipping"
    return 0
}

# Stage 3: Build & Push Backend Image
stage_build_backend() {
    log "🔨 Build stage"
    
    # Check if Dockerfile exists, if not use Dockerfile.backend
    if [ ! -f "Dockerfile" ]; then
        if [ -f "Dockerfile.backend" ]; then
            log "  Using Dockerfile.backend for build"
            cp Dockerfile.backend Dockerfile
        else
            log_warning "No Dockerfile found, skipping build"
            return 0
        fi
    else
        log "  Using existing Dockerfile"
    fi
    
    # Actual Docker build
    log "🐳 Building Docker image: ${DOCKER_NAME}:${TAG_ID}"
    log "  Registry: ${REGISTRY}"
    
    # Build backend image with cache optimization
    log "  Building backend image..."
    if docker build --cache-from ${DOCKER_NAME}:latest -t ${DOCKER_NAME}:${TAG_ID} .; then
        log_success "Backend image built successfully"
    else
        log_error "Backend image build failed"
        return 1
    fi
    
    # Push to registry (if credentials are available)
    if [ -n "${DOCKER_PASSWORD:-}" ] && [ -n "${DOCKER_USERNAME:-}" ]; then
        log "  Pushing to registry..."
        
        # Tag image for Docker Hub
        DOCKER_HUB_IMAGE="${DOCKER_USERNAME}/${DOCKER_NAME}:${TAG_ID}"
        docker tag ${DOCKER_NAME}:${TAG_ID} ${DOCKER_HUB_IMAGE}
        
        # Try to push directly (assuming already logged in)
        if docker push ${DOCKER_HUB_IMAGE}; then
            log_success "Image pushed successfully to registry: ${DOCKER_HUB_IMAGE}"
        else
            log_warning "Failed to push image, trying to login first..."
            if printf '%s\n' "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin; then
                if docker push ${DOCKER_HUB_IMAGE}; then
                    log_success "Image pushed successfully to registry: ${DOCKER_HUB_IMAGE}"
                else
                    log_error "Failed to push image to registry: ${DOCKER_HUB_IMAGE}"
                    return 1
                fi
            else
                log_warning "Docker login failed, skipping push"
            fi
        fi
    else
        log_warning "Docker credentials not available, skipping push"
        log "  To enable push, set DOCKER_USERNAME and DOCKER_PASSWORD environment variables"
    fi
    
    log_success "Build completed successfully"
    return 0
}

# Stage 2: Pre-Build Security Scan
stage_security_scan_pre() {
    log "🔒 Pre-build Security Scan"
    
    # Check if security scan script exists
    if [ ! -f "ci/security-scan.sh" ]; then
        log_warning "ci/security-scan.sh not found, skipping security scan"
        return 0
    fi
    
    # Run security scan
    log "🔍 Running pre-build security scan..."
    if [ -x "ci/security-scan.sh" ]; then
        ./ci/security-scan.sh pre-build
    else
        log_warning "ci/security-scan.sh is not executable"
        return 0
    fi
    
    return 0
}

# Stage 5: Deploy to Kubernetes
stage_deploy() {
    log "🚀 Deploy to Kubernetes"
    
    # Export environment variables like Jenkins does
    export PATH=$PATH:.:/
    export BUILD_NUMBER="${BUILD_NUMBER}"
    export GIT_BRANCH="${GIT_BRANCH}"
    export NAMESPACE="${NAMESPACE}"
    export ARGOCD_ENABLED="${ARGOCD_ENABLED}"
    export ARGOCD_SERVER="${ARGOCD_SERVER}"
    export ARGOCD_REPO_URL="${ARGOCD_REPO_URL}"
    export GIT_USERNAME="${GIT_USERNAME}"
    export GIT_TOKEN="${GIT_TOKEN}"
    export ARGOCD_PASSWORD="${ARGOCD_PASSWORD}"
    
    # Make k8s.sh executable
    chmod +x ci/k8s.sh
    
    # Simulate kubectl container environment
    log "🐳 Simulating kubectl container environment..."
    
    # Check if we have kubeconfig
    if [ -z "${KUBECONFIG:-}" ] && [ ! -f "${HOME}/.kube/config" ]; then
        log_warning "No kubeconfig found. This will test the script flow but won't actually deploy to Kubernetes."
        log "To test with actual Kubernetes deployment, set KUBECONFIG environment variable."
    fi
    
    # Run k8s deployment with proper environment setup
    log "🔧 Running Kubernetes deployment..."
    log "  Command: ./ci/k8s.sh ${BUILD_NUMBER} ${GIT_BRANCH} ${NAMESPACE} deploy"
    log "  Environment variables passed to k8s.sh:"
    log "    BUILD_NUMBER: ${BUILD_NUMBER}"
    log "    GIT_BRANCH: ${GIT_BRANCH}"
    log "    NAMESPACE: ${NAMESPACE}"
    log "    ARGOCD_ENABLED: ${ARGOCD_ENABLED}"
    log "    ARGOCD_SERVER: ${ARGOCD_SERVER}"
    log "    ARGOCD_REPO_URL: ${ARGOCD_REPO_URL}"
    log "    GIT_USERNAME: ${GIT_USERNAME}"
    log "    GIT_TOKEN: ${GIT_TOKEN:+[SET]}"
    log "    ARGOCD_PASSWORD: ${ARGOCD_PASSWORD:+[SET]}"
    
    # Debug: verify environment variable values
    log "🔍 DEBUG: Detailed environment variable values:"
    log "🔍 DEBUG: GIT_TOKEN length: ${#GIT_TOKEN}"
    log "🔍 DEBUG: GIT_TOKEN first 10 chars: ${GIT_TOKEN:0:10}"
    log "🔍 DEBUG: GIT_TOKEN last 10 chars: ${GIT_TOKEN: -10}"
    log "🔍 DEBUG: ARGOCD_PASSWORD length: ${#ARGOCD_PASSWORD}"
    log "🔍 DEBUG: ARGOCD_PASSWORD first 10 chars: ${ARGOCD_PASSWORD:0:10}"
    
    # Create environment file for k8s.sh
    ENV_FILE="/tmp/drillquiz-env-${BUILD_NUMBER}.env"
    cat > "${ENV_FILE}" << EOF
BUILD_NUMBER="${BUILD_NUMBER}"
GIT_BRANCH="${GIT_BRANCH}"
NAMESPACE="${NAMESPACE}"
ARGOCD_ENABLED="${ARGOCD_ENABLED}"
ARGOCD_SERVER="${ARGOCD_SERVER}"
ARGOCD_REPO_URL="${ARGOCD_REPO_URL}"
GIT_USERNAME="${GIT_USERNAME}"
GIT_TOKEN="${GIT_TOKEN}"
ARGOCD_PASSWORD="${ARGOCD_PASSWORD}"
ARGOCD_ID="${ARGOCD_ID}"
EOF
    
    log "🔍 DEBUG: Created environment file: ${ENV_FILE}"
    log "🔍 DEBUG: GIT_TOKEN in env file: ${GIT_TOKEN:0:10}..."
    
    # Execute k8s.sh with environment file
    if ./ci/k8s.sh ${BUILD_NUMBER} ${GIT_BRANCH} ${NAMESPACE} deploy "${ENV_FILE}"; then
        log_success "Kubernetes deployment completed successfully"
        return 0
    else
        log_error "Kubernetes deployment failed"
        return 1
    fi
}

# Stage 6: Post-Build Security Scan
stage_security_scan_post() {
    log "🔒 Post-Build Security Scan"
    
    # Check if security scan script exists
    if [ ! -f "ci/security-scan.sh" ]; then
        log_warning "ci/security-scan.sh not found, skipping security scan"
        return 0
    fi
    
    # Run security scan
    log "🔍 Running post-build security scan..."
    if [ -x "ci/security-scan.sh" ]; then
        ./ci/security-scan.sh post-build
    else
        log_warning "ci/security-scan.sh is not executable"
        return 0
    fi
    
    return 0
}

# Main pipeline execution
main() {
    log "🎬 Starting Local CI/CD Pipeline"
    
    # Check prerequisites
    check_prerequisites
    
    # Define pipeline stages
    local stages=(
        "Checkout:stage_checkout"
        "Pre-Build Security Scan:stage_security_scan_pre"
        "Build Frontend:stage_build_frontend"
        "Build & Push Backend Image:stage_build_backend"
        "Deploy to Kubernetes:stage_deploy"
        "Post-Build Security Scan:stage_security_scan_post"
    )
    
    # Execute stages
    local failed_stages=()
    for stage_info in "${stages[@]}"; do
        IFS=':' read -r stage_name stage_function <<< "$stage_info"
        
        if ! run_stage "$stage_name" "$stage_function"; then
            failed_stages+=("$stage_name")
        fi
    done
    
    # Pipeline summary
    log "📊 Pipeline Summary:"
    if [ ${#failed_stages[@]} -eq 0 ]; then
        log_success "All stages completed successfully!"
        log "🎉 Pipeline execution completed successfully"
        exit 0
    else
        log_error "Pipeline failed with ${#failed_stages[@]} failed stage(s):"
        for stage in "${failed_stages[@]}"; do
            log_error "  - $stage"
        done
        log "💥 Pipeline execution failed"
        exit 1
    fi
}

# Help function
show_help() {
    echo "Local CI/CD Pipeline Test Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -e, --env      Show current environment variables"
    echo "  -s, --stage    Run specific stage only"
    echo ""
    echo "Environment Variables:"
    echo "  BUILD_NUMBER           Build number (default: timestamp)"
    echo "  GIT_BRANCH            Git branch (default: origin/dev)"
    echo "  NAMESPACE             Kubernetes namespace (default: devops-dev)"
    echo "  ARGOCD_ENABLED        Enable ArgoCD deployment (default: true)"
    echo "  ARGOCD_SERVER         ArgoCD domain (default: drillquiz.com)"
    echo "  ARGOCD_PASSWORD       ArgoCD password (default: your-argocd-password)"
    echo "  GIT_TOKEN             GitHub token (default: your-github-token)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run full pipeline"
    echo "  $0 -s deploy          # Run only deploy stage"
    echo "  $0 -e                 # Show environment variables"
    echo "  ARGOCD_ENABLED=false $0  # Run without ArgoCD"
}

# Show environment variables
show_env() {
    log "📋 Current Environment Variables:"
    echo "  BUILD_NUMBER: ${BUILD_NUMBER}"
    echo "  GIT_BRANCH: ${GIT_BRANCH}"
    echo "  NAMESPACE: ${NAMESPACE}"
    echo "  ARGOCD_ENABLED: ${ARGOCD_ENABLED}"
    echo "  ARGOCD_SERVER: ${ARGOCD_SERVER}"
    echo "  ARGOCD_REPO_URL: ${ARGOCD_REPO_URL}"
    echo "  REGISTRY: ${REGISTRY}"
    echo "  DOCKER_NAME: ${DOCKER_NAME}"
    echo "  APP_NAME: ${APP_NAME}"
    echo "  WORKSPACE: ${WORKSPACE}"
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -e|--env)
        show_env
        exit 0
        ;;
    -s|--stage)
        if [ -z "${2:-}" ]; then
            log_error "Stage name required for -s option"
            show_help
            exit 1
        fi
        case "$2" in
            checkout) run_stage "Checkout" stage_checkout ;;
            build-frontend) run_stage "Build Frontend" stage_build_frontend ;;
            build-backend) run_stage "Build & Push Backend Image" stage_build_backend ;;
            security-pre) run_stage "Pre-Build Security Scan" stage_security_scan_pre ;;
            deploy) run_stage "Deploy to Kubernetes" stage_deploy ;;
            security-post) run_stage "Post-Build Security Scan" stage_security_scan_post ;;
            *)
                log_error "Unknown stage: $2"
                log "Available stages: checkout, build-frontend, build-backend, security-pre, deploy, security-post"
                exit 1
                ;;
        esac
        ;;
    "")
        main
        ;;
    *)
        log_error "Unknown option: $1"
        show_help
        exit 1
        ;;
esac
