# 1. SSH into your meta server
ssh root@159.56.4.94

# 2. Clone or update the repository
cd /opt
git clone <your-repo-url> correlation-station
# OR if already cloned:
cd /opt/correlation-station
git pull origin main  # or develop

# 3. Navigate to the observability stack
cd seefa-om

# 4. Set up environment variables (first time only)
cp .env.example .env
# Edit .env with your settings
nano .env

# 5. Run pre-setup checks (first time only)
make pre-setup

# 6. Start all services
make start-all

# 7. Verify deployment
make health
make status

# 8. View logs to ensure everything is running
make logs
Option 2: GitLab CI/CD Deployment (Automated)
The GitLab pipeline I created handles automated deployment. Here's how to set it up:

GitLab CI/CD Setup
Add SSH Key to GitLab:

# On meta server, generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "gitlab-deploy@meta-server"

# Copy the private key
cat ~/.ssh/id_ed25519
Configure GitLab Variables:

Go to your GitLab project → Settings → CI/CD → Variables
Add these variables:
SSH_PRIVATE_KEY: Paste the private key from step 1
META_SERVER: 159.56.4.94 (already set in .gitlab-ci.yml)
DATADOG_API_KEY (optional): Your DataDog API key if using dual export
Authorize GitLab Runner SSH:

# On meta server, add the SSH public key to authorized_keys
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
Deploy via GitLab:

Push to develop branch → triggers staging deployment (manual approval required)
Push to main branch → triggers production deployment (manual approval required)
In GitLab:

Go to CI/CD → Pipelines
Find your pipeline
Click on the deploy:meta-server:staging or deploy:meta-server:production job
Click the Play button to trigger deployment

MDSO Server Deployment (Grafana Alloy)
For the MDSO Dev server (159.56.4.37), deploy Grafana Alloy:

# SSH to MDSO Dev server
ssh root@159.56.4.37

# Copy the installation script
scp root@159.56.4.94:/opt/correlation-station/mdso-instrumentation/alloy/install-alloy.sh .

# Make it executable
chmod +x install-alloy.sh

# Run installation
sudo ./install-alloy.sh

# Verify Alloy is running
sudo systemctl status alloy
sudo journalctl -u alloy -f
Troubleshooting
If deployment fails:

# Check Docker service
sudo systemctl status docker

# Check disk space
df -h

# Check Docker logs
docker-compose logs --tail=50

# Restart services
make restart

# Complete cleanup and restart
make clean
make start-all
Which deployment option would you like to use? I recommend starting with Option 1 (Manual) for your first deployment to ensure everything is configured correctly, then moving to Option 2 (GitLab CI/CD) for ongoing deployments.

do i need to do anything from the gitlab ui

Yes, you need to configure a few things in the GitLab UI before deployment will work:

Required GitLab UI Setup
1. Add CI/CD Variables (One-time setup)
Navigate to: Your Project → Settings → CI/CD → Variables → Expand → Add Variable

Add these variables:

| Key | Value | Protected | Masked | |-----|-------|-----------|--------| | SSH_PRIVATE_KEY | Your SSH private key for meta server | ✓ | ✓ | | DATADOG_API_KEY | Your DataDog API key (optional) | ✓ | ✓ |

To get your SSH private key:

# On meta server (159.56.4.94)
ssh root@159.56.4.94
cat ~/.ssh/id_rsa
# OR if using ed25519:
cat ~/.ssh/id_ed25519

# Copy the entire output including:
# -----BEGIN OPENSSH PRIVATE KEY-----
# ... key content ...
# -----END OPENSSH PRIVATE KEY-----
2. Trigger Deployment (After pushing code)
Once you push your code and the pipeline runs:

Go to CI/CD → Pipelines
Click on the latest pipeline
You'll see the pipeline stages: test → build → deploy → validate
The deploy jobs will show a play button ▶️ (they're set to when: manual)
Click the play button on:
deploy:meta-server:staging (for develop branch)
deploy:meta-server:production (for main branch)
That's it! The pipeline will SSH into your meta server and run the deployment.

Optional: Monitor Pipeline
While the pipeline runs, you can:

Click on individual jobs to see real-time logs
View test results and coverage reports
Check deployment status
See validation results (health checks)
Do you have SSH access to the meta server already set up? If not, I can help you generate the SSH key and configure it.

yes I do

Perfect! Then you just need to do two things in the GitLab UI:

Step 1: Add SSH Private Key Variable
Go to your GitLab project: Settings → CI/CD → Variables
Click Add variable
Enter:
Key: SSH_PRIVATE_KEY
Value: Your SSH private key (copy from cat ~/.ssh/id_rsa or cat ~/.ssh/id_ed25519 on meta server)
Type: Variable
Flags: Check ✓ Protected and ✓ Masked
Click Add variable
Step 2: Trigger Deployment
Since you already pushed the code:

Go to CI/CD → Pipelines
Find the pipeline for your latest commit (faedc98 - feat: complete MDSO ↔ Sense observability implementation)
The pipeline will automatically run the test stage
Once tests pass, you'll see the deploy stage with a play button ▶️
Click ▶️ on deploy:meta-server:staging (since you pushed to a claude/* branch, this deploys to develop)
Watch the deployment logs in real-time
The deployment will SSH to 159.56.4.94 and run:

cd /opt/correlation-station/seefa-om
docker-compose pull
docker-compose up -d
docker-compose ps
After deployment completes, the validate:health-checks job will automatically verify all services are healthy.

That's it! The entire process is automated once you click the play button.


Perfect! I've created a unified deployment solution for the SENSE apps. Here's how to deploy them on your meta server:

Quick Deployment (Recommended)
# SSH to meta server
ssh root@159.56.4.94

# Navigate to sense-apps
cd /opt/correlation-station/sense-apps

# Pull latest code (after merging your PR)
git pull origin main

# Create environment config
cp .env.example .env

# Create app-specific .env files
cp .env.example arda/.env
cp .env.example beorn/.env
cp .env.example palantir/.env

# Start all three services
docker-compose up -d

# Verify they're running
docker-compose ps

# Check health
curl http://localhost:5001/health  # Arda
curl http://localhost:5002/health  # Beorn
curl http://localhost:5003/health  # Palantir

# View logs
docker-compose logs -f
That's it! All three SENSE apps will be running with:

Arda on port 5001 (FastAPI)
Beorn on port 5002 (Flask)
Palantir on port 5003 (Flask)
What I Created
sense-apps/docker-compose.yml - Unified deployment for all three apps with:

OpenTelemetry auto-configuration (exports to your Correlation Gateway at 159.56.4.94:4318)
Health checks for each service
Connection to your observability network
Optional DataDog dual export support
sense-apps/.env.example - Environment variable template

sense-apps/DEPLOYMENT.md - Complete deployment guide with troubleshooting

After Deployment
Access your services at:

Arda API Docs: http://159.56.4.94:5001/docs
Beorn: http://159.56.4.94:5002
Palantir: http://159.56.4.94:5003
Traces and logs will automatically flow to your Grafana stack at http://159.56.4.94:8443

The files are committed and ready to merge!

