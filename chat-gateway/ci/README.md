# DrillQuiz CI/CD Pipeline Documentation

## Overview

This document describes the comprehensive CI/CD pipeline implementation for the DrillQuiz project, including security scanning, deployment automation, and infrastructure management.

## Technology Stack

- **Backend**: Django 4.2.7 (Python 3.10)
- **Frontend**: Vue.js 2.6.14 (Node.js 18)
- **Container**: Docker (Backend: python:3.10-slim, Frontend: node:18-alpine + nginx:alpine)
- **Orchestration**: Kubernetes
- **CI/CD**: Jenkins (Kubernetes agent)
- **Security**: Comprehensive security scanning with multiple tools

## Pipeline Architecture

### Branch-Specific Pipeline Configuration

This project uses different Jenkins pipelines for each branch:

- **main/dev branch**: `Jenkinsfile` (basic pipeline, no security scan)
- **qa branch**: `Jenkinsfile_qa` (pipeline with comprehensive security scan)
- **mobile branch**: `Jenkins_mobile` (Capacitor-focused mobile delivery pipeline)

### Environment Configuration

#### Production Environment (main branch)
- **Namespace**: `devops`
- **Database**: `devops-postgres-postgresql.devops.svc.cluster.local` (drillquiz DB)
- **Redis**: `redis-cluster-drillquiz-master.devops.svc.cluster.local`
- **MinIO**: `minio.devops.svc.cluster.local` (drillquiz bucket)

#### QA Environment (qa branch)
- **Namespace**: `devops` (Pod deployment)
- **Database**: `devops-postgres-postgresql.devops-dev.svc.cluster.local` (drillquiz-qa DB)
- **Redis**: `redis-cluster-drillquiz-master.devops-dev.svc.cluster.local`
- **MinIO**: `minio.devops.svc.cluster.local` (drillquiz-dev bucket)

#### Development Environment (other branches)
- **Namespace**: `devops-dev`
- **Database**: `devops-postgres-postgresql.devops-dev.svc.cluster.local` (drillquiz DB)
- **Redis**: `redis-cluster-drillquiz-master.devops-dev.svc.cluster.local`
- **MinIO**: `minio.devops.svc.cluster.local` (drillquiz-dev bucket)

## Jenkins Setup

### 1. Create Multibranch Pipeline

1. Click "New Item" in Jenkins dashboard
2. Select "Multibranch Pipeline"
3. Enter project name (e.g., `drillquiz-multibranch`)

### 2. Branch Sources Configuration

1. In **Branch Sources** section, click "Add source" → "Git"
2. **Repository URL**: `https://github.com/doohee323/drillquiz.git`
3. **Credentials**: Select GitHub token
4. Add **Behaviors**:
   - Check "Discover branches"
   - Check "Discover pull requests from origin" (optional)

### 3. Build Configuration Setup

1. In **Build Configuration** section:
   - **Mode**: "by Jenkinsfile"
   - **Script Path**: Set differently for each branch

### 4. Branch-Specific Script Path Setup

#### Method A: Rename Jenkinsfile (Recommended)

Rename Jenkinsfile in each branch:

```bash
# In main/dev branch
mv ci/Jenkinsfile ci/Jenkinsfile_main
mv ci/Jenkinsfile_qa ci/Jenkinsfile

# In qa branch  
mv ci/Jenkinsfile_qa ci/Jenkinsfile
```

#### Method B: Specify Script Path

Set Script Path for each branch in Multibranch Pipeline:

- **main branch**: `ci/Jenkinsfile`
- **dev branch**: `ci/Jenkinsfile`  
- **qa branch**: `ci/Jenkinsfile_qa`

## Pipeline Stages

### Basic Pipeline (main/dev branch)

1. **Checkout**: Source code checkout
2. **Build Frontend**: Vue.js application build
3. **Build & Push Backend Image**: Docker image creation and push
4. **Deploy to Kubernetes**: Application deployment

### Enhanced Pipeline (qa branch)

