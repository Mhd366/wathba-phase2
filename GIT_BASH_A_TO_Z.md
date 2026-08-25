# WATHBA — Git Bash A to Z

## 1. Extract and open the project

Extract `WATHBA_PHASE2_REPO_READY.zip`, then right-click the extracted
`WATHBA_PHASE2` folder and choose **Open Git Bash here**.

## 2. Confirm Git

```bash
git --version
pwd
ls
```

## 3. Configure your identity (first time only)

```bash
git config --global user.name "YOUR NAME"
git config --global user.email "YOUR_GITHUB_EMAIL"
```

## 4. Create an empty private repository on GitHub

Use the name `wathba-phase2`. Select **Private** and do not add README,
`.gitignore`, or a license because they already exist locally.

## 5. Initialize and create the first commit

```bash
git init
git branch -M main
git status
git add .
git status
git commit -m "chore: initialize WATHBA Phase 2 foundation"
```

## 6. Connect your private repository

Replace `YOUR_USERNAME`:

```bash
git remote add origin https://github.com/YOUR_USERNAME/wathba-phase2.git
git remote -v
git push -u origin main
```

If GitHub requests authentication, sign in through the browser. Do not paste
your GitHub password into Git Bash.

## 7. Start each task in its own branch

```bash
git checkout -b feature/fastapi-integration
```

After making changes:

```bash
git status
git add .
git commit -m "feat: connect frontend analysis flow to FastAPI"
git push -u origin feature/fastapi-integration
```

Open GitHub and create a Pull Request from `feature/fastapi-integration` to
`main`. Merge only after review and tests pass.

## 8. Daily workflow

```bash
git checkout main
git pull origin main
git checkout -b feature/SHORT-TASK-NAME
```

When finished:

```bash
git add .
git commit -m "feat: SHORT DESCRIPTION"
git push -u origin feature/SHORT-TASK-NAME
```

## 9. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Return to the repository root:

```bash
cd ..
```

## 10. Run FastAPI

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the API documentation.

## 11. Transfer work to the team repository later

From the repository root:

```bash
git checkout main
git pull origin main
git remote rename origin personal
git remote add team https://github.com/TEAM_OR_ORG/TEAM_REPOSITORY.git
git fetch team
git checkout -b integration/wathba-phase2 team/main
```

Find your commits:

```bash
git log --oneline personal/main
```

Apply the required commits one by one, oldest first:

```bash
git cherry-pick COMMIT_ID
```

Then publish the integration branch:

```bash
git push -u team integration/wathba-phase2
```

Create a Pull Request into the team's `main` branch. Do not copy files manually
over the team project.

## Safety rules

- Never commit `.env`, API keys, database passwords, videos, or model weights.
- Run `git status` before every commit and push.
- Do not work directly on `main` after the first upload.
- Pull the latest `main` before starting a new feature branch.
- Use Pull Requests so every team change can be reviewed or reverted.

