import * as tl from 'azure-pipelines-task-lib/task';
import * as tr from 'azure-pipelines-task-lib/toolrunner';
import * as path from 'path';

async function run(): Promise<void> {
    try {
        tl.setResourcePath(path.join(__dirname, 'task.json'));
        console.log(tl.loc('TaskStarted'));

        // Check if this is a PR build
        const buildReason = tl.getVariable('Build.Reason');
        if (buildReason !== 'PullRequest') {
            console.log(tl.loc('NotPullRequest'));
            tl.setResult(tl.TaskResult.Skipped, 'Not a Pull Request build');
            return;
        }

        // Get inputs
        const openaiApiKey = tl.getInput('openaiApiKey', true);
        if (!openaiApiKey) {
            throw new Error(tl.loc('MissingApiKey'));
        }

        const openaiModel = tl.getInput('openaiModel', false) || 'gpt-5.2-codex';
        const maxFiles = tl.getInput('maxFiles', false) || '50';
        const maxLinesPerFile = tl.getInput('maxLinesPerFile', false) || '1000';
        const debug = tl.getBoolInput('debug', false);
        const continueOnError = tl.getBoolInput('continueOnError', false);

        // Get Azure DevOps context from predefined variables
        const systemAccessToken = tl.getVariable('System.AccessToken');
        const prId = tl.getVariable('System.PullRequest.PullRequestId');
        const orgUrl = tl.getVariable('System.CollectionUri');
        const project = tl.getVariable('System.TeamProject');
        const repoId = tl.getVariable('Build.Repository.ID');

        if (!systemAccessToken) {
            throw new Error('System.AccessToken is not available. Ensure "Allow scripts to access the OAuth token" is enabled in the pipeline.');
        }

        if (!prId) {
            throw new Error('Pull Request ID not found. This task must run on a PR build.');
        }

        // Set up environment variables for the Python script
        const env: { [key: string]: string } = {
            'SYSTEM_ACCESSTOKEN': systemAccessToken,
            'OPENAI_API_KEY': openaiApiKey,
            'PR_ID': prId,
            'ORG_URL': orgUrl || '',
            'PROJECT': project || '',
            'REPO_ID': repoId || '',
            'OPENAI_MODEL': openaiModel,
            'MAX_FILES': maxFiles,
            'MAX_LINES_PER_FILE': maxLinesPerFile,
            'DEBUG': debug ? 'true' : 'false',
            'SKILL_PATH': path.join(__dirname, 'code-review-skill')
        };

        // Find Python
        const pythonPath = tl.which('python3', false) || tl.which('python', true);
        console.log(`Using Python: ${pythonPath}`);

        // Run the Python script
        const scriptPath = path.join(__dirname, 'ai-code-review.py');
        console.log(`Running script: ${scriptPath}`);

        const pythonTool: tr.ToolRunner = tl.tool(pythonPath)
            .arg(scriptPath);

        const options: tr.IExecOptions = {
            env: { ...process.env, ...env },
            failOnStdErr: false,
            ignoreReturnCode: continueOnError
        };

        const exitCode = await pythonTool.exec(options);

        if (exitCode !== 0 && !continueOnError) {
            throw new Error(`Python script exited with code ${exitCode}`);
        }

        console.log(tl.loc('TaskCompleted'));
        tl.setResult(tl.TaskResult.Succeeded, tl.loc('ReviewPosted'));

    } catch (err: any) {
        const continueOnError = tl.getBoolInput('continueOnError', false);
        const errorMessage = err.message || String(err);

        console.error(tl.loc('TaskFailed', errorMessage));

        if (continueOnError) {
            tl.setResult(tl.TaskResult.SucceededWithIssues, errorMessage);
        } else {
            tl.setResult(tl.TaskResult.Failed, errorMessage);
        }
    }
}

run();