1. **Checkout**: Source code checkout
2. **Security Scan**: Comprehensive security analysis
3. **Build Frontend**: Vue.js application build
4. **Build & Push Backend Image**: Docker image creation and push
5. **Deploy to Kubernetes**: Application deployment

### Mobile Pipeline (mobile branch)

1. **Checkout**: Source code checkout
2. **Prepare Mobile Assets**: Executes `ci/mobile-build.sh prepare` inside a Node.js container to install dependencies, build the Vue bundle, and sync Capacitor platforms
3. **Android Build**: Runs Gradle within an Android SDK container to produce APK/AAB artefacts (`ANDROID_SDK_ROOT` is provided by the container)
4. **Package iOS Project**: Archives the Capacitor iOS project files for manual Xcode compilation (optional `.xcarchive` when macOS agents are available)
5. **Archive Artefacts**: Stores `build/mobile/**` outputs in Jenkins artefacts for download and signing

> ℹ️ iOS binary generation still requires a macOS executor. The pipeline packages the project to keep the workflow consistent until a macOS agent is configured.

### Mobile Build Helper Script

- **Script**: `ci/mobile-build.sh`
- **Purpose**: Shared across local development and Jenkins runners to keep Capacitor build steps consistent
- **Phases**:
  - `prepare`: Install npm dependencies, run `npm run build`, execute `npx cap sync/add` for enabled platforms
  - `android`: Trigger Gradle tasks (default `assembleRelease`) and collect APK/AAB artefacts into `build/mobile/android`
  - `ios`: Package the iOS project directory or produce an `.xcarchive` when `CAPACITOR_IOS_ARCHIVE=true` on macOS
  - `full`: Convenience wrapper that runs `prepare` and platform-specific phases sequentially
- **Key environment variables**:
  - `CAPACITOR_PLATFORMS` (`android,ios` by default)
  - `CAPACITOR_BUILD_MODE` (`release` / `debug`)
  - `CAPACITOR_OUTPUT_DIR` (`build/mobile`)
  - `CAPACITOR_ANDROID_TASK` (override Gradle task, e.g. `bundleRelease`)
  - `CAPACITOR_IOS_ARCHIVE` (`true` to enable xcarchive creation)
  - `CAPACITOR_LOCAL_API` (`true` to point the Vue bundle at `http://10.0.2.2:8000` for emulator testing)

## Security Scanning Implementation

### Security Tools Integration

The security scanning system includes multiple layers of analysis:

#### 1. SAST (Static Application Security Testing)
- **Tool**: Semgrep
- **Coverage**: Python/Django + JavaScript/Vue.js
- **Rules**: OWASP Top 10 + language-specific rules
- **Output**: SARIF format

#### 2. SCA (Software Composition Analysis)
- **Tool**: Trivy
- **Coverage**: Python dependencies, Node.js packages, OS packages
- **Vulnerability Database**: Up-to-date CVE database
- **Output**: SARIF format

#### 3. Container Image Scanning
- **Tool**: Trivy
- **Coverage**: Backend and Frontend Docker images
- **Analysis**: Vulnerabilities, configuration issues, unused packages
- **Output**: SARIF format

#### 4. IaC (Infrastructure as Code) Scanning
- **Tools**: Checkov, kube-linter
- **Coverage**: Kubernetes manifests, Dockerfiles
- **Analysis**: Security best practices, misconfigurations
- **Output**: SARIF format

#### 5. DAST (Dynamic Application Security Testing)
- **Tools**: OWASP ZAP, Nikto
- **Coverage**: Running web application
- **Analysis**: Runtime vulnerabilities, web security issues
- **Output**: SARIF format

### Security Scripts

#### `ci/security-scan.sh`
Comprehensive security scanning script with the following features:

- **Multi-tool Installation**: Automatic installation of security tools
- **Parallel Execution**: Efficient scanning with parallel tool execution
- **SARIF Integration**: Standardized output format
- **ChatGPT Analysis**: AI-powered security issue analysis and recommendations
- **MinIO Storage**: Secure storage of scan results
- **Error Handling**: Robust error handling and fallback mechanisms

#### `ci/security-gate.sh`
Security threshold enforcement script:

