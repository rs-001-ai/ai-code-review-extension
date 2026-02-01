# Building and Publishing the Extension

## Prerequisites

1. **Node.js** (v18+)
2. **npm**
3. **tfx-cli** (Azure DevOps Extension CLI)

```bash
npm install -g tfx-cli
```

4. **Publisher Account** - Create at https://marketplace.visualstudio.com/manage/publishers

## Setup

1. **Update publisher ID** in `vss-extension.json`:
   ```json
   "publisher": "your-publisher-id"
   ```

2. **Generate a unique task ID** - Replace the placeholder GUID in `tasks/AICodeReviewTask/task.json`:
   ```bash
   # On Linux/Mac
   uuidgen

   # On Windows PowerShell
   [guid]::NewGuid().ToString()
   ```

3. **Add icon and screenshot** - Replace placeholder files in `images/`:
   - `icon.png` (128x128)
   - `screenshot-pr-comment.png`

## Build

```bash
# Install root dependencies
npm install

# Build the task
npm run build

# This will:
# 1. Install task dependencies
# 2. Compile TypeScript to JavaScript
```

## Package

```bash
# Create .vsix package
npm run package
```

This creates `your-publisher-id.ai-code-review-1.0.0.vsix`

## Publish

### First Time - Create Publisher

1. Go to https://marketplace.visualstudio.com/manage/publishers
2. Click "Create Publisher"
3. Fill in details (ID, name, description)

### Get Personal Access Token (PAT)

1. Go to Azure DevOps → User Settings → Personal Access Tokens
2. Create token with scope: **Marketplace > Publish**

### Publish to Marketplace

```bash
# Login (first time)
tfx login --service-url https://marketplace.visualstudio.com

# Publish
npm run publish
```

Or upload manually:
1. Go to https://marketplace.visualstudio.com/manage/publishers/your-publisher-id
2. Click "New Extension" → "Azure DevOps"
3. Upload the `.vsix` file

## Testing Locally

### Share with Your Organization (Private)

```bash
tfx extension publish --manifest-globs vss-extension.json --share-with your-org-name
```

### Install in Azure DevOps

1. Go to your Azure DevOps organization
2. Organization Settings → Extensions
3. Find your extension under "Shared with this organization"
4. Click Install

## Versioning

Update version in:
1. `vss-extension.json` - Extension version
2. `tasks/AICodeReviewTask/task.json` - Task version
3. `package.json` (optional)

```bash
# Bump version and publish
tfx extension publish --manifest-globs vss-extension.json --rev-version
```

## Troubleshooting

### "Task not found"
- Ensure `tasks/AICodeReviewTask` is included in `vss-extension.json` files array
- Verify task ID in `task.json` is a valid GUID

### "Python not found"
- The task requires Python 3.x on the agent
- Use `ubuntu-latest` or `windows-latest` pools (have Python pre-installed)

### "System.AccessToken is empty"
- Enable "Allow scripts to access the OAuth token" in pipeline settings
- Or explicitly pass: `SYSTEM_ACCESSTOKEN: $(System.AccessToken)`