- **Severity-based Filtering**: Critical/High issue detection
- **Pipeline Control**: Build failure on critical issues
- **Configurable Thresholds**: Adjustable security policies

### Security Scan Configuration

#### Environment Variables

```bash
# Security scan control
SAST_YN=true
SCA_YN=true
CONTAINER_SCAN_YN=true
IAC_SCAN_YN=true
DAST_SCAN_YN=true

# Service configuration
SERVICE_URL=https://us.drillquiz.com

# MinIO configuration
MINIO_ACCESS_KEY=credentials('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY=credentials('MINIO_SECRET_KEY')
MINIO_ENDPOINT=http://minio.devops.svc.cluster.local:9000
MINIO_BUCKET_NAME=drillquiz

# ChatGPT API (optional)
OPENAI_API_KEY=credentials('openai-api-key')
```

#### Scan Execution

```bash
# Run comprehensive security scan
./ci/security-scan.sh

# Run specific scan types
SAST_YN=true SCA_YN=false ./ci/security-scan.sh
```

## Kubernetes Deployment

### Deployment Scripts

#### `ci/k8s.sh`
Main deployment script with the following capabilities:

- **Environment Detection**: Automatic environment configuration
- **Resource Management**: Dynamic resource naming based on branch
- **Health Checks**: Application health verification
- **Rollback Support**: Automatic rollback on deployment failure

#### Kubernetes Manifests

- **`ci/k8s.yaml`**: Production deployment configuration
- **`ci/k8s-dev.yaml`**: Development environment configuration
- **`ci/k8s-qa.yaml`**: QA environment configuration

### Resource Naming Convention

- **Production (main branch)**: No branch suffix
- **Non-production branches**: `${GIT_BRANCH}` suffix appended
- **Secrets**: Always include `${SECRET_SUFFIX}` for security

## Monitoring and Notifications

### Slack Integration

```groovy
// Security alerts
slackSend channel: '#security-alerts',
         color: 'danger',
         message: "🚨 Security scan failed in ${env.JOB_NAME} #${env.BUILD_NUMBER}"

// Deployment notifications
slackSend channel: '#deployments',
         color: 'good',
         message: "✅ ${env.JOB_NAME} #${env.BUILD_NUMBER} deployed successfully"
```

### SARIF Results Management

- **Storage**: MinIO for secure, long-term storage
- **Access**: Jenkins Archive Artifacts for immediate access
- **Security**: Never committed to Git repository
- **Analysis**: ChatGPT-powered issue analysis and recommendations

## Implementation Phases

### Phase 1: Basic Pipeline (Completed)
- ✅ Jenkins multibranch pipeline setup
- ✅ Docker image build and push
- ✅ Kubernetes deployment
- ✅ Basic security scanning

### Phase 2: Enhanced Security (Completed)
- ✅ Comprehensive security tool integration
- ✅ SARIF output standardization
- ✅ Security gate implementation
- ✅ MinIO storage integration

### Phase 3: Advanced Features (In Progress)
- 🔄 ChatGPT-powered security analysis
- 🔄 Advanced monitoring and alerting
- 🔄 Automated remediation suggestions
- 🔄 Security dashboard integration

## Cost Considerations

- **Free Tools**: Semgrep, Trivy, Checkov, kube-linter, OWASP ZAP
- **Paid Tools**: Optional ChatGPT API for advanced analysis
- **Infrastructure**: Kubernetes cluster resources
- **Storage**: MinIO for scan result storage

## Best Practices

### Security
- Regular security scan execution
- Critical/High issue immediate remediation
- Secure storage of scan results
- Regular tool updates and rule updates

### Development
- Branch-specific pipeline configuration
- Environment isolation
- Automated testing integration
- Code quality gates

### Operations
- Health check monitoring
- Automated rollback procedures
- Resource optimization
- Log aggregation and analysis

## Troubleshooting

### Common Issues

1. **Security Scan Failures**
   - Check tool installation
   - Verify network connectivity
   - Review scan configuration

2. **Deployment Issues**
   - Verify Kubernetes cluster access
   - Check resource availability
   - Review manifest configuration

3. **MinIO Storage Issues**
   - Verify credentials
   - Check network connectivity
   - Review bucket permissions

### Debug Commands

```bash
# Check security scan status
./ci/security-scan.sh

# Verify Kubernetes deployment
kubectl get pods -n devops

# Check MinIO connectivity
mc ls drillquiz/security-scan/
```

## Local Testing with ci.sh

### Overview

The `ci/ci.sh` script provides a local testing environment that simulates the Jenkins pipeline flow, allowing developers to test the entire CI/CD process locally before pushing to the repository.

### Features

- **Full Pipeline Simulation**: Replicates all Jenkins pipeline stages
- **Environment Variable Management**: Configurable environment variables for testing
- **ArgoCD Integration Testing**: Tests ArgoCD deployment flow locally
- **Security Scan Testing**: Validates security scanning scripts
- **Kubernetes Deployment Testing**: Tests k8s.sh deployment logic
- **Error Handling**: Comprehensive error reporting and stage-by-stage validation

### Prerequisites

```bash
# Required tools
docker
kubectl
git
bash (version 4.0+)

# Optional (for full functionality)
# Valid kubeconfig file
# ArgoCD access credentials
# GitHub token for Git operations
```

### Usage

#### Basic Usage

```bash
# Run full pipeline simulation
./ci/ci.sh

# Show help
./ci/ci.sh --help

# Show current environment variables
./ci/ci.sh --env
```

#### Environment Configuration

```bash
# Set custom environment variables
export BUILD_NUMBER="20240101120000"
export GIT_BRANCH="origin/dev"
export NAMESPACE="devops-dev"
export ARGOCD_ENABLED="true"
export ARGOCD_PASSWORD="your-argocd-password"
export GIT_TOKEN="your-github-token"

# Run with custom configuration
./ci/ci.sh
```

#### Stage-Specific Testing

```bash
# Run only specific stages
./ci/ci.sh --stage checkout    # Checkout stage only
./ci/ci.sh --stage build       # Build stage only
./ci/ci.sh --stage deploy      # Deploy stage only
./ci/ci.sh --stage security-pre # Pre-build security scan only
```

#### Testing Scenarios

##### 1. Full Pipeline Test (Recommended)

```bash
# Test complete pipeline flow
./ci/ci.sh
```

##### 2. ArgoCD Deployment Test

```bash
# Test ArgoCD integration specifically
export ARGOCD_ENABLED="true"
export ARGOCD_PASSWORD="your-password"
export GIT_TOKEN="your-token"
./ci/ci.sh --stage deploy
```

##### 3. Security Scan Test

```bash
# Test security scanning functionality
./ci/ci.sh --stage security-pre
./ci/ci.sh --stage security-post
```

##### 4. Kubernetes Deployment Test

```bash
# Test k8s.sh deployment logic
export KUBECONFIG="$HOME/.kube/config"  # For actual deployment
./ci/ci.sh --stage deploy
```

### Environment Variables

#### Required Variables (with defaults)

```bash
BUILD_NUMBER="${BUILD_NUMBER:-$(date +%Y%m%d%H%M%S)}"
GIT_BRANCH="${GIT_BRANCH:-origin/dev}"
NAMESPACE="${NAMESPACE:-devops-dev}"
ARGOCD_ENABLED="${ARGOCD_ENABLED:-true}"
```

#### ArgoCD Configuration

```bash
ARGOCD_ID="${ARGOCD_ID:-admin}"
ARGOCD_PASSWORD="${ARGOCD_PASSWORD:-your-argocd-password}"
ARGOCD_SERVER="${ARGOCD_SERVER:-argocd.drillquiz.com}"
ARGOCD_REPO_URL="${ARGOCD_REPO_URL:-https://github.com/doohee323/tz-argocd-repo.git}"
GIT_USERNAME="${GIT_USERNAME:-doohee323}"
GIT_TOKEN="${GIT_TOKEN:-your-github-token}"
```

#### Security Scan Configuration

```bash
SAST_YN="${SAST_YN:-false}"
SCA_YN="${SCA_YN:-false}"
IAC_YN="${IAC_YN:-false}"
OPENAI_API_KEY="${OPENAI_API_KEY:-your-openai-api-key}"
```

### Pipeline Stages

The local test script simulates the following Jenkins pipeline stages:

1. **Checkout**: Source code checkout simulation
2. **Build**: Docker image build simulation
3. **Security Scan (Pre-build)**: Pre-build security scanning
4. **Deploy to Kubernetes**: Full k8s.sh deployment execution
5. **Use Case Tests**: Application testing
6. **Security Scan (Post-build)**: Post-build security scanning

### Output and Logging

The script provides color-coded output:

- 🔵 **Blue**: General information and stage progress
- 🟢 **Green**: Success messages
- 🟡 **Yellow**: Warnings
- 🔴 **Red**: Errors

Example output:

```
[2024-01-01 12:00:00] 🚀 Starting Local CI/CD Pipeline Simulation
[2024-01-01 12:00:01] 🔍 Checking prerequisites...
[2024-01-01 12:00:02] ✅ docker is available
[2024-01-01 12:00:02] ✅ kubectl is available
[2024-01-01 12:00:02] ✅ Prerequisites check completed
[2024-01-01 12:00:03] 🎯 Starting stage: Deploy to Kubernetes
[2024-01-01 12:00:04] 🐳 Simulating kubectl container environment...
[2024-01-01 12:00:05] ✅ Stage completed: Deploy to Kubernetes
```

### Troubleshooting

#### Common Issues

1. **Permission Denied**
   ```bash
   chmod +x ci/ci.sh
   chmod +x ci/k8s.sh
   ```

2. **Missing Dependencies**
   ```bash
   # Install required tools
   brew install docker kubectl  # macOS
   apt-get install docker.io kubectl  # Ubuntu
   ```

3. **ArgoCD Connection Issues**
   ```bash
   # Verify credentials
   export ARGOCD_PASSWORD="correct-password"
   export GIT_TOKEN="valid-github-token"
   ```

4. **Kubernetes Access Issues**
   ```bash
   # Set kubeconfig
   export KUBECONFIG="$HOME/.kube/config"
   kubectl cluster-info  # Verify cluster access
   ```

#### Debug Mode

```bash
# Enable debug output
set -x
./ci/ci.sh --stage deploy
set +x
```

### Integration with Jenkins

The local test script is designed to:

- **Match Jenkins Environment**: Uses the same environment variables and script execution
- **Validate Changes**: Ensures changes work locally before Jenkins execution
- **Reduce Debug Time**: Identifies issues early in the development cycle
- **Test ArgoCD Flow**: Validates ArgoCD integration without affecting production

### Best Practices

1. **Always test locally first**: Run `./ci/ci.sh` before pushing changes
2. **Use stage-specific testing**: Test individual stages during development
3. **Set proper credentials**: Use valid tokens and passwords for full testing
4. **Monitor output**: Pay attention to warnings and errors
5. **Clean environment**: Reset environment variables between test runs

### Examples

#### Development Workflow

```bash
# 1. Make changes to k8s.sh or Jenkinsfile
# 2. Test locally
./ci/ci.sh

# 3. Test specific functionality
./ci/ci.sh --stage deploy

# 4. If successful, commit and push
git add .
git commit -m "Fix deployment issue"
git push origin dev
```

#### Debugging Deployment Issues

```bash
# Test deployment with verbose output
export KUBECONFIG="$HOME/.kube/config"
export ARGOCD_PASSWORD="your-password"
set -x
./ci/ci.sh --stage deploy
set +x
```

#### Security Scan Validation

```bash
# Test security scanning
export SAST_YN="true"
export SCA_YN="true"
./ci/ci.sh --stage security-pre
```

## Contributing

When contributing to the CI/CD pipeline:

1. Test changes in development environment using `./ci/ci.sh`
2. Update documentation for new features
3. Follow security best practices
4. Maintain backward compatibility
5. Update version numbers and changelog

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review Jenkins build logs
3. Consult security scan results
4. Contact the DevOps team

---

*This documentation is maintained as part of the DrillQuiz project CI/CD pipeline implementation.*